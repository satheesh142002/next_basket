from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price: float
    seller_username: str


class OrderCreate(BaseModel):
    items: List[OrderItem]
    total_amount: float


class OrderOut(BaseModel):
    id: str
    customer_username: str
    items: List[OrderItem]
    total_amount: float
    status: str  # pending | confirmed | shipped | delivered | cancelled
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(confirmed|shipped|delivered|cancelled)$")
