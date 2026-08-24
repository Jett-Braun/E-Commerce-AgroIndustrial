cat > README.md << 'EOF'
# Sistema de Cotizaciones Agroindustriales

## Arquitectura
- **C1**: API de Café (FastAPI)
- **A1**: API de Aguacate (FastAPI)
- **M1**: API de Maquinaria (FastAPI)
- **Frontend**: PHP/HTML

## Despliegue en Render

### APIs
Cada API se despliega como un Web Service independiente:
- `c1/` → https://c1-xxxx.onrender.com
- `a1/` → https://a1-xxxx.onrender.com
- `m1/` → https://m1-xxxx.onrender.com

### Frontend
El frontend se despliega como Web Service PHP:
- `frontend/` → https://frontend-xxxx.onrender.com

## Variables de Entorno
- `DB_HOST`: Host de MySQL
- `DB_PORT`: Puerto de MySQL
- `DB_USER`: Usuario de MySQL
- `DB_PASSWORD`: Contraseña de MySQL
- `DB_NAME`: Nombre de la base de datos

## Modelos de IA
Los modelos `.pkl` se entrenan automáticamente al desplegar.
EOF