from pydantic import BaseModel, Field
from typing import Optional


class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemOut(BaseModel):
    id: str
    product_id: str
    product_name: str
    price: float
    quantity: int
    image_url: Optional[str]
    seller_username: str
    available_quantity: int
    subtotal: float
