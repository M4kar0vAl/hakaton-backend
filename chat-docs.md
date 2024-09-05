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
- писать/редактировать/удалять сообщения могут только в комнатах поддержки и помощи. В комнатах метчей могут только если это их метч (соответственно если у админа есть бренд, вероятно это только для самого W2W бренда)
- писать/редактировать/удалять сообщения можно только присоединившись к комнате
- редактировать/удалять могут только свои сообщения

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

`participants` - id пользователей (не брендов)
`interlocutors_brand` - короткая информация о бренде собеседника, используйте ее для отрисовки списка чатов. Когда пользователь захочет подробно про бренд посмотреть делайте запрос на `/api/v1/brand/{id}/` для получения всей информации.

Для комнат поддержки/помощи `interlocutors_brand` вернет `null`. Возможно, потом заменю на бренд агентство W2W.

```json
{
  "errors": [],
  "data": [
    {
      "id": 1,
      "last_message": {
        "id": 1,
        "room": 1,
        "text": "text",
        "created_at": "2024-09-04T11:22:02.474470Z",
        "user": 1
      },
      "interlocutors_brand": {
        "id": 1,
        "brand_name_pos": "text",
        "fullname": "text",
        "logo": "path",
        "photo": "path",
        "product_photo": "path",
        "category": {
          "text": "text"
        }
      },
      "has_business": true,
      "type": "M",
      "participants": [
        1,
        2
      ]
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

```json
{
  "errors": [],
  "data": {
    "id": 1,
    "last_message": {
      "id": 1,
      "room": 1,
      "text": "text",
      "created_at": "2024-09-04T11:22:02.474470Z",
      "user": 1
    },
    "interlocutors_brand": {
      "id": 1,
      "brand_name_pos": "text",
      "fullname": "text",
      "logo": "path",
      "photo": "path",
      "product_photo": "path",
      "category": {
        "text": "text"
      }
    },
    "has_business": true,
    "type": "M",
    "participants": [
      1,
      2
    ]
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

> [!NOTE]
> Теперь вместо информации о пользователе возвращается его id

```json
{
  "errors": [],
  "data": [
    {
      "id": 1,
      "user": 1,
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

```json
{
  "errors": [],
  "data": {
    "id": 1,
    "room": 1,
    "text": "test",
    "created_at": "2024-09-05T13:02:46.859077Z",
    "user": 1
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
    "id": 1,
    "last_message": {
      "room": null,
      "text": "",
      "user": null
    },
    "interlocutors_brand": {
      "id": 1,
      "brand_name_pos": "text",
      "fullname": "text",
      "logo": "path",
      "photo": "path",
      "product_photo": "path",
      "category": {
        "text": "text"
      }
    },
    "has_business": true,
    "type": "M",
    "participants": [
      1,
      2
    ]
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

#### `get_room_of_type`

**_Получить комнату определенного типа._**

**_Должен быть использован для получения комнат, которых может быть максимум по одной на пользователя._**

**_Типы таких комнат:_**
- **_`'S'` (Support): комната поддержки_**
- **_`'H'` (Help): комната индивидуальной помощи с коллаборациями_**

**_Для других типов вернет 400._**

**_Если тип верный, но по каким-то причинам комнат все равно больше, чем одна, то вернет 500._**
**_В этом случае админам придется чинить через админку. Но само по себе такое произойти не может._**

##### Параметры

- `action`: str - _название action_
- `type_`: str - _тип комнаты_ (`_` - не опечатка! Нужно, чтобы избежать конфликта со встроенной в язык функцией)
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "get_room_of_type",
  "type_": "S",
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": {
    "id": 1,
    "last_message": {
      "id": 1,
      "room": 1,
      "text": "test",
      "created_at": "2024-09-04T11:22:02.474470Z",
      "user": 1
    },
    "interlocutors_brand": null,
    "has_business": true,
    "type": "S",
    "participants": [
        1
    ]
  },
  "action": "get_room_of_type",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200** - если комната существовала, то вернется она
  - ```
    "errors": []
    ```
- **201** - если комнаты не существовало она будет создана
  - ```
    "errors": []
    ```
- **400** - если указали тип, который было сказано не указывать
  - ```
    "errors": ["There can be multiple rooms of type [{type_}]. Use 'list' action instead and filter result by type."]
    ```
- **500** - если ошибка на стороне сервера. Кто-то из админов доигрался с количеством комнат или при обращении к базе данных какая-то ошибка произошла.
  - ```
    "errors": ["Multiple rooms returned! Must be exactly one."]
    ```
  - ```
    "errors": ["Room creation failed! Please try again."]
    ```

### `ws://localhost:80/ws/admin-chat/`

**_Все те же actions, что и в обычном чате, но без `current_room_info`._**

**_`get_room_of_type` заменено на `get_support_room`, потому что админы могут писать в поддержку (коллективный разум, все дела), но комнаты помощи им недоступны_**

**_У некоторых actions изменено поведение (см. ниже)_**

**_Во всех ответах, где есть `interlocutors_brand` возвращает список брендов всех участников комнаты, если они есть. Структура такая же, только вместо одного объекта - список объектов. (P.S. мне лень было определять, где админ, как админ, а где как пользователь, поэтому пока будет так)_**

#### Необходимые разрешения

- Пользователь должен быть **администратором**

#### Права

- Просматривать сообщения можно в **любой** комнате
- `create_message`, `edit_message`, `delete_messages` доступны только в комнатах поддержки и помощи или метча, если это метч администратора (см. описание эндпоинта в начале документации)

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
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}] if you are not a participant of it!"]
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
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}] if you are not a participant of it!"]
    ```
- **404**
  - ```
    "errors": ["Message with id: {msg_id} and user: {current_user.email} not found! Check whether the user is the author of the message and the id is correct! Check if messages belong to the current user's room!"]
    ```

#### `delete_messages`

**_Только дл своих сообщений_**

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
- **403**
  - ```
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}] if you are not a participant of it!"]
    ```
- **404**
  - ```
    "errors": ["Messages with ids: {msg_id_list} were not found! Nothing was deleted! Check whether the user is the author of the message and the ids are correct! Check if messages belong to the current user's room!"]
    ```

#### `get_support_room`

**_Получить комнату поддержки._**

##### Параметры

Здесь, в отличие от `get_room_of_type`, не нужно передавать тип. Всегда вернется тип `'S'` (Support)

- `action`: str - _название action_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "get_support_room",
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": {
    "id": 1,
    "last_message": {
      "room": null,
      "text": "",
      "user": null
    },
    "interlocutors_brand": [],
    "has_business": false,
    "type": "S",
    "participants": [
        1
    ]
  },
  "action": "get_support_room",
  "response_status": 200,
  "request_id": 1500000
}
```

##### Возможные статусы

- **200** - если комната существовала, то вернется она
  - ```
    "errors": []
    ```
- **201** - если комнаты не существовало она будет создана
  - ```
    "errors": []
    ```
- **500** - если ошибка на стороне сервера. Кто-то из админов доигрался с количеством комнат или при обращении к базе данных какая-то ошибка произошла.
  - ```
    "errors": ["Multiple rooms returned! Must be exactly one."]
    ```
  - ```
    "errors": ["Room creation failed! Please try again."]
    ```
