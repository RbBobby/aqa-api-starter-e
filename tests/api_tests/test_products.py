import allure
import pytest
from api.sevices.products_service import ProductsService
from api.constants import MESSAGE_PUT_BRANDS

@allure.epic("API")
@allure.feature("Products")
@pytest.mark.api
class TestsProductsService:

    @allure.story("GET /productsList")
    @allure.title("Список товаров возвращается")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "products")
    def test_get_products(self, products_service):
        with allure.step("Запросить список товаров"):
            products = products_service.get_products()

            assert isinstance(products, list)
            assert len(products) > 1

    @allure.story("POST /productsList")
    @allure.title("POST на список товаров не поддерживается")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("negative", "products")
    def test_post_products_not_supported(self,products_service):
        with allure.step("Отправить POST через сервис"):
            body = products_service.post_products_not_supported()

        with allure.step("Проверить, что метод запрещён в JSON"):
            assert body["responseCode"] == 405
            assert body["message"] == MESSAGE_PUT_BRANDS
