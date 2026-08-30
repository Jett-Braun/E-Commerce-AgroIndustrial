FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY dataset.csv /app/dataset.csv

RUN echo "=== CSV EN EL CONTENEDOR ===" && \
    ls -la /app/dataset.csv && \
    echo "=== PRIMERAS LÍNEAS ===" && \
    head -5 /app/dataset.csv && \
    echo "=== FIN ==="

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]