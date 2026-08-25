import os
import pickle
import pandas as pd
import numpy as np
import mysql.connector
from mysql.connector import Error
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.linear_model import LinearRegression
from supabase import create_client, Client
import time
from pathlib import Path

# RUTA ABSOLUTA BASE (Soluciona el error de lectura del CSV en Render)
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "model_aguacate.pkl"
DATASET_FILE = BASE_DIR / "dataset.csv"

app = FastAPI(title="Microservicio - Aguacate AI (A1)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración desde Variables de Entorno
MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST", "bxcyjzl01ttmj7sbirum-mysql.services.clever-cloud.com"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "uxefqjn8zmichsb1"),
    "password": os.getenv("DB_PASSWORD", "NEm0EL1wZzMX0LPNjMQA"),
    "database": os.getenv("DB_NAME", "bxcyjzl01ttmj7sbirum"),
    "use_pure": True,
    "connection_timeout": 30,
    "autocommit": True
}

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "modelos-privados")

model = None
latest_ipc_factor = 1.20

class AguacateRequest(BaseModel):
    service_id: int
    batch_weight_kg: float
    cooling_hours: float
    electricity_kwh_rate: float


def get_supabase_client() -> Client:
    """Inicializa el cliente de Supabase usando credenciales de variables de entorno."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Las variables de entorno SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar configuradas.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def download_model_from_supabase() -> bool:
    """Intenta descargar el archivo PKL desde el bucket privado de Supabase."""
    try:
        supabase = get_supabase_client()
        data = supabase.storage.from_(SUPABASE_BUCKET).download("model_aguacate.pkl")
        with open(MODEL_FILE, "wb") as f:
            f.write(data)
        print("📥 [Supabase] Modelo PKL descargado exitosamente.")
        return True
    except Exception as e:
        print(f"ℹ️ [Supabase] No se pudo descargar el modelo PKL ({e}). Se procederá a entrenar.")
        return False


def upload_model_to_supabase() -> bool:
    """Sube o actualiza el archivo PKL entrenado hacia el bucket de Supabase."""
    try:
        supabase = get_supabase_client()
        with open(MODEL_FILE, "rb") as f:
            file_data = f.read()
        
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            file=file_data,
            path="model_aguacate.pkl",
            file_options={"cache-control": "3600", "upsert": "true"}
        )
        print("📤 [Supabase] Modelo PKL subido/actualizado exitosamente en el almacenamiento privado.")
        return True
    except Exception as e:
        print(f"❌ [Supabase] Error crítico al subir el modelo PKL a Supabase: {e}")
        return False


def get_db_connection():
    """Obtiene conexión a MySQL con reintentos."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            return conn
        except Error as e:
            print(f"⚠️ Intento {attempt+1}/{max_retries} de conexión a DB falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise HTTPException(status_code=500, detail=f"Error de conexión a DB: {str(e)}")


def load_or_train_model():
    global model
    
    # 1. Intentar cargar el PKL local o descargarlo de Supabase
    if not MODEL_FILE.exists():
        download_model_from_supabase()

    if MODEL_FILE.exists():
        try:
            with open(MODEL_FILE, "rb") as f:
                model = pickle.load(f)
            print("📦 [Aguacate] Modelo cargado desde pickle exitosamente.")
            return
        except Exception as e:
            print(f"⚠️ [Aguacate] El archivo PKL local está corrupto o falló al leerse ({e}). Re-entrenando...")

    # 2. Entrenar usando la ruta absoluta del CSV
    print(f"⚙️ [Aguacate] Iniciando entrenamiento utilizando {DATASET_FILE}...")
    if not DATASET_FILE.exists():
        error_msg = f"No se encontró el archivo obligatorio '{DATASET_FILE}'."
        print(f"❌ [Aguacate] {error_msg}")
        model = None
        return

    try:
        data_df = pd.read_csv(DATASET_FILE)
        
        required_features = ["service_id", "batch_weight_kg", "cooling_hours", "electricity_kwh_rate", "ipc_factor"]
        target_col = "price"

        missing_features = [col for col in required_features if col not in data_df.columns]
        if missing_features:
            raise ValueError(f"Faltan columnas requeridas en el CSV: {missing_features}")
        if target_col not in data_df.columns:
            raise ValueError(f"Falta la columna objetivo '{target_col}' en el CSV.")

        X = data_df[required_features]
        y = data_df[target_col]

        new_model = LinearRegression()
        new_model.fit(X, y)

        with open(MODEL_FILE, "wb") as f:
            pickle.dump(new_model, f)
        
        model = new_model
        print("✅ [Aguacate] Modelo entrenado localmente con éxito.")

        upload_model_to_supabase()

    except Exception as train_error:
        print(f"❌ [Aguacate] Fallo crítico durante el procesamiento/entrenamiento del CSV: {train_error}")
        model = None


@app.on_event("startup")
async def startup_event():
    """Ejecuta la lógica de carga/entrenamiento al iniciar la API."""
    load_or_train_model()


@app.get("/")
async def root():
    return {
        "service": app.title,
        "status": "online",
        "health_check": "/health",
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    db_status = "disconnected"
    db_error = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_error = str(e)

    model_ready = model is not None
    status_code = "healthy" if db_status == "connected" and model_ready else "degraded"

    return {
        "status": status_code,
        "database": db_status,
        "model_loaded": model_ready,
        "db_error": db_error
    }


@app.post("/api/aguacate/quote")
async def quote_aguacate(data: AguacateRequest):
    if model is None:
        raise HTTPException(
            status_code=503, 
            detail="El servicio no está disponible: El modelo IA no está cargado ni pudo entrenarse. Revisa la presencia de dataset.csv."
        )

    try:
        input_df = pd.DataFrame([{
            "service_id": data.service_id,
            "batch_weight_kg": data.batch_weight_kg,
            "cooling_hours": data.cooling_hours,
            "electricity_kwh_rate": data.electricity_kwh_rate,
            "ipc_factor": latest_ipc_factor
        }])
        
        prediction = model.predict(input_df)
        unit_price_kg = round(max(0.03, float(prediction[0])), 3)
        total = round(unit_price_kg * data.batch_weight_kg, 2)
    except Exception as e:
        print(f"❌ [Aguacate] Error en inferencia de IA: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la predicción del modelo: {str(e)}")

    quote_id = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO service_quotes (service_id, batch_volume_qq, fuel_cost_per_liter, calculated_cost_per_qq) VALUES (%s, %s, %s, %s)",
            (data.service_id, data.batch_weight_kg, data.electricity_kwh_rate, unit_price_kg)
        )
        conn.commit()
        quote_id = cursor.lastrowid
        cursor.close()
        conn.close()
        print(f"✅ [Aguacate] Cotización guardada en DB: ID={quote_id}")
    except Exception as db_err:
        print(f"⚠️ [Aguacate] Advertencia: No se pudo registrar la cotización en MySQL ({db_err})")

    return {
        "quote_id": quote_id,
        "unit_price_per_kg_usd": unit_price_kg,
        "total_usd": total,
        "weight_kg": data.batch_weight_kg
    }