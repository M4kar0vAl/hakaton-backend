# Backend проекта W2W

## Для развертывания в докере:

### Через команды докера

   1. Перейти в корень проекта.

   2. Запуск БД:
      ```commandline
      docker compose -f ./docker-compose/storages.yml up --build -d
      ```
   
   3. Запуск приложения:
      ```commandline
      docker compose --env-file example.env -f ./docker-compose/app.yml up --build -d
      docker exec -it django python manage.py migrate
      ```
   
   4. Приложение будет доступно на локальном интерфейсе: `http://localhost/` или `http://127.0.0.1/`
   
   5. Запуск периодических задач (`celery`):
      ```commandline
      docker compose -f ./docker-compose/celery.yml up --build -d
      ```

   6. Остановить контейнеры:
      ```commandline
      docker compose -f ./docker-compose/celery.yml down
      docker compose -f ./docker-compose/app.yml down
      docker compose -f ./docker-compose/storages.yml down
      ```

### Через make

   1. Перейти в корень проекта.

   2. Запустить все приложение:
      ```commandline
      make run
      ```
   
   3. Приложение будет доступно на локальном интерфейсе: `http://localhost/` или `http://127.0.0.1/`
   
   4. Запустить выполнение периодических задач:
      ```commandline
      make celery
      ```

   5. Остановить контейнеры:
      ```commandline
      make down
      ```

## Для разработки:

1. Вместо `pip` используется `poetry`, после создания виртуального окружения установите через `pip`:
`pip install poetry`
2. Установка `dev` зависимостей:
`poetry install --no-root --without prod`

3. Вы можете добавлять собственные группы зависимостей через `poetry`, которые нужны вам только для локальной работы.
4. В `local_settings.py` (нужно создать рядом с `settings.py`, он добавлен в гитигнор) можете указать удобное для вас подключение к БД и иные настройки.
5. Если вы дебажите запуская приложение без контейнера а БД в контейнере в `.env` измените хост БД на `localhost`.

### Создание новых приложений в проекте

1. Создать в пакете `core/apps/` папку (без `__init__.py`) в соответствии с названием приложения.
2. Запустить команду с указанием пути, где создать приложение: `python3 manage.py startapp new-app core/apps/new-app-folder` 
3. В `settings.INSTALLED_APPS` указывайте полный путь до приложения:
   ```python
   INSTALLED_APPS = [
       ...
       "core.apps.app-name.apps.ConfigName",
   ]
   ```
4. В приложении в `apps.py` в поле `name` конфигурации указать путь до приложения: `core.apps.<app-name>`

### API docs
`http://localhost/api/docs/`
