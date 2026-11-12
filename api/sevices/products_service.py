import allure

from api.client import ApiClient
from api.constants import MESSAGE_PUT_BRANDS
from api.models.products import Product, ProductListResponse

ENDPOINT = "/productsList"

class ProductsService:
    def __init__(self, api_client: ApiClient) -> None:
        self.api_client = api_client

    def get_products(self):
        with allure.step("Запросить список брендов"):
            response = self.api_client.get(ENDPOINT)
        with allure.step("Проверить HTTP 200"):
            assert response.status_code == 200, f"Статус код = {response.status_code}"
            assert response.reason == "OK"

        with allure.step("Проверка схемы ответа продуктов"):
            parsed = ProductListResponse.model_validate(response.json())
            assert parsed.response_code == 200

        return parsed.products

    def post_products_not_supported(self):
        with allure.step("Обновляем список брендов"):
            # целевой вариант для неподдерживаемого POST:
            response = self.api_client.post(ENDPOINT)
            body = response.json()
        with allure.step("Проверить, что метод не рабочий. responseCode 405"):
            assert body["responseCode"] == 405, f"responseCode = {body['responseCode']}"
            assert body["message"] == MESSAGE_PUT_BRANDS, f"Текст = {body['message']}"
        return body