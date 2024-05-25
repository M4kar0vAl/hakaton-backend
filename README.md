# Для развертывания в докере:
1. Перейти в корень проекта.
2. Запуск БД:

    ``docker compose -f ./docker-compose/storages.yml up -d``
3. Запуск приложения:

    ``docker compose --env-file example.env -f ./docker-compose/app.yml up --build -d``

4. Приложение будет доступно на локальном интерфейсе: `http://localhost:8000/` или `http://127.0.0.1:8000/`
5. Остановить контейнеры:

   ```angular2html
   docker compose -f ./docker-compose/storages.yml down
   docker compose --env-file example.env -f ./docker-compose/app.yml down
   ```
# Для разработки:
1. Вместо pip используется poetry, для windows установка зависимостей:
`poetry install --no-root --without unix`

   для unix:
`poetry install --no-root --without win`
2. Вы можете добавлять собственные группы зависимостей через poetry, которые нужны вам только для локальной работы.
3. В local_settings.py (нужно создать рядом с settings.py, он добавлен в гитигнор) можете указать удобное для вас подключение к БД и иные настройки.
4. Если вы дебажите запуская приложение без контейнера а БД в контейнере в .env измените хост БД на localhost.

### Создание новых приложений в проекте
1. Создать в пакете core/apps/ папку (без \_\_init__.py) в соответствии с названием приложения.
2. Запустить команду с указанием пути, где создать приложение: `python3 manage.py startapp new-app core/apps/new-app-folder` 
3. В settings.INSTALLED_APPS указывайте полный путь до приложения:
   ```angular2html
   INSTALLED_APPS = [
       ...
       "core.apps.app-name.apps.ConfigName",
   ]
   ```
