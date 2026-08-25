FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar librerías en C
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del microservicio
COPY . .

# Puerto expuesto para Render
EXPOSE 8000

# Comando de inicio con manejo de keep-alive
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]