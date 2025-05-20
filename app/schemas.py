from typing import Optional, List
from pydantic import BaseModel

class Brand(BaseModel):
    id: int
    brand_kor: Optional[str] = None
    brand_eng: Optional[str] = None
    like_count: Optional[int] = 0
    created_at: Optional[float]
    updated_at: Optional[float]

class ProductBase(BaseModel):
    id: int
    name: Optional[str] = None
    discounted_price: Optional[float] = 0
    category_code: Optional[str] = None
    discount: Optional[float] = 0
    major_category: Optional[str] = None
    gender: Optional[str] = None
    img_url: Optional[str] = None
    like_count: Optional[int] = 0
    view_count: Optional[int] = 0
    purchase_count: Optional[int] = 0
    sub_category: Optional[str] = None
    rank: Optional[int] = None
    price: Optional[float] = 0
    created_at: Optional[float]
    updated_at: Optional[float]
    brand_id: Optional[int] = None

class CombinedProduct(ProductBase, Brand):
    brand_kor: Optional[str] = None
    brand_eng: Optional[str] = None
    brand_like_count: Optional[int] = 0

class PaginatedProducts(BaseModel):
    total: int
    items: List[CombinedProduct]

class BulkProduct(BaseModel):
    id: int
    name: Optional[str] = None
    img_url: Optional[str] = None
    discount: Optional[float] = 0
    price: Optional[float] = 0
    discounted_price: Optional[float] = 0
    brand_id: Optional[int] = None