from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    price: float = Field(..., gt=0)
    quantity: int = Field(..., ge=0)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductOut(BaseModel):
    id: str
    name: str
    category: str
    price: float
    quantity: int
    description: Optional[str]
    image_url: Optional[str]
    seller_username: str
    seller_name: Optional[str] = None
    avg_rating: float = 0.0
    review_count: int = 0
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
