import os

BASE_URL = os.getenv("API_BASE_URL", "https://automationexercise.com/api").rstrip("/")
TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

MESSAGE_PUT_BRANDS = "This request method is not supported."