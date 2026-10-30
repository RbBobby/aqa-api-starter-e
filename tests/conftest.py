import json

import allure
import pytest
from requests import Response

from api.client import ApiClient


def _attach_http(response: Response) -> None:
    request = response.request
    request_lines = [f"{request.method} {request.url}"]
    if request.body:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        request_lines.extend(["", str(body)])

    allure.attach(
        "\n".join(request_lines),
        name="Request",
        attachment_type=allure.attachment_type.TEXT,
    )

    try:
        payload = json.dumps(response.json(), indent=2, ensure_ascii=False)
        attachment_type = allure.attachment_type.JSON
    except ValueError:
        payload = response.text
        attachment_type = allure.attachment_type.TEXT

    allure.attach(
        payload,
        name=f"Response [{response.status_code}]",
        attachment_type=attachment_type,
    )


class AllureApiClient(ApiClient):
    def get(self, path: str, **kwargs) -> Response:
        with allure.step(f"GET {path}"):
            response = super().get(path, **kwargs)
            _attach_http(response)
            return response

    def post(self, path: str, **kwargs) -> Response:
        with allure.step(f"POST {path}"):
            response = super().post(path, **kwargs)
            _attach_http(response)
            return response


@pytest.fixture(scope="session")
def api_client():
    client = AllureApiClient()
    yield client
    client.close()


def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("api") or item.get_closest_marker("ui"):
            continue
        if "ui" in item.path.parts:
            item.add_marker(pytest.mark.ui)
        else:
            item.add_marker(pytest.mark.api)
