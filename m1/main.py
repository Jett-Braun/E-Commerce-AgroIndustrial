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

app = FastAPI(title="Microservicio - Maquinaria AI (M1)")

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

MODEL_FILE = "model_maquinaria.pkl"
DATASET_FILE = "dataset.csv"
model = None
latest_maint_factor = 1.55

class MaquinariaRequest(BaseModel):
    equipment_type: int
    hours_requested: float
    fuel_cost_per_liter: float

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
            print("📦 [Maquinaria] Modelo cargado desde pickle exitosamente.")
        else:
            raise FileNotFoundError("Archivo PKL no encontrado, iniciando entrenamiento dinámico.")
    except Exception as e:
        print(f"⚠️ [Maquinaria] Error al cargar PKL ({e}). Intentando entrenar desde {DATASET_FILE}...")
        try:
            if not os.path.exists(DATASET_FILE):
                records = [{"equipment_type": 1, "hours_requested": 8.0, "fuel_cost_per_liter": 0.8, "mantenimiento_factor": 1.55, "price": 45.0}]
                data_df = pd.DataFrame(records)
            else:
                data_df = pd.read_csv(DATASET_FILE)

            X = data_df[["equipment_type", "hours_requested", "fuel_cost_per_liter", "mantenimiento_factor"]]
            y = data_df["price"] if "price" in data_df.columns else np.random.uniform(30, 80, len(data_df))

            model = LinearRegression()
            model.fit(X, y)

            with open(MODEL_FILE, "wb") as f:
                pickle.dump(model, f)
            print("✅ [Maquinaria] Modelo entrenado y guardado en PKL.")
        except Exception as train_error:
            print(f"❌ [Maquinaria] Fallo crítico durante el entrenamiento: {train_error}")
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

@app.post("/api/maquinaria/quote")
async def quote_maquinaria(data: MaquinariaRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="El modelo de IA de Maquinaria no está disponible.")

    try:
        input_df = pd.DataFrame([{
            "equipment_type": data.equipment_type,
            "hours_requested": data.hours_requested,
            "fuel_cost_per_liter": data.fuel_cost_per_liter,
            "mantenimiento_factor": latest_maint_factor
        }])
        
        prediction = model.predict(input_df)
        hourly_rate = round(max(8.00, float(prediction[0])), 2)
        total = round(hourly_rate * data.hours_requested, 2)
    except Exception as e:
        print(f"❌ [Maquinaria] Error en inferencia de IA: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la predicción: {str(e)}")

    quote_id = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO service_quotes (service_id, batch_volume_qq, fuel_cost_per_liter, calculated_cost_per_qq) VALUES (%s, %s, %s, %s)",
            (6, data.hours_requested, data.fuel_cost_per_liter, hourly_rate)
        )
        conn.commit()
        quote_id = cursor.lastrowid
        cursor.close()
        conn.close()
        print(f"✅ [Maquinaria] Cotización guardada en DB: ID={quote_id}")
    except Exception as db_err:
        print(f"⚠️ [Maquinaria] Advertencia: No se pudo guardar en MySQL ({db_err})")

    return {
        "quote_id": quote_id,
        "hourly_rate_usd": hourly_rate,
        "total_usd": total,
        "hours": data.hours_requested
    }