# Routes и REST API

Muscles предоставляет два основных инструмента для построения HTTP-интерфейсов:

- `Routes` — обычная маршрутизация HTTP-запросов;
- `RestApi` — маршрутизация REST API с единым префиксом, документацией и API-инфраструктурой.

Оба интерфейса используют одинаковый принцип декларации маршрутов:

```python
@routes.init("/path")
async def handler(request):
    ...
```

или:

```python
@api.init("/path")
async def handler(request):
    ...
```

---

# 1. Routes

`Routes` используется для HTTP-маршрутов приложения:

```python
from muscles.asgi import application_routes as routes
```

Простейший маршрут:

```python
@routes.init("/")
async def home(request):
    return "Hello, World!"
```

Маршрут `/` является корнем приложения.

Другой маршрут:

```python
@routes.init("/about")
async def about(request):
    return "About"
```

Запрос:

```text
GET /about
```

будет передан функции `about`.

---

# 2. HTTP-методы

Метод запроса можно указать через `method`:

```python
@routes.init("/users", method="GET")
async def users(request):
    ...
```

Поддерживаются стандартные HTTP-методы:

```text
GET
POST
PUT
PATCH
DELETE
HEAD
OPTIONS
```

Например:

```python
@routes.init("/users", method="GET")
async def get_users(request):
    ...


@routes.init("/users", method="POST")
async def create_user(request):
    ...


@routes.init("/users/{id}", method="PUT")
async def update_user(request, id):
    ...


@routes.init("/users/{id}", method="DELETE")
async def delete_user(request, id):
    ...
```

Один путь может иметь несколько обработчиков — по одному на каждый HTTP-метод.

---

# 3. REST API

Для REST API используется `RestApi`.

Например:

```python
from muscles.asgi import application_api as api
```

API можно создать с общим префиксом:

```python
api = RestApi(
    prefix="/api/v1",
    version="1.0",
    name="ApiV1",
    title="System API",
)
```

После этого маршруты API объявляются относительно `/api/v1`.

```python
@api.init("/")
async def home(request):
    ...
```

соответствует:

```text
GET /api/v1
```

А:

```python
@api.init("/users")
async def users(request):
    ...
```

соответствует:

```text
GET /api/v1/users
```

---

# 4. RESTful API

RESTful API рекомендуется строить вокруг **ресурсов**, а не действий.

Например, ресурс пользователя:

```text
/users
/users/{id}
```

### Получить список

```python
@api.init("/users", method="GET")
async def get_users(request):
    ...
```

```text
GET /api/v1/users
```

### Получить пользователя

```python
@api.init("/users/{id}", method="GET")
async def get_user(request, id):
    ...
```

```text
GET /api/v1/users/123
```

### Создать пользователя

```python
@api.init("/users", method="POST")
async def create_user(request):
    ...
```

```text
POST /api/v1/users
```

### Изменить пользователя

```python
@api.init("/users/{id}", method="PATCH")
async def update_user(request, id):
    ...
```

```text
PATCH /api/v1/users/123
```

### Удалить пользователя

```python
@api.init("/users/{id}", method="DELETE")
async def delete_user(request, id):
    ...
```

```text
DELETE /api/v1/users/123
```

В результате один REST-ресурс получает стандартный набор операций:

```text
GET     /users
POST    /users
GET     /users/{id}
PATCH   /users/{id}
DELETE  /users/{id}
```

---

# 5. Параметры пути

Параметры объявляются непосредственно в URL:

```python
@api.init("/users/{id}", method="GET")
async def get_user(request, id):
    ...
```

Запрос:

```text
GET /api/v1/users/42
```

передаст:

```python
id == "42"
```

Параметров может быть несколько:

```python
@api.init(
    "/users/{user_id}/orders/{order_id}",
    method="GET",
)
async def get_order(request, user_id, order_id):
    ...
```

Запрос:

```text
GET /api/v1/users/42/orders/100
```

передаст:

```python
user_id == "42"
order_id == "100"
```

---

# 6. Группировка маршрутов

Для больших приложений маршруты можно объединять в группы.

Например:

```python
users = routes.group("/users")
```

После этого:

```python
@users.init("/")
async def users_index(request):
    ...


@users.init("/{id}")
async def user(request, id):
    ...
```

создают:

```text
/users
/users/{id}
```

Группы можно вкладывать:

```python
users = routes.group("/users")
orders = users.group("/orders")
```

Теперь:

```python
@orders.init("/")
async def orders_list(request):
    ...
```

соответствует:

```text
/users/orders
```

Группы особенно полезны для разделения больших API по доменам.

---

# 7. Организация REST API по ресурсам

Для большого API рекомендуется разделять ресурсы:

```text
api/
├── users.py
├── orders.py
├── products.py
└── payments.py
```

Например, `users.py`:

```python
from muscles.asgi import application_api as api


@api.init("/users", method="GET")
async def get_users(request):
    ...


@api.init("/users", method="POST")
async def create_user(request):
    ...


@api.init("/users/{id}", method="GET")
async def get_user(request, id):
    ...


@api.init("/users/{id}", method="PATCH")
async def update_user(request, id):
    ...


@api.init("/users/{id}", method="DELETE")
async def delete_user(request, id):
    ...
```

А `orders.py`:

```python
from muscles.asgi import application_api as api


@api.init("/orders", method="GET")
async def get_orders(request):
    ...


@api.init("/orders", method="POST")
async def create_order(request):
    ...


@api.init("/orders/{id}", method="GET")
async def get_order(request, id):
    ...
```

---

# 8. Actions

Не все операции являются CRUD.

