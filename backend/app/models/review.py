from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class ReviewOut(BaseModel):
    id: str
    product_id: str
    customer_username: str
    rating: int
    comment: Optional[str]
    created_at: datetime
