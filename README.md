# Для развертывания в докере:
1. Через команды докера

   1.1 Перейти в корень проекта.

   1.2 Запуск БД:
      ```
      docker compose -f ./docker-compose/storages.yml up -d
      ```
   1.3 Запуск приложения:
      ```
      docker compose --env-file example.env -f ./docker-compose/app.yml up --build -d
      docker exec -it django python manage.py migrate
      ```
   1.4 Приложение будет доступно на локальном интерфейсе: `http://localhost/` или `http://127.0.0.1/`
   
   1.5 Остановить контейнеры:

      ```angular2html
      docker compose -f ./docker-compose/storages.yml down
      docker compose --env-file example.env -f ./docker-compose/app.yml down
      ```
2. Через make

   2.1 Перейти в корень проекта.

   2.2 Запустить все приложение:
      ```
      make run
      ```
   2.3 Приложение будет доступно на локальном интерфейсе: `http://localhost/` или `http://127.0.0.1/`
   
   2.4 Остановить контейнеры:

      ```angular2html
      make down
      ```

# Для разработки:
1. Вместо pip используется poetry, после создания виртуального окружения установите через pip:
`pip install poetry`
2. Установка dev зависимостей:
`poetry install --no-root --without prod`

3. Вы можете добавлять собственные группы зависимостей через poetry, которые нужны вам только для локальной работы.
4. В local_settings.py (нужно создать рядом с settings.py, он добавлен в гитигнор) можете указать удобное для вас подключение к БД и иные настройки.
5. Если вы дебажите запуская приложение без контейнера а БД в контейнере в .env измените хост БД на localhost.

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
4. В приложении в `apps.py` в поле name конфигурации указать путь до приложения: `core.apps.<app-name>`

### Fake data
1. Персонал:

   Первый пользователь: email: staff@example.com, phone: +79998884422, password: Pass!234
   Второй пользователь: email: admin@example.com, phone: +79993332211, password: Pass!234

2. Промокоды: discount5, discount10

### API docs
`http://localhost/api/docs/`