Если операция является действием над ресурсом, можно использовать отдельный endpoint:

```text
POST /users/{id}/activate
POST /orders/{id}/cancel
POST /payments/{id}/refund
```

Например:

```python
@api.init("/users/{id}/activate", method="POST")
async def activate_user(request, id):
    ...
```

Такой подход предпочтительнее, чем пытаться представить любое действие как изменение ресурса.

---

# 9. Query parameters

Query-параметры не являются частью маршрута.

Например:

```text
GET /api/v1/users?page=2&limit=20
```

маршрут остаётся:

```python
@api.init("/users", method="GET")
async def users(request):
    ...
```

А параметры:

```text
?page=2&limit=20
```

обрабатываются непосредственно из `request`.

Таким образом, эти запросы используют один маршрут:

```text
/users
/users?page=2
/users?page=2&limit=20
```

---

# 10. Тело запроса

Для `POST`, `PUT` и `PATCH` данные обычно передаются в request body.

Например:

```text
POST /api/v1/users
Content-Type: application/json
```

```json
{
    "name": "Denis",
    "email": "denis@example.com"
}
```

Обработчик:

```python
@api.init("/users", method="POST")
async def create_user(request):
    data = request.json()
    ...
```

Конкретный способ получения body зависит от используемого transport/request implementation.

---

# 11. Ответ API

API-обработчик может возвращать данные через стандартный response-механизм Muscles.

Например:

```python
from muscles.asgi import BaseResponse


@api.init("/users", method="GET")
async def users(request):
    return BaseResponse(
        data={
            "items": [
                {"id": 1, "name": "Denis"},
            ]
        }
    )
```

Для JSON API рекомендуется возвращать структурированные данные, а не HTML.

---

# 12. REST API и обычные Routes

Разница между ними — прежде всего назначение.

### Routes

Используйте для:

```text
HTML
web pages
browser endpoints
webhooks
static application endpoints
обычных HTTP handlers
```

Например:

```python
@routes.init("/privacy")
async def privacy(request):
    return await application.template.render_async(
        "privacy.html"
    )
```

### RestApi

Используйте для:

```text
JSON API
мобильных клиентов
frontend applications
microservices
интеграций
RESTful ресурсов
```

Например:

```python
@api.init("/users/{id}", method="GET")
async def user(request, id):
    ...
```

---

# 13. Версионирование API

Для публичных API рекомендуется использовать версию в префиксе:

```python
api = RestApi(
    prefix="/api/v1",
    version="1.0",
)
```

Получаются endpoints:

```text
/api/v1/users
/api/v1/orders
/api/v1/products
```

При несовместимом изменении API можно создать новую версию:

```text
/api/v1/...
/api/v2/...
```

При этом существующие клиенты продолжают использовать старую версию.

---

# 14. Рекомендуемая структура

Для приложения с REST API:

```text
src/
├── app.py
│
├── main/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── home.py
│   │   └── privacy.py
│   │
│   └── api/
│       ├── __init__.py
│       ├── users.py
│       ├── orders.py
│       └── products.py
│
└── controllers/
    ├── users.py
    ├── orders.py
    └── products.py
```

Web-маршруты:

```python
from muscles.asgi import application_routes as routes
```

API:

```python
from muscles.asgi import application_api as api
```

---

# 15. Полный пример

```python
from muscles.asgi import application_api as api


# GET /api/v1
@api.init("/", method="GET")
async def api_root(request):
    return {
        "name": "My API",
        "version": "1.0",
    }


# GET /api/v1/users
@api.init("/users", method="GET")
async def get_users(request):
    ...


# POST /api/v1/users
@api.init("/users", method="POST")
async def create_user(request):
    ...


# GET /api/v1/users/{id}
@api.init("/users/{id}", method="GET")
async def get_user(request, id):
    ...


# PATCH /api/v1/users/{id}
@api.init("/users/{id}", method="PATCH")
async def update_user(request, id):
    ...


# DELETE /api/v1/users/{id}
@api.init("/users/{id}", method="DELETE")
async def delete_user(request, id):
    ...


# POST /api/v1/users/{id}/activate
@api.init("/users/{id}/activate", method="POST")
async def activate_user(request, id):
    ...
```

При:

```python
api = RestApi(prefix="/api/v1")
```

получаем:

```text
GET     /api/v1
GET     /api/v1/users
POST    /api/v1/users
GET     /api/v1/users/{id}
PATCH   /api/v1/users/{id}
DELETE  /api/v1/users/{id}
POST    /api/v1/users/{id}/activate
```

---

# Краткая схема

```text
Routes
│
├── "/"                    → корень приложения
├── "/about"               → обычный HTTP endpoint
├── "/users/{id}"          → параметризованный маршрут
└── group("/admin")        → группа маршрутов
     ├── "/"
     └── "/users"


RestApi(prefix="/api/v1")
│
├── "/"                    → GET /api/v1
├── "/users"               → коллекция пользователей
│    ├── GET               → список
│    └── POST              → создание
│
└── "/users/{id}"          → отдельный пользователь
     ├── GET               → получение
     ├── PATCH             → изменение
     └── DELETE            → удаление
```

## Главное правило

Маршрут описывает **ресурс и его путь**, а HTTP-метод определяет **операцию над этим ресурсом**:

```text
GET    /users       → получить пользователей
POST   /users       → создать пользователя
GET    /users/{id}  → получить пользователя
PATCH  /users/{id}  → изменить пользователя
DELETE /users/{id}  → удалить пользователя
```

Для корня всегда используется `/`, а не пустая строка:

```python
@api.init("/")
```