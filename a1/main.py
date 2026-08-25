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
from sklearn.metrics import mean_squared_error, r2_score
from supabase import create_client, Client
import time
from pathlib import Path
import traceback
from datetime import datetime

# ============================================
# RUTAS ABSOLUTAS (SOLUCIONA EL ERROR DE LECTURA DEL CSV)
# ============================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "model_aguacate.pkl"
DATASET_FILE = BASE_DIR / "dataset.csv"

# ============================================
# INICIALIZACIÓN DE FASTAPI
# ============================================

app = FastAPI(title="Microservicio - Aguacate AI (A1)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================

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

# ============================================
# CONFIGURACIÓN DE SUPABASE
# ============================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "modelos-privados")
SUPABASE_MODEL_NAME = os.getenv("MODEL_NAME", "model_aguacate.pkl")

# ============================================
# VARIABLES GLOBALES
# ============================================

model = None
model_loaded = False
last_training_date = None
training_data_count = 0
last_error = None
latest_ipc_factor = 1.20

# ============================================
# MODELOS DE DATOS
# ============================================

class AguacateRequest(BaseModel):
    service_id: int
    batch_weight_kg: float
    cooling_hours: float
    electricity_kwh_rate: float

# ============================================
# EXCEPCIONES PERSONALIZADAS
# ============================================

class ModelError(Exception):
    pass

class CSVNotFoundError(ModelError):
    pass

class CSVInvalidError(ModelError):
    pass

class TrainingError(ModelError):
    pass

# ============================================
# FUNCIONES DE SUPABASE
# ============================================

def get_supabase_client() -> Client:
    """Inicializa el cliente de Supabase usando credenciales de variables de entorno."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Las variables de entorno SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar configuradas.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def download_model_from_supabase() -> bool:
    """Intenta descargar el archivo PKL desde el bucket privado de Supabase."""
    try:
        supabase = get_supabase_client()
        data = supabase.storage.from_(SUPABASE_BUCKET).download(SUPABASE_MODEL_NAME)
        with open(MODEL_FILE, "wb") as f:
            f.write(data)
        print(f"📥 [Supabase] Modelo {SUPABASE_MODEL_NAME} descargado exitosamente.")
        return True
    except Exception as e:
        print(f"ℹ️ [Supabase] No se pudo descargar el modelo ({e}). Se procederá a entrenar.")
        return False

def upload_model_to_supabase() -> bool:
    """Sube o actualiza el archivo PKL entrenado hacia el bucket de Supabase."""
    try:
        supabase = get_supabase_client()
        with open(MODEL_FILE, "rb") as f:
            file_data = f.read()
        
        # Intentar subir o actualizar
        try:
            # Primero intentamos subir
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                file=file_data,
                path=SUPABASE_MODEL_NAME,
                file_options={"cache-control": "3600", "upsert": "true"}
            )
        except Exception as upload_error:
            # Si falla, intentamos actualizar (si existe)
            print(f"⚠️ [Supabase] Error al subir, intentando actualizar: {upload_error}")
            supabase.storage.from_(SUPABASE_BUCKET).update(
                file=file_data,
                path=SUPABASE_MODEL_NAME,
                file_options={"cache-control": "3600"}
            )
        
        print(f"📤 [Supabase] Modelo {SUPABASE_MODEL_NAME} subido/actualizado exitosamente.")
        return True
    except Exception as e:
        print(f"❌ [Supabase] Error al subir el modelo: {e}")
        return False

# ============================================
# FUNCIONES DE BASE DE DATOS
# ============================================

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

# ============================================
# VALIDACIÓN DEL CSV
# ============================================

def validate_csv_file():
    """
    Valida que el archivo CSV exista y tenga el formato correcto.
    Lanza excepciones si hay problemas.
    """
    # 1. Verificar que el archivo existe
    if not DATASET_FILE.exists():
        raise CSVNotFoundError(
            f"El archivo CSV no existe en: {DATASET_FILE}\n"
            f"BASE_DIR: {BASE_DIR}\n"
            f"Archivos en el directorio: {list(BASE_DIR.iterdir()) if BASE_DIR.exists() else 'Directorio no existe'}"
        )
    
    # 2. Verificar que no está vacío
    if DATASET_FILE.stat().st_size == 0:
        raise CSVInvalidError(f"El archivo {DATASET_FILE} está vacío.")
    
    # 3. Intentar leer el CSV
    try:
        data = pd.read_csv(DATASET_FILE)
    except Exception as e:
        raise CSVInvalidError(f"Error al leer el CSV: {str(e)}")
    
    # 4. Verificar que tiene datos
    if len(data) == 0:
        raise CSVInvalidError(f"El archivo {DATASET_FILE} está vacío (0 filas).")
    
    # 5. Verificar columnas necesarias
    required_columns = ['service_id', 'batch_weight_kg', 'cooling_hours', 'electricity_kwh_rate', 'price']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        raise CSVInvalidError(
            f"Columnas faltantes: {', '.join(missing_columns)}\n"
            f"Columnas encontradas: {', '.join(data.columns)}\n"
            f"Columnas requeridas: {', '.join(required_columns)}"
        )
    
    # 6. Validar datos
    for col in required_columns:
        if data[col].isnull().any():
            raise CSVInvalidError(f"La columna '{col}' tiene valores nulos.")
    
    # 7. Verificar suficientes datos
    if len(data) < 10:
        raise CSVInvalidError(f"Solo {len(data)} registros. Se necesitan al menos 10.")
    
    # 8. Verificar que los valores son válidos
    if (data['batch_weight_kg'] <= 0).any():
        raise CSVInvalidError("El peso del lote debe ser mayor a 0.")
    
    if (data['cooling_hours'] < 0).any():
        raise CSVInvalidError("Las horas de enfriamiento no pueden ser negativas.")
    
    if (data['electricity_kwh_rate'] <= 0).any():
        raise CSVInvalidError("La tarifa eléctrica debe ser mayor a 0.")
    
    if (data['price'] <= 0).any():
        raise CSVInvalidError("Los precios deben ser mayores a 0.")
    
    return data

# ============================================
# FUNCIONES DE ENTRENAMIENTO
# ============================================

def train_model_from_csv():
    """
    Entrena el modelo desde el archivo CSV local.
    Lanza excepciones si hay problemas.
    """
    global model, model_loaded, last_training_date, training_data_count, last_error
    
    try:
        print("📊 [Aguacate] Iniciando entrenamiento...")
        
        # 1. Validar CSV
        data = validate_csv_file()
        
        # 2. Preparar características
        features = ['service_id', 'batch_weight_kg', 'cooling_hours', 'electricity_kwh_rate']
        
        # Agregar IPC factor si existe
        if 'ipc_factor' in data.columns:
            features.append('ipc_factor')
            X = data[features]
            print("📊 [Aguacate] Usando ipc_factor del CSV")
        else:
            # Si no existe, usar el valor por defecto
            data['ipc_factor'] = latest_ipc_factor
            features.append('ipc_factor')
            X = data[features]
            print(f"📊 [Aguacate] Usando ipc_factor por defecto: {latest_ipc_factor}")
        
        y = data['price']
        
        # 3. Entrenar el modelo
        print(f"🧠 [Aguacate] Entrenando modelo con {len(X)} registros...")
        new_model = LinearRegression()
        new_model.fit(X, y)
        
        # 4. Evaluar el modelo
        y_pred = new_model.predict(X)
        r2 = r2_score(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        
        print(f"✅ [Aguacate] Modelo entrenado: R²={r2:.4f}, MSE={mse:.4f}")
        
        # 5. Guardar el modelo
        with open(MODEL_FILE, "wb") as f:
            pickle.dump(new_model, f)
        print(f"💾 [Aguacate] Modelo guardado en {MODEL_FILE}")
        
        # 6. Actualizar variables globales
        model = new_model
        model_loaded = True
        last_training_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        training_data_count = len(X)
        last_error = None
        
        # 7. Subir a Supabase (no crítico)
        try:
            upload_model_to_supabase()
        except Exception as e:
            print(f"⚠️ [Aguacate] No se pudo subir a Supabase: {e}")
        
        return {
            "status": "success",
            "records": training_data_count,
            "r2_score": round(r2, 4),
            "mse": round(mse, 4),
            "date": last_training_date,
            "features_used": features
        }
        
    except (CSVNotFoundError, CSVInvalidError, TrainingError) as e:
        model_loaded = False
        last_error = str(e)
        print(f"❌ [Aguacate] Error: {e}")
        raise e
        
    except Exception as e:
        model_loaded = False
        last_error = str(e)
        print(f"❌ [Aguacate] Error inesperado: {e}")
        print(traceback.format_exc())
        raise TrainingError(f"Error inesperado durante el entrenamiento: {str(e)}")

def load_or_train_model():
    """
    Función principal: intenta cargar desde Supabase, si falla, entrena desde CSV.
    """
    global model, model_loaded, last_error
    
    print("🚀 [Aguacate] Iniciando carga de modelo...")
    
    # 1. Intentar descargar desde Supabase
    if download_model_from_supabase() and MODEL_FILE.exists():
        try:
            with open(MODEL_FILE, "rb") as f:
                model = pickle.load(f)
            model_loaded = True
            last_error = None
            print("✅ [Aguacate] Modelo cargado desde Supabase")
            return True
        except Exception as e:
            print(f"⚠️ [Aguacate] Error al cargar modelo descargado: {e}")
    
    # 2. Intentar cargar modelo local
    if MODEL_FILE.exists():
        try:
            with open(MODEL_FILE, "rb") as f:
                model = pickle.load(f)
            model_loaded = True
            last_error = None
            print("✅ [Aguacate] Modelo cargado desde archivo local")
            return True
        except Exception as e:
            print(f"⚠️ [Aguacate] Modelo local corrupto: {e}")
    
    # 3. Entrenar desde CSV
    try:
        print("🔄 [Aguacate] Entrenando modelo desde CSV...")
        result = train_model_from_csv()
        if result['status'] == 'success':
            print("✅ [Aguacate] Modelo entrenado exitosamente")
            return True
    except Exception as e:
        last_error = str(e)
        print(f"❌ [Aguacate] Error al entrenar: {e}")
        return False
    
    return False

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "service": app.title,
        "status": "running",
        "model_loaded": model_loaded,
        "last_training": last_training_date,
        "training_records": training_data_count,
        "last_error": last_error,
        "csv_exists": DATASET_FILE.exists(),
        "csv_path": str(DATASET_FILE)
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

    model_ready = model is not None and model_loaded
    status_code = "healthy" if db_status == "connected" and model_ready else "degraded"

    return {
        "status": status_code,
        "database": db_status,
        "model_loaded": model_ready,
        "last_training": last_training_date,
        "training_records": training_data_count,
        "last_error": last_error,
        "db_error": db_error,
        "csv_exists": DATASET_FILE.exists(),
        "csv_path": str(DATASET_FILE)
    }

@app.get("/diagnostico")
async def diagnostico():
    """Diagnóstico completo de la API"""
    import sys
    
    csv_info = {}
    if DATASET_FILE.exists():
        try:
            data = pd.read_csv(DATASET_FILE)
            csv_info = {
                "exists": True,
                "rows": len(data),
                "columns": list(data.columns),
                "size_bytes": DATASET_FILE.stat().st_size,
                "path": str(DATASET_FILE)
            }
        except Exception as e:
            csv_info = {"exists": True, "error": str(e)}
    else:
        csv_info = {
            "exists": False,
            "expected_path": str(DATASET_FILE),
            "base_dir": str(BASE_DIR),
            "files_in_base_dir": [str(f.name) for f in BASE_DIR.iterdir()] if BASE_DIR.exists() else []
        }
    
    return {
        "model_loaded": model_loaded,
        "last_training": last_training_date,
        "training_records": training_data_count,
        "last_error": last_error,
        "csv": csv_info,
        "supabase": {
            "url": SUPABASE_URL,
            "bucket": SUPABASE_BUCKET,
            "model_name": SUPABASE_MODEL_NAME
        },
        "python_version": sys.version,
        "dependencias": {
            "sklearn": __import__('sklearn').__version__,
            "pandas": __import__('pandas').__version__,
            "numpy": __import__('numpy').__version__
        }
    }

@app.get("/debug/files")
async def debug_files():
    """Lista todos los archivos en el directorio"""
    try:
        files = []
        for item in BASE_DIR.iterdir():
            files.append({
                "name": item.name,
                "is_file": item.is_file(),
                "size": item.stat().st_size if item.is_file() else 0
            })
        
        return {
            "base_dir": str(BASE_DIR),
            "files": files,
            "csv_exists": DATASET_FILE.exists(),
            "csv_path": str(DATASET_FILE),
            "model_exists": MODEL_FILE.exists(),
            "model_path": str(MODEL_FILE)
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/aguacate/quote")
async def quote_aguacate(data: AguacateRequest):
    """Endpoint principal de cotización"""
    global model, model_loaded
    
    # 1. Verificar que el modelo está cargado
    if not model_loaded or model is None:
        # Intentar recargar/entrenar
        success = load_or_train_model()
        
        if not model_loaded or model is None:
            raise HTTPException(
                status_code=503,
                detail=f"Modelo no disponible. Error: {last_error or 'Desconocido'}"
            )
    
    try:
        # 2. Validar entrada
        if data.service_id not in [1, 2]:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de servicio inválido: {data.service_id}. Tipos válidos: 1, 2"
            )
        
        if data.batch_weight_kg <= 0:
            raise HTTPException(
                status_code=400,
                detail="El peso del lote debe ser mayor a 0"
            )
        
        if data.cooling_hours < 0:
            raise HTTPException(
                status_code=400,
                detail="Las horas de enfriamiento no pueden ser negativas"
            )
        
        if data.electricity_kwh_rate <= 0:
            raise HTTPException(
                status_code=400,
                detail="La tarifa eléctrica debe ser mayor a 0"
            )
        
        # 3. Preparar datos para predicción
        input_df = pd.DataFrame([{
            "service_id": data.service_id,
            "batch_weight_kg": data.batch_weight_kg,
            "cooling_hours": data.cooling_hours,
            "electricity_kwh_rate": data.electricity_kwh_rate,
            "ipc_factor": latest_ipc_factor
        }])
        
        # 4. Hacer la predicción
        prediction = model.predict(input_df)
        unit_price_kg = round(max(0.03, float(prediction[0])), 3)
        total = round(unit_price_kg * data.batch_weight_kg, 2)
        
        # 5. Guardar en base de datos (no crítico)
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
        
        # 6. Devolver respuesta
        return {
            "quote_id": quote_id,
            "unit_price_per_kg_usd": unit_price_kg,
            "total_usd": total,
            "weight_kg": data.batch_weight_kg
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [Aguacate] Error en quote_aguacate: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la cotización: {str(e)}"
        )

@app.post("/api/aguacate/retrain")
async def retrain_model():
    """Endpoint para forzar el re-entrenamiento del modelo desde CSV"""
    try:
        result = train_model_from_csv()
        return {
            "status": "success",
            "message": "Modelo re-entrenado exitosamente",
            "details": result
        }
    except CSVNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CSVInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TrainingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

# ============================================
# INICIALIZACIÓN
# ============================================

print("=" * 60)
print("🚀 INICIANDO API DE AGUACATE (A1)")
print("=" * 60)
print(f"📁 BASE_DIR: {BASE_DIR}")
print(f"📄 DATASET_FILE: {DATASET_FILE}")
print(f"📄 ¿Existe CSV? {DATASET_FILE.exists()}")
print(f"📄 MODEL_FILE: {MODEL_FILE}")
print(f"☁️ Supabase configurada: {'Sí' if SUPABASE_URL else 'No'}")
print("=" * 60)

# Listar archivos para debug
try:
    files = list(BASE_DIR.iterdir())
    print(f"📂 Archivos en {BASE_DIR}:")
    for f in files:
        print(f"   - {f.name} ({'📄' if f.is_file() else '📁'})")
except Exception as e:
    print(f"⚠️ Error al listar archivos: {e}")
print("=" * 60)

# Inicializar el modelo
if not load_or_train_model():
    print("⚠️ API iniciada SIN modelo.")
    print(f"📝 Error: {last_error}")
    print("🔧 Usa /health para verificar el estado")
    print("📊 Usa /diagnostico para más detalles")
else:
    print("✅ API lista para usar")
    if model_loaded:
        print(f"📊 {training_data_count} registros en entrenamiento")
        print(f"📅 Último entrenamiento: {last_training_date}")

print("📍 Endpoints disponibles:")
print("  - GET  /")
print("  - GET  /health")
print("  - GET  /diagnostico")
print("  - GET  /debug/files")
print("  - POST /api/aguacate/quote")
print("  - POST /api/aguacate/retrain")