# Сборка и запуск всех сервисов
docker compose up -d --build

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f


#добавление соединения в airflow
docker-compose exec airflow-apiserver airflow connections add 'carsapi' \
    --conn-type 'http' \
    --conn-host 'carsapi' \
    --conn-port '8081' \
    --conn-schema 'http' \
    --conn-login 'airflow' \
    --conn-password 'airflow'


#
x-airflow-common:
  &airflow-common
  environment:
    &airflow-common-env
    # ... существующие переменные ...
    
    # ← Добавьте эту строку:
    AIRFLOW_CONN_CARSAPI: 'http://airflow:airflow@carsapi:8081'