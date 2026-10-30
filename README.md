# AQA API Starter

Учебный минимум API-автотестов для [Automation Exercise](https://automationexercise.com/api_list).

Тесты ходят на живой сайт — нужен интернет. Браузер не нужен.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
```

Результаты Allure пишутся в `allure-results/`. HTML-отчёт:

```bash
allure serve allure-results
```

Если команды `allure` нет: macOS — `brew install allure`, Windows — `scoop install allure`.

Только API или только UI:

```bash
pytest -m api -v
pytest -m ui -v
```

---

## GitHub Actions

Пайплайн [`.github/workflows/tests.yml`](.github/workflows/tests.yml) запускается на push в `main`, на pull request и вручную.

| Стадия | Job | Что делает |
|--------|-----|------------|
| 1 | Build + requirements | Ставит Python 3.11 и зависимости из `requirements.txt` |
| 2 | API layer | `pytest -m api` — текущие тесты брендов и товаров |
| 3 | UI layer | `pytest -m ui` — после успешного API; пока заглушка в `tests/ui/` |

Стадии идут строго по порядку: если сломались зависимости, API не стартует; если красный API, UI не запускается. Allure-результаты каждой тестовой стадии сохраняются как artifact.

После тестов job **Allure report** собирает HTML, job **GitHub Pages** пушит его в ветку `gh-pages`.

**https://rbbobby.github.io/aqa-api-starter/**

Пайплайн сам сайт не включает — у `GITHUB_TOKEN` нет такого права. Один раз в репозитории:

1. Дождитесь зелёного прогона: в репозитории появится ветка `gh-pages`.
2. **Settings → Pages → Build and deployment**.
3. **Source:** Deploy from a branch.
4. **Branch:** `gh-pages` / `/ (root)` → Save.

Pull request на сайт не выкладывается — HTML лежит в artifact `allure-report`.

Опционально переопределить URL и таймаут:

```bash
export API_BASE_URL=https://automationexercise.com/api
export API_TIMEOUT=30
```

---

## Как устроен проект

```text
aqa-api-starter/
├── api/
│   └── client.py          # HTTP-клиент: Session, get/post
├── tests/
│   ├── conftest.py        # фикстура api_client
│   └── test_products.py   # сами тесты
├── pytest.ini             # где искать тесты, allure-results
└── requirements.txt       # pytest + requests + allure-pytest
```

Цепочка вызова:

```text
тест  →  api_client.get("/productsList")  →  requests.Session  →  automationexercise.com/api
         ↑ фикстура из conftest.py
```

Роли файлов:

| Файл | Зачем |
|------|--------|
| `api/client.py` | Единственное место, где собирается URL и уходит HTTP-запрос |
| `tests/conftest.py` | Создаёт клиент один раз на прогон и отдаёт его тестам |
| `tests/test_products.py` | Сценарии: что вызвать и что проверить |
| `pytest.ini` | `testpaths = tests` и `pythonpath = .`, чтобы работал `from api.client import ApiClient` |

Тест **не** знает полный URL и **не** вызывает `requests.get` сам. Он получает готовый клиент аргументом функции.

---

## Паттерны автотестов

### 1. AAA — Arrange, Act, Assert

Каждый тест читается в три шага:

1. **Arrange** — подготовка. Здесь её делает фикстура: клиент уже создан, сессия открыта.
2. **Act** — одно действие: запрос к API.
3. **Assert** — проверки ответа.

```python
def test_get_products(api_client):          # Arrange: pytest передал клиент
    response = api_client.get("/productsList")  # Act
    body = response.json()

    assert response.status_code == 200          # Assert
    assert body["responseCode"] == 200
    assert body["products"]
```

В тесте не должно быть настройки URL, логина «на всякий случай» и второго запроса «заодно». Один тест — одно поведение.

### 2. API Client

Клиент — тонкая обёртка над `requests`. Зачем он, если можно писать `requests.get` прямо в тесте:

- один `base_url` и таймаут на весь проект;
- тесты пишут путь (`/productsList`), а не полный URL;
- cookies и keep-alive живут в одной HTTP-сессии;
- если завтра сменится хост или появится заголовок — правка в одном месте.

```python
class ApiClient:
    def __init__(self, ...):
        self.session = requests.Session()

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", ...)
```

`requests.get(...)` каждый раз открывает новое соединение. `requests.Session()` переиспользует TCP-соединение и хранит cookies между вызовами.

### 3. Фикстура как dependency injection

Тест объявляет зависимость именем аргумента. pytest сам находит фикстуру с таким же именем и подставляет значение.

```python
def test_get_products(api_client):   # «мне нужен api_client»
    ...
```

Тест не делает `ApiClient()` внутри себя. Это важно:

- не дублировать setup в каждом тесте;
- легко подменить клиент (другой URL, мок) без правки сценариев;
- закрыть соединение один раз после всех тестов, а не забывать `close()` в каждом файле.

### 4. HTTP-статус и бизнес-статус

Особенность Automation Exercise: при ошибке сервер часто отвечает **HTTP 200**, а настоящий результат лежит в JSON-поле `responseCode`.

Поэтому проверяют оба уровня:

| Что | Пример | Смысл |
|-----|--------|--------|
| `response.status_code` | `200` | Транспорт: запрос дошёл, HTTP ок |
| `body["responseCode"]` | `200` или `405` | Бизнес: операция разрешена или метод не поддерживается |
| `body["message"]` | `"This request method is not supported."` | Текст ошибки API |

Именно это показывает `test_post_products_not_supported`: POST на `/productsList` даёт HTTP 200 и `responseCode == 405`.

---

## Что такое фикстура `api_client`

Фикстура — функция, которую pytest вызывает **за** тест и передаёт результат в аргумент теста.

Она лежит в `tests/conftest.py`. pytest подхватывает этот файл автоматически: импортировать его в тестах не нужно.

```python
@pytest.fixture(scope="session")
def api_client():
    client = ApiClient()   # setup: создать клиент
    yield client           # отдать тестам
    client.close()         # teardown: закрыть соединения
```

Как это читается:

1. **Имя** `api_client` — такое же, как аргумент в `def test_get_products(api_client)`.
2. **`scope="session"`** — один экземпляр на весь прогон pytest, а не новый на каждый тест.
3. **`yield`** — всё до `yield` выполняется до тестов, всё после — когда прогон закончился.

Жизненный цикл при `pytest -v`:

```text
pytest стартует
    → создаётся ApiClient()          # один раз
    → внутри него requests.Session()
    → test_get_products(api_client)
    → test_post_products_not_supported(api_client)   # тот же клиент
    → client.close()                 # после всех тестов
pytest завершается
```

Без `scope="session"` (по умолчанию `function`) клиент создавался бы и закрывался **на каждый тест**. Для API это лишние соединения. Session-scope имеет смысл, пока тесты не портят общее состояние (не логинятся под разными пользователями в одной сессии без очистки).

Другие scope, которые встретятся дальше: `function` (каждый тест), `class` (класс тестов), `module` (файл), `session` (весь прогон).

---

## Как создаётся сессия

Здесь две разные «сессии» — их часто путают.

### Pytest session

Это **прогон тестов**: от команды `pytest` до финального отчёта. `scope="session"` привязан именно к нему. Фикстура живёт, пока жив этот прогон.

### HTTP session (`requests.Session`)

Это **постоянное HTTP-соединение** к серверу. Создаётся внутри клиента:

```python
class ApiClient:
    def __init__(self, ...):
        self.session = requests.Session()
```

Дальше `get` / `post` идут через `self.session`, а не через голый `requests.get`.

Что даёт HTTP-сессия:

- keep-alive — меньше рукопожатий TCP/TLS между тестами;
- общие cookies — если позже появится логин, второй запрос увидит ту же авторизацию;
- общие заголовки — их можно выставить один раз на `session.headers`.

Закрытие:

```python
def close(self) -> None:
    self.session.close()
```

`close()` вызывается в teardown фикстуры, после `yield`. Соединения не висят после окончания pytest.

Связка целиком:

```text
pytest session (прогон)
    └── фикстура api_client (scope="session")
            └── ApiClient
                    └── requests.Session()   # HTTP session
                            ├── GET /productsList
                            └── POST /productsList
                    └── close()
```

Один прогон pytest → один `ApiClient` → одна HTTP-сессия → все запросы тестов.

---

## Что смотреть дальше

Когда этот минимум станет привычным:

- добавить `PUT` / `DELETE` в клиент и тесты на `/brandsList`;
- вынести эндпоинты в сервис (`ProductsService.get_products()`), если путей станет много;
- параметризовать поиск (`@pytest.mark.parametrize`);
- типизировать JSON-ответ dataclass / pydantic, если проверки полей разрастутся.
