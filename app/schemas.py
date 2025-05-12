from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    price: int
    category_code: str
    discount: Optional[int] = 0
    purchase_total: Optional[int] = 0
    major_category: Optional[str]
    gender: Optional[str]
    img_url: Optional[str]
    page_view_total: Optional[int] = 0
    brand_eng: Optional[str]
    product_likes: Optional[int] = 0
    sub_category: Optional[str]
    brand: Optional[str]
    brand_likes: Optional[int] = 0
    rank: Optional[str]
    ori_price: Optional[int]

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductInDB(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
