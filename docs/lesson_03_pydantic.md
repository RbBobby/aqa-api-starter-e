# Урок 3. От словаря к модели: проверяем контракт API с Pydantic

В этом уроке добавим проверку структуры и типов ответа API с помощью **Pydantic 2**. На примере каталога брендов пройдём путь от JSON-словаря до типизированной модели и научимся находить ошибки в данных. Команды выполняем из корня репозитория в активированном виртуальном окружении.

**Результат:** `BrandsService` возвращает `list[Brand]`, поля и типы ответа проверяются в одном месте, а тест проверяет содержимое каталога. Ученик умеет объяснить `model_validate`, `Field(alias=...)`, строгий режим и прочитать `ValidationError`.

## 1. Подготовка к работе

Для примеров нужен проект с `ApiClient`, сервисом `BrandsService` и фикстурой `brands_service`. Сервис выполняет запрос `GET /brandsList` и возвращает список брендов.

В примерах используем пути `api/services/` и `tests/api_tests/`. Если в проекте папка сервисов называется `api/sevices/`, сначала переименуйте её в `api/services/` и обновите импорты. Если тесты лежат непосредственно в `tests/`, вносите изменения в существующие файлы без создания дублей.

В `requirements.txt` добавьте отдельную строку, сохранив остальные зависимости:

```text
pydantic==2.12.5
```

Это конкретная версия для воспроизводимого примера, а не требование использовать самую новую.

```bash
python -m pip install -r requirements.txt
python -c "import pydantic; print(pydantic.__version__)"
```

Ожидается `2.12.5`. В уроке применяется API **Pydantic 2**; примеры с `parse_obj` из старых материалов сюда не переносим.

## 2. Почему аннотация — ещё не проверка

Сейчас сервис отдаёт словари, и каждый тест заново описывает их структуру:

```python
for brand in brands:
    assert "id" in brand
    assert type(brand["id"]) is int
    assert "brand" in brand
    assert isinstance(brand["brand"], str)
```

Аннотация `-> list[dict]` сама эти проверки не выполняет. Она помогает человеку, редактору и анализатору типов. Чтобы проверить реальные данные во время прогона, нужен выполняемый код — в нашем случае Pydantic.

Есть три разных действия:

| Код | Что происходит |
|---|---|
| `response.json()` | JSON-текст разбирается в Python-значения; ожидаемая схема брендов ещё не проверена |
| `BrandsListResponse.model_validate(body)` | Проверяется форма данных и создаётся объект модели |
| `assert brands` | Проверяется продуктовое ожидание: каталог не пуст |

Валидный JSON может содержать `{"hello": 123}`. Это корректный JSON, но неправильный ответ ручки брендов.

## 3. Создаём модели ответа

Создайте папку `api/models` и пустой файл `api/models/__init__.py`.

**Файл `api/models/brands.py`:**

```python
from pydantic import BaseModel, ConfigDict, Field


class Brand(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    id: int
    brand: str


class BrandsListResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    response_code: int = Field(alias="responseCode")
    brands: list[Brand]
```

Разберём каждое непривычное место.

- **`BaseModel`** даёт классу механизм проверки данных. `model_validate` наследуется от него: писать этот метод самим не нужно.
- **`id: int`** — обязательное поле с ожидаемым типом. Значения по умолчанию нет, поэтому отсутствие `id` вызовет ошибку.
- **`list[Brand]`** — список объектов `Brand`. Проверяется каждый элемент, а не только первый.
- **`Field(alias="responseCode")`** связывает входной ключ JSON `responseCode` с Python-атрибутом `response_code`.
- **`strict=True`** запрещает незаметно принимать строковый `"1"` как целочисленный `id`. Настройка задана в обеих моделях явно, включая вложенную.
- **`extra="ignore"`** позволяет серверу добавить неизвестное нам поле. Оно не попадёт в модель; обязательные поля при этом всё равно проверяются.

`strict` отвечает за типы, `extra` — за неизвестные поля. Это разные настройки. Если договорённость требует отклонять любые дополнительные ключи, выбирают `extra="forbid"`; для этого занятия новые поля допускаем.

Обычное `id: int` без строгого режима может принять `"1"` и преобразовать его в `1`. Для проверки изменения типа этого недостаточно. Именно поэтому здесь включён `strict=True`.

Попробуйте в Python-консоли, запущенной из корня проекта:

