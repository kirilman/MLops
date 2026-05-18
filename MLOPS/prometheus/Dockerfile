# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Установка системных утилит для мониторинга (как в лекции)
RUN apt-get update && apt-get install -y \
    net-tools \
    htop \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Проверка что модели есть
RUN ls -la *.joblib || echo "Warning: Model files not found"

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["python", "main.py"]