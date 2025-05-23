DC = docker compose
EXEC = docker exec -it
LOGS = docker logs
ENV = --env-file .env
APP_FILE = ./docker-compose/app.yml
STORAGE_FILE = ./docker-compose/storages.yml
CELERY_FILE = ./docker-compose/celery.yml
APP_CONTAINER = django
DB_CONTAINER = w2w_db
MANAGE = python manage.py


.PHONY: run
run:
	${DC} -f ${STORAGE_FILE} up --build -d
	${DC} -f ${APP_FILE} up --build -d
	${EXEC} ${APP_CONTAINER} ${MANAGE} migrate
	${DC} -f ${CELERY_FILE} up --build -d celery_worker

.PHONY: app
app:
	${DC} -f ${APP_FILE} up --build -d

.PHONY: debug
debug:
	${MANAGE} runserver

.PHONY: stor
stor:
	${DC} -f ${STORAGE_FILE} up -d

.PHONY: app-logs
app-logs:
	${LOGS} ${APP_CONTAINER} -f

.PHONY: db-logs
db-logs:
	${LOGS} ${DB_CONTAINER} -f

.PHONY: app-down
app-down:
	${DC} -f ${APP_FILE} down

.PHONY: down
down:
	${DC} -f ${CELERY_FILE} down
	${DC} -f ${APP_FILE} down
	${DC} -f ${STORAGE_FILE} down

.PHONY: migrate
migrate:
	${EXEC} ${APP_CONTAINER} ${MANAGE} migrate

.PHONY: migrations
migrations:
	${EXEC} ${APP_CONTAINER} ${MANAGE} makemigrations

.PHONY: app-bash
app-bash:
	${EXEC} ${APP_CONTAINER} bash

.PHONY: app-shell
app-shell:
	${EXEC} ${APP_CONTAINER} bash -c "${MANAGE} shell"

.PHONY: test
test:
	${EXEC} ${APP_CONTAINER} bash -c "${MANAGE} test"

.PHONY: cities
cities:
	${EXEC} ${APP_CONTAINER} ${MANAGE} cities_light --progress

.PHONY: celery
celery:
	${DC} -f ${CELERY_FILE} up --build -d

.PHONY: worker
worker:
	${DC} -f ${CELERY_FILE} up --build -d celery_worker
