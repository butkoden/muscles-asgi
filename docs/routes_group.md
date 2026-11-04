# Routes, Groups и Packages

Muscles позволяет организовывать маршрутизацию приложения через **Packages** и **Groups**.

Эта модель позволяет отделить:

- приложение;
- функциональные пакеты;
- маршруты пакета;
- API пакета;
- вложенные группы маршрутов.

Package отвечает за собственный контекст и ресурсы, а `Routes` и `RestApi` отвечают за регистрацию HTTP-маршрутов.

---

# 1. Package

Package — самостоятельный функциональный модуль приложения.

Простейший пакет:

```python
from muscles.core import MusclesPackage


class CorePackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )
```

Например, пакет подключён с конфигурацией:

```yaml
packages:
  - class: packages.core.main.CorePackage
    config:
      rootPath: /core
```

Тогда пакет получает собственную группу:

```text
Application
└── Routes
    └── /core
```

---

# 2. Root Path Package

`rootPath` определяет публичный URL-префикс пакета.

Например:

```yaml
packages:
  - class: packages.users.main.UsersPackage
    config:
      rootPath: /users
```

Package:

```python
class UsersPackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )
```

Теперь маршруты пакета объявляются относительно `/users`.

```python
@routes.init("/")
async def home(request):
    ...
```

соответствует:

```text
/users
```

А:

```python
@routes.init("/profile")
async def profile(request):
    ...
```

соответствует:

```text
/users/profile
```

Таким образом, Package не должен вручную добавлять `rootPath` к каждому маршруту.

---

# 3. Использование Package Routes

После создания группы пакет может экспортировать свои маршруты:

```python
class CorePackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )
```

В модуле пакета:

```python
from muscles.asgi import package_routes as routes


@routes.init("/")
async def home(request):
    return "Core"
```

`package_routes` автоматически обращается к `routes` текущего Package.

Поэтому один и тот же модуль маршрутов может работать внутри разных экземпляров Package.

---

# 4. Package Context

Во время загрузки Package Muscles устанавливает текущий Package в контекст.

Условно:

```text
Package loading
      │
      ▼
set_package(package)
      │
      ├── import routes
      ├── import api
      └── import controllers
      │
      ▼
reset_package()
```

Поэтому:

```python
from muscles.asgi import package_routes as routes
```

не содержит конкретный Package.

Это proxy, который во время выполнения получает текущий Package:

```text
package_routes
      │
      ▼
current package
      │
      ▼
package.routes
```

---

# 5. Application Routes

Кроме Package Routes существуют Application Routes.

```python
from muscles.asgi import application_routes as routes
```

Они обращаются непосредственно к текущему Application:

```text
application_routes
        │
        ▼
current application
        │
        ▼
application.routes
```

Это удобно для маршрутов, принадлежащих всему приложению, а не отдельному Package.

Например:

```python
from muscles.asgi import application_routes as routes


@routes.init("/privacy")
async def privacy(request):
    ...
```

---

# 6. Package Routes vs Application Routes

Используйте `application_routes`, если маршрут относится ко всему приложению:

```text
/privacy
/health
/
/robots.txt
```

Используйте `package_routes`, если маршрут является частью функционального Package:

```text
/core
/core/settings
/core/users

/shop
/shop/products
/shop/orders
```

Схематично:

```text
Application
│
├── application_routes
│   ├── /
│   ├── /privacy
│   └── /health
│
├── CorePackage
│   └── package_routes
│       ├── /core
│       └── /core/settings
│
└── ShopPackage
    └── package_routes
        ├── /shop
        └── /shop/orders
```

---

# 7. Groups

`group()` позволяет создать вложенный URL-контекст.

```python
routes = app.routes.group("/admin")
```

Теперь:

```python
@routes.init("/")
async def home(request):
    ...
```

создаёт:

```text
/admin
```

А:

```python
@routes.init("/users")
async def users(request):
    ...
```

создаёт:

```text
/admin/users
```

---

# 8. Вложенные Groups

Groups можно вкладывать друг в друга.

```python
admin = app.routes.group("/admin")
users = admin.group("/users")
```

Теперь:

```python
@users.init("/")
async def users_home(request):
    ...
```

соответствует:

```text
/admin/users
```

А:

```python
@users.init("/{id}")
async def user(request, id):
    ...
```

соответствует:

```text
/admin/users/{id}
```

Структура:

```text
Routes
└── /admin
    └── /users
        ├── /
        └── /{id}
```

---

# 9. Metadata Groups

Group может передавать metadata своим маршрутам.

Например:

```python
api = routes.group(
    "/api",
    version="1.0",
)
```

Маршруты внутри группы получают соответствующий metadata-контекст.

Вложенная группа может добавлять или переопределять metadata:

```python
admin = api.group(
    "/admin",
    auth="admin",
)
```

В результате маршрут получает контекст обеих групп:

```text
/api
    version = 1.0

/api/admin
    version = 1.0
    auth = admin
```

Metadata объединяется при создании вложенных групп.

---

# 10. Package + Group

Package и Group решают разные задачи.

**Package** отвечает за функциональный модуль:

```text
Users
Orders
Payments
Core
Admin
```

**Group** отвечает за URL-пространство:

```text
/users
/orders
/payments
/admin
```

Обычно они используются вместе:

```python
class UsersPackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )
```

Конфигурация:

```yaml
packages:
  - class: packages.users.main.UsersPackage
    config:
      rootPath: /users
```

Маршруты:

```python
from muscles.asgi import package_routes as routes


@routes.init("/")
async def index(request):
    ...


@routes.init("/{id}")
async def user(request, id):
    ...
```

Получаем:

```text
/users
/users/{id}
```

---

# 11. Package API

Та же модель используется для API.

Package может получить отдельную API-группу:

```python
class UsersPackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )

        self.api = app.api.group(
            config.apiPath
        )
```

Конфигурация:

```yaml
packages:
  - class: packages.users.main.UsersPackage
    config:
      rootPath: /users
      apiPath: /api/v1/users
```

Теперь Package имеет два пространства:

```text
Web:
    /users

API:
    /api/v1/users
```

---

# 12. Package API Routes

Внутри Package:

```python
from muscles.asgi import package_api as api


@api.init("/", method="GET")
async def users(request):
    ...
```

Если Package API имеет:

```text
/api/v1/users
```

то endpoint будет:

```text
GET /api/v1/users
```

Другой endpoint:

```python
@api.init("/{id}", method="GET")
async def user(request, id):
    ...
```

получит:

```text
GET /api/v1/users/{id}
```

---

# 13. Полная структура Package

Типичный Package может выглядеть так:

```text
packages/
└── users/
    ├── __init__.py
    ├── main.py
    │
    ├── routes/
    │   ├── __init__.py
    │   ├── home.py
    │   └── profile.py
    │
    ├── api/
    │   ├── __init__.py
    │   ├── users.py
    │   └── profile.py
    │
    └── controllers/
        ├── __init__.py
        └── users.py
```

Package:

```python
class UsersPackage(MusclesPackage):

    modules = (
        "packages.users.routes",
        "packages.users.api",
    )

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )

        self.api = app.api.group(
            config.apiPath
        )
```

---

# 14. Package Module Loading

Package определяет, какие модули принадлежат ему:

```python
class UsersPackage(MusclesPackage):

    modules = (
        "packages.users.routes",
        "packages.users.api",
    )
```

Muscles загружает эти модули в контексте Package.

Модули могут использовать:

```python
from muscles.asgi import package_routes as routes
```

или:

```python
from muscles.asgi import package_api as api
```

При этом им не требуется импортировать сам `UsersPackage`.

Это позволяет избежать жёсткой связи между модулями и конкретным экземпляром Package.

---

# 15. Один Package — несколько ресурсов

Package не ограничен только `routes` и `api`.

Например:

```python
class AdminPackage(MusclesPackage):

    def __init__(self, app, config):
        self.routes = app.routes.group(
            config.rootPath
        )

        self.api = app.api.group(
            config.apiPath
        )

        self.admin = app.admin.group(
            config.adminPath
        )
```

Package может владеть любыми ресурсами приложения:

```text
Package
│
├── routes
├── api
├── admin
├── controllers
├── database
├── queue
└── ...
```

Muscles не требует фиксированной структуры Package.

---

# 16. Независимость Package от URL-структуры

Package не должен самостоятельно собирать URL:

```python
# Не рекомендуется
@routes.init("/users/profile")
```

если `/users` уже является `rootPath` Package.

Лучше:

```python
@routes.init("/profile")
```

а Package получает:

```text
rootPath = /users
```

В результате:

```text
Package root:
    /users

Route:
    /profile

Final:
    /users/profile
```

Это позволяет изменить URL Package через конфигурацию, не изменяя его маршруты.

---

# 17. Рекомендуемая архитектура

Для большого приложения рекомендуется строить URL-пространство следующим образом:

```text
Application
│
├── Global Routes
│   ├── /
│   ├── /privacy
│   └── /health
│
├── CorePackage
│   ├── Routes
│   │   ├── /core
│   │   └── /core/settings
│   │
│   └── API
│       ├── /api/v1/core
│       └── /api/v1/core/settings
│
├── UsersPackage
│   ├── Routes
│   │   ├── /users
│   │   └── /users/profile
│   │
│   └── API
│       ├── /api/v1/users
│       └── /api/v1/users/{id}
│
└── OrdersPackage
    ├── Routes
    │   └── /orders
    │
    └── API
        ├── /api/v1/orders
        └── /api/v1/orders/{id}
```

---

# 18. Краткая модель

В Muscles URL формируется из нескольких уровней:

```text
Application
    +
Package root
    +
Group
    +
Route
    =
Final URL
```

Например:

```text
Application API
    /api/v1

Package
    /users

Group
    /orders

Route
    /{id}

Final URL
    /api/v1/users/orders/{id}
```

Каждый уровень отвечает только за свою часть URL.

---

# 19. Основные правила

### Application Routes

```python
from muscles.asgi import application_routes as routes
```

Используются для глобальных маршрутов приложения.

### Package Routes

```python
from muscles.asgi import package_routes as routes
```

Используются внутри Package.

### Application API

```python
from muscles.asgi import application_api as api
```

Используется для глобального REST API.

### Package API

```python
from muscles.asgi import package_api as api
```

Используется для API конкретного Package.

### Groups

```python
group = routes.group("/prefix")
```

Создают вложенное URL-пространство.

### Root route

Корневой маршрут всегда обозначается:

```python
@routes.init("/")
```

Пустая строка `""` не используется как замена корню.

---

# Архитектурный принцип

Package владеет **функциональностью**.

Group владеет **URL-контекстом**.

Route описывает **конкретный endpoint**.

Application предоставляет **общие ресурсы**.

В результате:

```text
Application
     │
     ├── предоставляет Routes / API
     │
     ▼
Package
     │
     ├── выбирает свои Groups
     │
     ▼
Group
     │
     ├── добавляет URL-контекст
     │
     ▼
Route
     │
     └── определяет конкретный endpoint
```

Muscles при этом не навязывает Package фиксированную внутреннюю структуру. Package может использовать любые ресурсы и модули, необходимые конкретному приложению.