```python
from api.models.brands import BrandsListResponse

payload = {
    "responseCode": 200,
    "brands": [{"id": 1, "brand": "Polo"}],
}
parsed = BrandsListResponse.model_validate(payload)

print(parsed.response_code)       # 200
print(parsed.brands[0].brand)     # Polo
print(type(parsed.brands[0]).__name__)  # Brand
```

**Здесь нет HTTP-запроса.** Мы проверяем локальный словарь. `model_validate` не обращается к серверу и не читает Swagger автоматически.

После перехода на модель меняется доступ к данным:

| Раньше | Теперь |
|---|---|
| `body["responseCode"]` | `parsed.response_code` |
| `brands[0]["id"]` | `brands[0].id` |
| `brands[0]["brand"]` | `brands[0].brand` |

`parsed.model_dump()` вернёт словарь с Python-именами. Если нужны исходные ключи API, используйте `parsed.model_dump(by_alias=True)`. Это полезно при сериализации, но для проверки ответа сейчас не требуется.

## 4. Подключаем модель в сервис

В `api/services/brands_service.py` добавьте импорт моделей и замените **только `get_brands`**. Существующий `upd_brands` и его импорты сохраните.

Ниже минимальная реализация класса для успешного GET:

```python
import allure

from api.client import ApiClient
from api.models.brands import Brand, BrandsListResponse

ENDPOINT = "/brandsList"


class BrandsService:
    def __init__(self, api_client: ApiClient) -> None:
        self.api_client = api_client

    def get_brands(self) -> list[Brand]:
        with allure.step("Запросить список брендов"):
            response = self.api_client.get(ENDPOINT)

        with allure.step("Проверить HTTP-статус"):
            assert response.status_code == 200, (
                f"Ожидали HTTP 200, получили {response.status_code}"
            )

        with allure.step("Проверить схему ответа брендов"):
            parsed = BrandsListResponse.model_validate(response.json())

        with allure.step("Проверить код операции"):
            assert parsed.response_code == 200, (
                f"Ожидали responseCode 200, получили {parsed.response_code}"
            )

        return parsed.brands
```

Почему такой порядок:

1. Сначала проверяем HTTP-статус: при 500 с HTML-страницей важнее увидеть HTTP-ошибку, чем ошибку разбора JSON.
2. Затем разбираем JSON и валидируем структуру.
3. Потом проверяем значение кода операции.
4. Возвращаем тесту список моделей.

`response_code: int` проверяет тип поля, но не требует значения `200`. Поэтому проверка успешного кода остаётся отдельной.

`response.reason == "OK"` здесь не используем: текстовая фраза статуса не нужна для проверки числового HTTP-кода и зависит от протокола/реализации.

Фикстура сервиса остаётся прежней. Если её ещё нет, добавьте этот код в `tests/api_tests/conftest.py` рядом с существующими фикстурами:

```python
import pytest

from api.client import ApiClient
from api.services.brands_service import BrandsService


@pytest.fixture
def brands_service(api_client: ApiClient) -> BrandsService:
    return BrandsService(api_client)
```

Не копируйте второй раз `api_client` или `AllureApiClient`: уже существующая фикстура продолжает создавать HTTP-клиент и закрывать его после прогона. Она должна находиться в этом же `conftest.py` или родительском `tests/conftest.py`.

## 5. Оставляем в тесте смысл сценария

Замените успешный тест брендов следующим. Остальные тесты файла, в том числе PUT, сохраняйте. Если используете тестовый класс, добавьте `self` первым аргументом метода.

**Файл `tests/api_tests/test_brands.py`:**

```python
import allure
import pytest

from api.services.brands_service import BrandsService


@allure.epic("API")
@allure.feature("Brands")
@allure.title("Каталог брендов непустой, данные корректны")
@pytest.mark.api
def test_get_brands(brands_service: BrandsService):
    brands = brands_service.get_brands()

    with allure.step("Проверить содержимое каталога"):
        assert brands, "Каталог брендов пуст"

        brand_ids = []
        for brand in brands:
            assert brand.id > 0, f"Некорректный id: {brand.id}"
            assert brand.brand.strip(), f"Пустое имя у бренда id={brand.id}"
            brand_ids.append(brand.id)

        assert len(brand_ids) == len(set(brand_ids)), "Повторяются id брендов"
```

Что исчезло: проверки наличия ключей, `dict`, `int`, `str`. Эту работу выполнила модель.

