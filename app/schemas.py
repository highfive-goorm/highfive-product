# product/app/schemas.py
from pydantic import BaseModel
from typing import Optional


class Brand(BaseModel):
    id: int
    brand_kor: Optional[str]
    brand_eng: Optional[str]
    like_count: Optional[int]  # 필드명 수정
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
    brand_id: int  # brand_id는 필수


class CombinedProduct(ProductBase):
    # 브랜드 정보
    brand_kor: Optional[str]
    brand_eng: Optional[str]
    brand_like_count: Optional[int]  # 필드명 수정
