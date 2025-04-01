1. Собираем докер образ: "docker build -t fast_api:latest ."
2. Посмотреть список образов: "docker image list"
3. Запускаем в докер контейнер: "docker run -d -p 9005:8005 fast_api" # запуск сервиса в фоне на 9005 -p 9005:8005 (host port:docker port) 
4. Открываем сервис по localhost:9005 
5. Посмотреть список контейнеров "docker ps -a"
6. Лог контейнера "docker logs 'id'" #id контейнера