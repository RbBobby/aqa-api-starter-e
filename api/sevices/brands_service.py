import allure

from api.client import ApiClient
from api.constants import MESSAGE_PUT_BRANDS
from api.models.brands import Brand, BrandsListResponse

ENDPOINT = "/brandsList"


class BrandsService:
    def __init__(self, api_client: ApiClient) -> None:
        self.api_client = api_client

    def get_brands(self) -> list[Brand]:
        with allure.step("Запросить список брендов"):
            response = self.api_client.get(ENDPOINT)
        with allure.step("Проверить HTTP 200"):
            assert response.status_code == 200, f"Статус код = {response.status_code}"
            assert response.reason == "OK"

        with allure.step("Проверка схемы ответа брендов"):
            parsed = BrandsListResponse.model_validate(response.json())
            assert parsed.response_code == 200

        return parsed.brands

    def upd_brands(self):
        with allure.step("Обновляем список брендов"):
            response = self.api_client.put(ENDPOINT)
            body = response.json()
        with allure.step("Проверить, что метод не рабочий. HTTP 405"):
            assert body["responseCode"] == 405, f"Статус код = {body['responseCode']}"
            assert body["message"] == MESSAGE_PUT_BRANDS, f"Текст = {body['message']}"

        return body

