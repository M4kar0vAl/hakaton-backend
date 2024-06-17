# Документация chat

## Эндпоинты

1. `ws://localhost:8000/ws/chat/`
   - обычный чат, где общаются бренды после метча
   - присоединиться могут только к комнатам, где состоит сам бренд (после метча)
   - писать сообщения можно только присоединившись к комнате
2. `ws://localhost:8000/ws/admin-chat/`
   - чат для админов (для подключения нужно иметь права администратора)
   - присоединиться могут только к комнате, где есть бизнес тариф
   - писать сообщения могут только в чат, где есть бизнес тариф
   - писать сообщения можно только присоединившись к комнате

## Авторизация

- Указать access токен в Authorization хедере запроса.
  - Пример (Bearer и токен через пробел):
  - Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE4MjE1Mzc4LCJpYXQiOjE3MTgyMTM1NzgsImp0aSI6IjA2MzdhOTJiN2UyNzQxMThiMGEwZTkyZGViODU1NzYxIiwidXNlcl9pZCI6MX0.qLnRLCoIOjJN6_XKvGvkDMQSC52fO-cliZVJIwbHEIE
- Авторизовываться нужно только при подключении. Соединение не закрывается после каждого запроса.

## Actions

1. Для `ws://localhost:8000/ws/chat/`:
   - Необходимые разрешения:
     - Пользователь должен быть авторизованным
   - `list` - получить список всех комнат
     - Параметры:
       - `action`: str - название action
       - `request_id`: int - уникальный id запроса (можно указать текущую дату-время в миллисекундах)
     - Пример запроса:
       - ```json
         {
            "action": "list",
            "request_id": 1500000
         }
         ```
     - Пример ответа:
       - ```json
         {
            "errors": [],
            "data": [],
            "action": "list",
            "response_status": 200,
            "request_id": 1500000
         }
         ```
   - `join_room` - присоединиться к комнате
     - Параметры:
       - `action`: str - название action
       - `room_pk`: int - первичный ключ комнаты, куда присоединиться
       - `request_id`: int - уникальный id запроса (можно указать текущую дату-время в миллисекундах)
     - Пример запроса:
       - ```json
         {
            "action": "join_room",
            "room_pk": 1,
            "request_id": 1500000
         }
         ```
     - Пример ответа:
       - В качестве ответа приходит комната в формате json, которую указали в запросе
       - `participants` - список из двух объектов (структура такая же как у брендов, см. по http://127.0.0.1:8000/api/docs/)
       - ```json
         {
            "errors": [],
            "data": {
              "pk": 1,
              "participants": [
                {},
                {}
              ],
              "has_business": true
            },
            "action": "join_room",
            "response_status": 200,
            "request_id": 1500000
         }
         ```
   - `leave_room` - выйти из комнаты
     - `room_pk` не передается, выходит из текущей комнаты
     - Параметры:
       - `action`: str - название action
       - `request_id`: int - уникальный id запроса (можно указать текущую дату-время в миллисекундах)
       - Пример запроса:
         - ```json
           {
              "action": "leave_room",
              "request_id": 1500000
           }
           ```
       - Пример ответа:
         - ```json
           {
              "errors": [],
              "data": {
                "response": "leaved room 1 successfully!"
              },
              "action": "leave_room",
              "response_status": 200,
              "request_id": 1500000
           }
           ```
   - `create_message` - написать сообщение
     - `room_pk` не передается, отправляет в текущую комнату
     - Параметры:
       - `action`: str - название action
       - `msg_text`: str - текст сообщения
       - `request_id`: int - уникальный id запроса (можно указать текущую дату-время в миллисекундах)
     - Пример запроса:
       - ```json
         {
            "action": "create_message",
            "msg_text": "hello",
            "request_id": 1500000
         }
         ```
     - Пример ответа:
       - `user` и `participants` имеет структуру пользователя и бренда соответственно (см. по http://127.0.0.1:8000/api/docs/)
       - ```json
         {
            "errors": [],
            "data": {
              "text": "hello",
              "user": {},
              "created_at": "2024-06-17T18:00:00.000Z",
              "room": {
              "pk": 1,
              "participants": [
                {},
                {}
              ],
              "has_business": true
              }
            },
            "action": "create_message",
            "response_status": 200,
            "request_id": 1500000
         }
         ```
   - `current_room_info` - получить информацию о текущей комнате
     - Параметры:
       - `action`: str - название action
       - `request_id`: int - уникальный id запроса (можно указать текущую дату-время в миллисекундах)
     - Пример запроса:
       - ```json
         {
            "action": "current_room_info",
            "request_id": 1500000
         }
         ```
     - Пример ответа:
       - ```json
         {
            "errors": [],
            "data": {
              "pk": 1,
              "participants": [
                {},
                {}
              ],
              "has_business": true
            },
            "action": "current_room_info",
            "response_status": 200,
            "request_id": 1500000
         }
         ```
2. Для `ws://localhost:8000/ws/admin-chat/`:
   - Необходимые разрешения:
     - Пользователь должен быть администратором
   - Все те же actions, что и в обычном чате, но без `current_room_info`
