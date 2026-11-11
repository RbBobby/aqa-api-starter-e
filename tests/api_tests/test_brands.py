import allure
import pytest
from api.sevices.brands_service import BrandsService
from api.constants import MESSAGE_PUT_BRANDS
from api.models.brands import Brand


@allure.epic("API")
@allure.feature("Brands")
@pytest.mark.api
class TestBrands:

    @allure.story("GET /brandsList")
    @allure.title("Список брендов возвращается")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_brands(self, brands_service: BrandsService):
        with allure.step("Получаем список брендов"):
            brands = brands_service.get_brands()

            assert isinstance(brands, list)
            assert len(brands) > 33

        with allure.step("Проверить структуру, типы и уникальность брендов"):
            brand_ids = []

            for brand in brands:
                assert isinstance(brand, Brand)
                assert type(brand.id) is int
                assert brand.id > 0
                assert brand.brand.strip() != ""
                brand_ids.append(brand.id)

            assert len(brand_ids) == len(set(brand_ids))

    @allure.story("PUT /brandsList")
    @allure.title("PUT на список брендов не поддерживается")
    @allure.severity(allure.severity_level.NORMAL)
    def test_put_brands_not_supported(self, brands_service: BrandsService):
        with allure.step("Отправить PUT запрос"):
            body = brands_service.upd_brands()

        with allure.step("Проверить ответ об ошибке"):
            assert body["responseCode"] == 405
            assert body["message"] == MESSAGE_PUT_BRANDS
