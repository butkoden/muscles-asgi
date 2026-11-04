# Запуск ASGI-приложения

`muscles-asgi` предоставляет `AsgiStrategy`, базовый класс `MuscularAsgiApp`
и фабрику `asgi_app`. Фабрика подключает API приложения и возвращает ASGI
callable для сервера:

```python
from muscles.asgi import MuscularAsgiApp, asgi_app


class App(MuscularAsgiApp):
    pass


application = asgi_app(App())
```

Запускайте `application` ASGI-сервером, например Uvicorn. Объект приложения
остаётся корнем конфигурации и расширений; runtime не создаёт второе приложение.

## Настройка стратегии

Если нужна собственная конфигурация `Context`, задайте стратегию в приложении.
Например, логгер и режим отладки передаются через `options`:

```python
import logging

from muscles import Context
from muscles.asgi import AsgiStrategy

context = Context(
    AsgiStrategy,
    options={
        "logger": logging.getLogger("my.application"),
        "debug": False,
    },
)
```

`asgi_app(app, context="asgi")` использует контекст `app.asgi` по умолчанию;
можно передать имя другого атрибута или экземпляр `Context`.

## Обработка запросов

ASGI-сервер передаёт runtime `scope`, `receive` и `send`. Стратегия Muscles
создаёт запрос, сопоставляет маршрут, выполняет handler и отправляет ответ через
ASGI `send`. Обработчики и метаданные маршрутов объявляются средствами runtime;
бизнес-логика остаётся в вызываемых use case/actions приложения.

Для тестов пакет предоставляет `TestClient` и `TestResponse`:

```python
from muscles.asgi import TestClient

client = TestClient(application)
response = client.get("/")
```

Проверяйте конкретные методы клиента и регистрации маршрутов по API текущей
версии пакета; пример выше показывает только создание клиента и GET-запрос.
