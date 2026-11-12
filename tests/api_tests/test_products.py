import allure
import pytest
from api.sevices.products_service import ProductsService
from api.constants import MESSAGE_PUT_BRANDS
from api.models.products import Product, ErrorResponse

@allure.epic("API")
@allure.feature("Products")
@pytest.mark.api
class TestsProductsService:

    @allure.story("GET /productsList")
    @allure.title("Список товаров возвращается")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "products")
    def test_get_products(self, products_service: ProductsService):
        with allure.step("Запросить список товаров"):
            products = products_service.get_products()

        with allure.step("Каталог не пустой"):
            assert len(products) > 10

        with allure.step("Все id положительные и уникальные"):
            ids = [p.id for p in products]
            assert all(pid > 0 for pid in ids)
            assert len(ids) == len(set(ids))

        with allure.step("Названия не пустые"):
            assert all(p.name.strip() !='' for p in products)

    @allure.story("POST /productsList")
    @allure.title("POST на список товаров не поддерживается")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("negative", "products")
    def test_post_products_not_supported(self,products_service):
        with allure.step("Отправить POST через сервис"):
            response_dict = products_service.post_products_not_supported()
            error = ErrorResponse.model_validate(response_dict)
        with allure.step("Проверить, что метод запрещён в JSON"):
            assert error.response_code == 405
            assert error.message == MESSAGE_PUT_BRANDS
