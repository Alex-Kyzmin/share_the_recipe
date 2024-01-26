**О проекте share the recipe**.

Cайт, на котором пользователи могут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Пользователям сайта также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

адрес домена - yoursfoodgram.hopto.org;
админ - Alex;
пароль админа - Rxh-JZ4-Eqe-sX6;

## Проект содержит страницы:
    - Главная страница содержит список первых шести рецептов с возможностью постраничной пагинации.
    - Страница рецепта содержит полное описание рецепта с возможностью добавления в избранное и список покупок.
    - Страница пользователя содержит имя пользователя, все опубликованные рецепты и возможность подписаться на автора.
    - Страница подписок доступна только для владельца аккаунта и содержит список рецептов, на которые подписан пользователь.

а так же страницы избранных рецептов, список покупок для приготовления рецеатов, создание и редактирование рецепта

**Технологии проекта**:
Python, Django, Django Rest Framework, Docker, Gunicorn, NGINX, React, PostgreSQL, CI/CD.

# Как развернуть проект на удаленном сервере:
    1. Клонируйте репозиторий (git clone "ссылка с GitHub")
    2. Установите на сервере Docker, Docker Compose следующими командами:
        - sudo apt install curl (установка утилиты для скачивания файлов);
        - curl -fsSL https://get.docker.com -o get-docker.sh (скачать скрипт для установки);
        - sh get-docker.sh (запуск скрипта);
        - sudo apt-get install docker-compose-plugin (последняя версия docker compose);
    3. Скопируйте на сервер файлы docker-compose.yml, nginx.conf из папки infra (команды выполнять находясь в папке infra):
        - scp docker-compose.yml nginx.conf username@IP:/home/username/ (username - имя пользователя на сервере, IP - публичный IP сервера)
    4. Для работы с GitHub Actions необходимо в репозитории в разделе Secrets > Actions создать переменные окружения:

        SECRET_KEY              # секретный ключ Django проекта
        DOCKER_PASSWORD         # пароль от Docker Hub
        DOCKER_USERNAME         # логин Docker Hub
        HOST                    # публичный IP сервера
        USER                    # имя пользователя на сервере
        PASSPHRASE              # *если ssh-ключ защищен паролем
        SSH_KEY                 # приватный ssh-ключ
        TELEGRAM_TO             # ID телеграм-аккаунта для посылки сообщения
        TELEGRAM_TOKEN          # токен бота, посылающего сообщение

        DB_ENGINE               # django.db.backends.postgresql
        POSTGRES_DB             # postgres
        POSTGRES_USER           # postgres
        POSTGRES_PASSWORD       # postgres
        DB_HOST                 # db
        DB_PORT                 # 5432 (порт по умолчанию)

    5. Создайте и запустите контейнеры Docker командой:
        - sudo docker compose up -d
    6. Выполните миграции командой:
        - sudo docker compose exec backend python manage.py migrate
    7. Создать суперпользователя командой:
        - sudo docker compose exec backend python manage.py createsuperuser
    8. Собирите статические файлы командой:
        - sudo docker compose exec backend python manage.py collectstatic --noinput
    9. Загрузите в БД данными ингридиентов и тегов (или создайте сами в админ-зоне проекта суперпользователем):
        - sudo docker compose exec backend python manage.py loaddata ingredients_and_tags.json

    Примечание - для остановки контейнеров Docker:
        - sudo docker compose down -v (их удалением);
        - sudo docker compose stop (без удаления);

## После обновления репозитория (командой из IDE- git push):
    - Код будет проходить соответствие стандарту PEP8 и правильности импорта библиотек;
    - CI/CD проверка (обновление докер-образов в docker hub и обновленное развертывание проекта на удаленном сервере)
    - Отправка сообщения в Telegram в случае успеха.

## Разаработчики:
    - frontend: Команда яндекс-практикум;
    - backend and CI/CD: Александр Кузьмин.