Что осталось: список не пуст, идентификаторы положительные и уникальные, названия не состоят из пробелов. Строка `"   "` соответствует типу `str`, поэтому одна модель её не отклонит.

В учебном сценарии проверяем непустой список. Если минимальное или точное количество брендов задано требованиями продукта, добавьте отдельную проверку этого количества.

Граница «модель / бизнес-проверка» — договорённость проекта. Например, `id > 0` можно выразить ограничением Pydantic, если это часть утверждённой схемы. Здесь оставляем его в тесте как отдельное ожидание к содержимому каталога.

```bash
python -m pytest tests/api_tests/test_brands.py -k test_get_brands -v
```

У выбранного GET-теста ожидается успешный результат при доступном и корректно работающем стенде. Остальные тесты продолжают проверять свои сценарии.

## 6. Ломаем данные и читаем ошибку

Чтобы увидеть нарушение схемы, не нужно менять чужой сервер. Создадим локальную учебную проверку нашей модели. Она **не доказывает корректность API**, а показывает, что мы правильно настроили валидатор.

Добавьте маркер в существующий раздел `markers` файла `pytest.ini`:

```ini
    contract: локальные проверки моделей без HTTP
```

**Файл `tests/api_tests/test_brand_contract.py`:**

```python
import pytest
from pydantic import ValidationError

from api.models.brands import BrandsListResponse


@pytest.mark.api
@pytest.mark.contract
@pytest.mark.parametrize(
    "invalid_brand, expected_field",
    [
        pytest.param({"id": "1", "brand": "Polo"}, "id", id="string-id"),
        pytest.param({"id": 1}, "brand", id="missing-brand"),
        pytest.param({"id": 1, "brand": None}, "brand", id="null-brand"),
    ],
)
def test_invalid_brand_is_rejected(invalid_brand, expected_field):
    payload = {"responseCode": 200, "brands": [invalid_brand]}

    with pytest.raises(ValidationError) as error:
        BrandsListResponse.model_validate(payload)

    locations = [item["loc"] for item in error.value.errors()]
    assert ("brands", 0, expected_field) in locations
```

Разбор «магии»:

- `parametrize` создаёт три запуска одной функции. Значения строки передаются в аргументы `invalid_brand` и `expected_field`.
- `id="string-id"` задаёт читаемое имя варианта в выводе pytest.
- `pytest.raises(ValidationError)` означает: **этот фрагмент обязан выбросить указанное исключение**. Если модель примет неправильные данные, тест упадёт.
- `as error` позволяет исследовать пойманное исключение. Само исключение находится в `error.value`.
- `.errors()` даёт список подробностей. `loc` — путь к проблемному полю.
- `("brands", 0, "id")` читается как «поле `id` первого элемента списка `brands`». Индексация начинается с нуля.

```bash
python -m pytest -m contract -v
```

В этом новом файле ожидается **3 passed**, без HTTP-запросов. Тесты зелёные именно потому, что неправильные данные отклонены.

Временно уберите `strict=True` из модели `Brand` и повторите запуск: вариант `string-id` должен упасть с `DID NOT RAISE`. Верните настройку и убедитесь, что все три варианта снова проходят.

При настоящем API-запросе `ValidationError` не перехватываем через `pytest.raises`: корректный ответ должен пройти валидацию. Иначе можно случайно написать тест, который ожидает дефект сервера.

## 7. Результат в Allure и типичные ошибки

```bash
python -m pytest -m api -v
allure serve allure-results
```

Сначала запускайте полный API-набор, затем открывайте отчёт. В проекте есть `--clean-alluredir`: каждый новый прогон очищает предыдущие сырые результаты.

В GET-тесте найдите шаг «Проверить схему ответа брендов». Вложения с запросом и ответом по-прежнему создаёт существующий `AllureApiClient`. Отдельный клиент или новое логирование ради Pydantic не нужны.

В этой связке pytest/Allure неперехваченный `ValidationError` может отображаться как **Broken**, а не **Failed**. Смотрите шаг, тип исключения и путь к полю; оба результата требуют разбора и делают pytest-прогон неуспешным.

| Симптом | Что проверить |
|---|---|
| `ModuleNotFoundError: pydantic` | Зависимость установлена именно в выбранный venv |
| У `BaseModel` нет `model_validate` | Версию Pydantic: урок рассчитан на 2.x |
| `Brand object is not subscriptable` | Старое `brand["id"]` заменить на `brand.id` |
| Ошибка по `responseCode` | Во входном словаре нужен ключ API; Python-имя доступно через атрибут после разбора |
| Строковый id проходит | Строгая настройка нужна и у вложенной модели `Brand` |
| `fixture 'brands_service' not found` | Имя аргумента и расположение `conftest.py` |
| `JSONDecodeError` | Ответ не является JSON: посмотреть статус и тело в Allure |

