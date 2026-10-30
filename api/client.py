import os

import requests

BASE_URL = os.getenv("API_BASE_URL", "https://automationexercise.com/api").rstrip("/")
TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = TIMEOUT) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def close(self) -> None:
        self.session.close()

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", timeout=self.timeout, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
