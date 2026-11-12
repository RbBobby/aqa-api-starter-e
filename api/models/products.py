from pydantic import BaseModel, ConfigDict, Field

class UserType(BaseModel):
    model_config = ConfigDict(strict=True)
    usertype: str

class Category(BaseModel):
    model_config = ConfigDict(strict=True)
    category: str
    usertype: UserType

class Product(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    id: int
    name: str
    price: str
    brand: str
    category: Category

class ProductListResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    response_code: int = Field(alias="responseCode")
    products: list[Product]

class ErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    response_code: int = Field(alias="responseCode")
    message: str
