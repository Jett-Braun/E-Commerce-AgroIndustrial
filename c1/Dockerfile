FROM python:3.11-slim

WORKDIR /app

# 🔥 Instalar dependencias del sistema para mysql-connector
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 🔥 Puerto que usa Render
EXPOSE 8000

# 🔥 Comando de inicio con timeout aumentado
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]