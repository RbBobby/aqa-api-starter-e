import allure
import pytest

@allure.epic("API")
@allure.feature("Products")
@allure.story("GET /productsList")
@allure.title("Список товаров возвращается")
@allure.severity(allure.severity_level.CRITICAL)
@allure.tag("smoke", "products")
@pytest.mark.api
def test_get_products(api_client):
    with allure.step("Запросить список товаров"):
        response = api_client.get("/productsList")
        body = response.json()

    with allure.step("Проверить HTTP 200 и непустой список"):
        assert response.status_code == 200
        assert body["responseCode"] == 201
        assert body["products"]
        assert body["products"][0]["brand"]


@allure.epic("API")
@allure.feature("Products")
@allure.story("POST /productsList")
@allure.title("POST на список товаров не поддерживается")
@allure.severity(allure.severity_level.NORMAL)
@allure.tag("negative", "products")
@pytest.mark.api
def test_post_products_not_supported(api_client):
    with allure.step("Отправить POST /productsList"):
        response = api_client.post("/productsList")
        body = response.json()

    with allure.step("Проверить, что метод запрещён в JSON"):
        # HTTP 200, ошибка в JSON — особенность этого API
        assert response.status_code == 200
        assert body["responseCode"] == 405
        assert body["message"] == "This request method is not supported."
