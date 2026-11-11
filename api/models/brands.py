from pydantic import BaseModel, ConfigDict, Field


class Brand(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    id: int
    brand: str


class BrandsListResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    response_code: int = Field(alias="responseCode")
    brands: list[Brand]
