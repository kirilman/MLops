FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и данные
COPY app/main.py app/main.py
COPY app/cars.csv app/cars.csv

EXPOSE 8081

# Запуск приложения
CMD ["python", "app/main.py"]