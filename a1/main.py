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
import time

app = FastAPI(title="Microservicio - Aguacate AI (A1)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
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

MODEL_FILE = "model_aguacate.pkl"
DATASET_FILE = "dataset.csv"
model = None
latest_ipc_factor = 1.20

class AguacateRequest(BaseModel):
    service_id: int
    batch_weight_kg: float
    cooling_hours: float
    electricity_kwh_rate: float

def get_db_connection():
    """Obtiene conexión a MySQL con reintentos"""
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
    try:
        if os.path.exists(MODEL_FILE):
            with open(MODEL_FILE, "rb") as f:
                model = pickle.load(f)
            print("📦 [Aguacate] Modelo cargado desde pickle exitosamente.")
        else:
            raise FileNotFoundError("Archivo PKL no encontrado, iniciando entrenamiento dinámico.")
    except Exception as e:
        print(f"⚠️ [Aguacate] Error al cargar PKL ({e}). Intentando entrenar desde {DATASET_FILE}...")
        try:
            if not os.path.exists(DATASET_FILE):
                records = [{"service_id": 1, "batch_weight_kg": 1000.0, "cooling_hours": 24.0, "electricity_kwh_rate": 0.15, "ipc_factor": 1.20, "price": 0.08}]
                data_df = pd.DataFrame(records)
            else:
                data_df = pd.read_csv(DATASET_FILE)

            X = data_df[["service_id", "batch_weight_kg", "cooling_hours", "electricity_kwh_rate", "ipc_factor"]]
            y = data_df["price"] if "price" in data_df.columns else np.random.uniform(0.04, 0.12, len(data_df))

            model = LinearRegression()
            model.fit(X, y)

            with open(MODEL_FILE, "wb") as f:
                pickle.dump(model, f)
            print("✅ [Aguacate] Modelo entrenado y guardado en PKL.")
        except Exception as train_error:
            print(f"❌ [Aguacate] Fallo crítico durante el entrenamiento: {train_error}")
            model = None

@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected", "result": result[0]}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

load_or_train_model()

@app.post("/api/aguacate/quote")
async def quote_aguacate(data: AguacateRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="El modelo de IA de Aguacate no está disponible.")

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
        raise HTTPException(status_code=500, detail=f"Error al procesar la predicción: {str(e)}")

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
        print(f"⚠️ [Aguacate] Advertencia: No se pudo guardar en MySQL ({db_err})")

    return {
        "quote_id": quote_id,
        "unit_price_per_kg_usd": unit_price_kg,
        "total_usd": total,
        "weight_kg": data.batch_weight_kg
    }