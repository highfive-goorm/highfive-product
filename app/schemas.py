from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProductBase(BaseModel):
    name: str
    price: int
    category_code: Optional[str] = None
    discount: Optional[int] = None
    payment_id: Optional[int] = None
    purchase_total: Optional[int] = 0
    major_category: Optional[str] = None
    gender: Optional[str] = None
    img_url: Optional[str] = None
    page_view_total: Optional[int] = 0
    product_likes: Optional[int] = 0
    sub_category: Optional[str] = None
    brand: Optional[str] = None
    brand_likes: Optional[int] = 0
    rank: Optional[str] = None
    hits: Optional[str] = None
    ori_price: Optional[int] = None


class ProductCreate(ProductBase):
    created_at: datetime


class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
