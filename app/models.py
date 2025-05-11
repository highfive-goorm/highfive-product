from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Product(BaseModel):
    id: Optional[str] = Field(alias="_id")
    name: str
    price: Optional[int]
    category_code: Optional[str]
    discount: Optional[int]
    payment_id: Optional[int]
    purchase_total: Optional[int] = 0
    major_category: Optional[str]
    gender: Optional[str]
    created_at: Optional[datetime] = datetime.utcnow()
    updated_at: Optional[datetime] = datetime.utcnow()
    img_url: Optional[str]
    page_view_total: Optional[int] = 0
    product_likes: Optional[int] = 0
    sub_category: Optional[str]
    brand: Optional[str]
    brand_likes: Optional[int] = 0
    rank: Optional[str]
    hits: Optional[str]
    ori_price: Optional[int]

    class Config:
        from_attributes = True  # FastAPI >= 0.100.0
        populate_by_name = True
