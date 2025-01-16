# Документация chat

## Эндпоинты

### `ws/chat/`

- обычный чат, где общаются бренды после метча
- для подключения у пользователя должен быть бренд
- присоединиться могут только к комнатам, где состоит сам бренд (после метча)
- писать/редактировать/удалять сообщения можно только присоединившись к комнате
- редактировать/удалять могут только свои сообщения и только в той комнате, к которой сейчас подключены

#### Доступные протоколы

- `chat`

### `ws/admin-chat/`

- чат для админов (для подключения нужно иметь права администратора)
- присоединиться могут к любой комнате, чтобы просматривать сообщения
- писать/редактировать/удалять сообщения могут только в комнатах поддержки и помощи. В комнатах метчей могут только если это их метч (соответственно если у админа есть бренд, вероятно это только для самого W2W бренда)
- писать/редактировать/удалять сообщения можно только присоединившись к комнате
- редактировать/удалять могут только свои сообщения

#### Доступные протоколы

- `admin-chat`

## Протоколы

- Для подключения к сокету нужно указать один из доступных протоколов
- За протоколы отвечает хэдер `sec-websocket-protocol`

## Авторизация

- Для авторизации нужен `access` токен
- Токен указывается один раз при подключении
- Токен указывается как протокол. Должен быть **последним** в списке протоколов
- Префикс `Bearer` не нужен

## Actions

### `ws/chat/`

#### Необходимые разрешения

- Пользователь должен быть **авторизованным**
- У пользователя должен быть бренд

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
        "name": "text",
        "logo": "path",
        "photo": "path",
        "category": {
          "id": 1,
          "name": "text"
        }
      },
      "type": "M"
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
      "name": "text",
      "logo": "path",
      "photo": "path",
      "category": {
        "id": 1,
        "name": "text"
      }
    },
    "type": "M"
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
- **400**
  - ```
    "data": null,
    "errors": ["You have already joined a room!"]
    ```
- **403**
  - ```
    "data": null,
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
    "response": "Leaved room 1 successfully!"
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
    "data": null,
    "errors": ["Action 'leave_room' not allowed. You are not in the room"]
    ```

#### `get_room_messages`

_**Получить все сообщения комнаты**_

`room_pk` не передается, отправляет сообщения текущей комнаты

Пагинация по 100 сообщений на странице. Номер первой страницы - 1.  

В ответе:
- `count` - кол-во всех сообщений в комнате
- `next` - номер следующей страницы. `null`, если эта страница последняя.

##### Параметры

- `action`: str - _название action_
- `page`: int - _номер страницы_
- `request_id`: int - _уникальный id запроса (можно указать текущую дату-время в миллисекундах)_

##### Пример запроса

```json
{
  "action": "get_room_messages",
  "page": 1,
  "request_id": 1500000
}
```

##### Пример ответа

```json
{
  "errors": [],
  "data": {
    "count": 1,
    "messages": [
      {
        "id": 1,
        "user": 1,
        "room": 1,
        "text": "Test message",
        "created_at": "2024-06-20T13:27:06.746701Z"
      }
    ],
    "next": 2
  },
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
    "data": null,
    "errors": ["Action not allowed. You are not in the room!"]
    ```
  - Если в качестве номера страницы передано не целое число
    ```
    "data": null,
    "errors": ["Page number must be an integer!"]
    ```
  - Если страницы с таким номером не существует
    ```
    "data": null,
    "errors": ["Page {page} does not exist!"]
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
    "text": "hello",
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
    "data": null,
    "errors": ["Action not allowed. You are not in the room!"]
    ```
  - Если попытаться отправить больше одного сопроводительного сообщения (тип чата `INSTANT`)
    ```
    "data": null,
    "errors": ["Action not allowed. You have already sent message to this user."]
    ```
  - Если попытаться отправить сообщение в чат типа `INSTANT`, не являясь инициатором кооперации
    ```
    "data": null,
    "errors": ["You cannot send a message to this room. Like this brand in response to be able to send a message."]
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
    "data": null,
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **404**
  - ```
    "data": null,
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
- **400**
  - ```
    "data": null,
    "errors": ["Action not allowed. You are not in the room!"]
    ```
- **404**  
  Этот статус будет вне зависимости от того все id были не найдены или только некоторые
  - ```
    "data": null,
    "errors": ["Messages with ids [msg_id_list] do not exist! Nothing was deleted!"]
    ```

#### `get_support_room`

**_Получить комнату поддержки._**

##### Параметры

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
    "type": "S"
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
- **201** - если комнаты не существовало, она будет создана
  - ```
    "errors": []
    ```
- **500** - если ошибка на стороне сервера
  - ```
    "data": null,
    "errors": ["Room creation failed! Please try again."]
    ```

### `ws/admin-chat/`

**_Все те же actions, что и в обычном чате._**

**_У некоторых actions изменено поведение (см. ниже)_**

**_В actions, в ответах которых есть `interlocutors_brand` возвращаются все пользователи состоящие в комнате._**

#### Необходимые разрешения

- Пользователь должен быть **администратором**

#### Права

- Просматривать сообщения можно в **любой** комнате
- `create_message`, `edit_message`, `delete_messages` доступны только в комнатах поддержки

#### `list`

**_Возвращает список **всех** комнат_**

#### `join_room`

##### Возможные статусы

- **200**
  - ```
    "errors": []
    ```
- **400**
  - ```
    "data": null,
    "errors": ["You have already joined a room!"]
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
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}]."]
    ```

#### `edit_message`

**_Только для своих сообщений_**

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
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}]."]
    ```
- **404**
  - ```
    "errors": ["Message with id: {msg_id} and user: {current_user.email} not found! Check whether the user is the author of the message and the id is correct! Check if messages belong to the current user's room!"]
    ```

#### `delete_messages`

**_Только для своих сообщений_**

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
    "errors": ["Action not allowed. You cannot write to room of type [{current_room.type}]."]
    ```
- **404**
  - ```
    "errors": ["Messages with ids {not_existing} do not exist! Nothing was deleted."]
    ```
