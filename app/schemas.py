from pydantic import BaseModel
from typing import Optional

class Brand(BaseModel):
    id: int
    brand_kor: Optional[str]
    brand_eng: Optional[str]
    like_count: Optional[int]           # ← 실제 DB에 맞춤
    created_at: Optional[float]
    updated_at: Optional[float]

class ProductBase(BaseModel):
    id: int
    name: Optional[str]
    discounted_price: Optional[float]
    category_code: Optional[str]
    discount: Optional[float]
    major_category: Optional[str]
    gender: Optional[str]
    img_url: Optional[str]
    like_count: Optional[int]
    view_count: Optional[int]
    purchase_count: Optional[int]
    sub_category: Optional[str]
    rank: Optional[int]
    price: Optional[float]
    created_at: Optional[float]
    updated_at: Optional[float]
    brand_id: int  # ← brand_id는 상품 기준, 반드시 포함

class CombinedProduct(ProductBase):
    # 브랜드 정보도 추가해서 한 번에 전달
    brand_kor: Optional[str]
    brand_eng: Optional[str]
    brand_like_count: Optional[int]
