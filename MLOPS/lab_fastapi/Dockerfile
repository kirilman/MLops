# app/Dockerfile
#базовый образ
FROM python:3.10-slim 
#рабочая директория проекта
WORKDIR /fast_app            
# RUN apt-get update && apt-get install 
# COPY requirements.txt .
COPY . .    
RUN pip3 install -r ./requirements.txt
#порт для взаимодействия с контейнером
EXPOSE 8005
#
CMD ["python", "./main.py"] 