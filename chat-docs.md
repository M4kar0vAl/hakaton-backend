# Документация chat

## Эндпоинты

### `ws://localhost:80/ws/chat/`

- обычный чат, где общаются бренды после метча
- присоединиться могут только к комнатам, где состоит сам бренд (после метча)
- писать/редактировать/удалять сообщения можно только присоединившись к комнате
- редактировать/удалять могут только свои сообщения и только в той комнате, к которой сейчас подключены

### `ws://localhost:80/ws/admin-chat/`

- чат для админов (для подключения нужно иметь права администратора)
- присоединиться могут к любой комнате, чтобы просматривать сообщения
- писать/редактировать/удалять сообщения могут только в чате, где есть бизнес тариф
- писать/редактировать/удалять сообщения можно только присоединившись к комнате
- редактировать могут только свои сообщения
- удалять могут любые сообщения в текущей комнате

## Авторизация

- Указать access токен в `Authorization` хедере запроса.
  - Пример (Bearer и токен через пробел):
    ```
    Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE4MjE1Mzc4LCJpYXQiOjE3MTgyMTM1NzgsImp0aSI6IjA2MzdhOTJiN2UyNzQxMThiMGEwZTkyZGViODU1NzYxIiwidXNlcl9pZCI6MX0.qLnRLCoIOjJN6_XKvGvkDMQSC52fO-cliZVJIwbHEIE
    ```
- Авторизовываться нужно только при подключении. Соединение не закрывается после каждого запроса.

## Необходимые Headers для соединения

- ```
  Authorization Bearer <access токен>
  ```
- ```
  Origin http://localhost:80
  ```
  - (указываете схему, хост и порт, с которых пытаетесь подключиться)

## Actions

### `ws://localhost:80/ws/chat/`

#### Необходимые разрешения

- Пользователь должен быть **авторизованным**

#### `list`

_**Получить список всех комнат, в которых состоит текущий бренд**_

##### Параметры

- `action`: str - _название action_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "list",
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": [
    {
      "pk": 1,
      "participants": [
        {},
        {}
      ],
      "has_business": true
    },
    {
      "pk": 2,
      "participants": [
        {},
        {}
      ],
      "has_business": false
    }
  ],
  "action": "list",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```

#### `join_room`

_**Присоединиться к комнате**_

##### Параметры

- `action`: str - _название action_
- `room_pk`: int - _первичный ключ комнаты, куда присоединиться_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "join_room",
  "room_pk": 1,
  "request_id": 1500000
}
```

##### Пример ответа

В качестве ответа приходит комната в формате json, которую указали в запросе

`participants` - список из двух объектов (структура такая же как у брендов, см. по http://127.0.0.1:80/api/docs/)

```json
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

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **403**
  - ```
    "errors": ["You cannot enter a room you are not a member of"]
    ```

#### `leave_room`

_**Выйти из комнаты**_

`room_pk` не передается, выходит из текущей комнаты

##### Параметры

- `action`: str - _название action_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "leave_room",
  "request_id": 1500000
}
```

##### Пример ответа

```json
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

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action 'leave_room' not allowed. You are not in the room"]
    ```

#### `get_room_messages`

_**Получить все сообщения комнаты**_

`room_pk` не передается, отправляет сообщения текущей комнаты

##### Параметры

- `action`: str - _название action_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "get_room_messages",
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": [
    {
      "id": 1,
      "user": {
        "id": 2,
        "email": "admin@example.com",
        "phone": "+79993332211",
        "telegram_link": "https://t.me/W2W_Match_Hakaton_Bot?start=Mg"
      },
      "room": 1,
      "text": "Test message",
      "created_at": "2024-06-20T13:27:06.746701Z"
    }
  ],
  "action": "get_room_messages",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```

#### `create_message`

_**Написать сообщение**_

`room_pk` не передается, отправляет в текущую комнату

##### Параметры

- `action`: str - _название action_
- `msg_text`: str - _текст сообщения_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "create_message",
  "msg_text": "hello",
  "request_id": 1500000
}
```

##### Пример ответа

`user` и `participants` имеет структуру пользователя и бренда соответственно (см. по http://127.0.0.1:80/api/docs/)

```json
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
  "response_status": 201,
  "request_id": 1500000
}
```

##### Возможные статусы

- **201**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```

#### `edit_message`

_**Редактировать сообщение**_

`room_pk` не передается, ищет сообщение в текущей комнате

##### Параметры

- `action`: str - _название action_
- `msg_id`: int - _идентификатор сообщения_
- `edited_msg_text`: str - _новый текст сообщения_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "edit_message",
  "msg_id": 1,
  "edited_msg_text": "edited_text",
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": {
    "room_id": 7,
    "message_id": 1,
    "message_text": "edited_text"
  },
  "action": "edit_message",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **404**
  - ```
    "errors": ["Message with id: {msg_id} and user: {current_user.email} not found! Check whether the user is the author of the message and the id is correct!"]
    ```
#### `delete_messages`

_**Удалить одно или больше сообщений**_

`room_pk` не передается, ищет сообщения в текущей комнате

##### Параметры

- `action`: str - _название action_
- `msg_id_list`: list[int] - _список идентификаторов сообщений (для удаления одного сообщения передавать список, а не int: [123])_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "delete_messages",
  "msg_id_list": [1],
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": {
    "room_id": 7,
    "messages_ids": [
      1
    ]
  },
  "action": "delete_messages",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
  - ```
    "errors": ["Not all of the requested messages were deleted! Check whether the user is the author of the message and the ids are correct! Check if messages belong to the current user's room!"]
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **404**
  - ```
    "errors": ["Messages with ids: {msg_id_list} were not found! Nothing was deleted!"]
    ```

#### `current_room_info`

_**Получить информацию о текущей комнате**_

##### Параметры

- `action`: str - _название action_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "current_room_info",
  "request_id": 1500000
}
```

##### Пример ответа

```json
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

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```

### `ws://localhost:80/ws/admin-chat/`

**_Все те же actions, что и в обычном чате, но без `current_room_info`._**

**_У некоторых actions изменено поведение (см. ниже)_**

#### Необходимые разрешения

- Пользователь должен быть **администратором**

#### Права

- Просматривать сообщения можно в **любой** комнате
- `create_message`, `edit_message`, `delete_messages` доступны только в комнате с брендом, у которого бизнес тариф

#### `list`

**_Возвращает список **всех** комнат_**

#### `join_room`

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```

#### `create_message`

##### Возможные статусы

- **201**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **403**
  - ```
    "errors": ["Action not allowed. You cannot write to a chat that does not have brand with business subscription!"]
    ```

#### `edit_message`

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **403**
  - ```
    "errors": ["Action not allowed. You cannot write to a chat that does not have brand with business subscription!"]
    ```
- **404**
  - ```
    "errors": ["Message with id: {msg_id} and user: {current_user.email} not found! Check whether the user is the author of the message and the id is correct!"]
    ```

#### `delete_messages`

**_Позволяет удалять любые сообщения в текущей комнате_**

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
  - ```
    "errors": ["Not all of the requested messages were deleted! Check whether the ids are correct and messages belong to the current user's room!"]
    ```
- **400**
  - ```
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **403**
  - ```
    "errors": ["Action not allowed. You cannot write to a chat that does not have brand with business subscription!"]
    ```
- **404**
  - ```
    "errors": ["Messages with ids: {msg_id_list} were not found! Nothing was deleted!"]
    ```