Вопросы для самопроверки:

1. Почему `response.json()` недостаточно для проверки контракта?
2. Почему `brands=[]` проходит модель, но не наш функциональный тест?
3. Почему `strict=True` и `extra="forbid"` — разные решения?
4. Где теперь искать причину, если API переименовал `brand` в `name`?

## Самостоятельная практика

### Обязательная часть: перенести тот же подход на товары

В своей ветке создайте `api/models/products.py` с моделями `Product` и `ProductsListResponse`. В качестве основы используйте реальный ответ `GET /productsList`:

```json
{
  "responseCode": 200,
  "products": [
    {
      "id": 1,
      "name": "Blue Top",
      "price": "Rs. 500",
      "brand": "Polo",
      "category": {
        "usertype": {"usertype": "Women"},
        "category": "Tops"
      }
    }
  ]
}
```

Для обязательной части достаточно явно описать `id`, `name`, `price`, `brand`. Поле `category` пока разрешается игнорировать через `extra="ignore"`: это **частичная проверка схемы**, а не полное покрытие ответа.

Обратите внимание: `price` в этом API — строка с обозначением валюты. Не объявляйте её `float` и не подменяйте контракт удобным для нас представлением.

Что сделать:

1. Включить строгую проверку типов и alias для `responseCode`.
2. Перевести `ProductsService.get_products()` на `list[Product]` по образцу брендов.
3. Обновить тест: непустой каталог, положительные уникальные id и непустые названия. Использовать атрибуты моделей.
4. Проверить, что существующий тест неподдерживаемого POST остался рабочим. Модель успешного каталога к этому ответу не применять.
5. Запустить `python -m pytest -m api -v`, отправить изменения в отдельную ветку и открыть PR.

В PR приложите результат прогона и ответьте тремя предложениями: что проверяет модель, что осталось в тесте и зачем понадобился строгий режим.

**Готово, когда:** старые тесты не потеряны; схемы не размазаны по тестам; строки вместо целочисленных id отклоняются; полный API-набор проходит при доступном стенде.

### По желанию

- Опишите вложенные модели `Category` и `UserType`, чтобы валидировать `category.usertype.usertype` и `category.category`.
- Сделайте отдельную модель ответа ошибки с `response_code` и `message` для неподдерживаемого POST. Не превращайте успешную модель в набор необязательных полей.

## Шпаргалка

| Место | Ответственность |
|---|---|
| `api/client.py` | HTTP, базовый URL, таймаут, Session |
| `api/models/brands.py` | Обязательные поля и типы тела ответа |
| `api/services/brands_service.py` | Endpoint, вызов клиента, HTTP-статус, валидация, код операции |
| `tests/api_tests/test_brands.py` | Ожидаемое содержимое каталога |
| `tests/api_tests/test_brand_contract.py` | Учебная проверка того, что модель отвергает испорченные данные |
| `conftest.py` | Создание зависимостей и закрытие клиента |

`model_validate` — проверить данные и создать модель. `alias` — связать имена API и Python. `strict` — контролировать преобразование типов. `extra` — определить судьбу неизвестных полей. `ValidationError` — объяснить, какие данные не соответствуют модели.

Мы внедрили проверку схемы ответа на стороне потребителя. Это ещё не полный процесс контрактного тестирования между командами и не автоматическая синхронизация с OpenAPI.

## Материалы

- [Урок 1: Service Object, фикстуры и отчёт прогона](https://quality-assurance-engineer.yonote.ru/share/42514619-3245-43f4-9ec6-76d5fbc05e39).
- [Урок 2: развитие Service Object и задел на контракт](https://quality-assurance-engineer.yonote.ru/share/cf8f286d-5344-4428-a89a-374067e8d5ba).
- [Учебный репозиторий](https://github.com/RbBobby/aqa-api-starter-e).
- [Документация учебного API](https://automationexercise.com/api_list).
- [Pydantic: модели](https://docs.pydantic.dev/latest/concepts/models/).
- [Pydantic: строгий режим](https://docs.pydantic.dev/latest/concepts/strict_mode/).
