from typing import Optional

from pydantic import BaseModel


class Brand(BaseModel):
    id: int
    brand_kor: Optional[str] =None
    brand_eng: Optional[str]=None
    like_count: Optional[int]  =0# 필드명 수정
    created_at: Optional[float]
    updated_at: Optional[float]


class ProductBase(BaseModel):
    id: int
    name: Optional[str]=None
    discounted_price: Optional[float]=0
    category_code: Optional[str]=None
    discount: Optional[float]=0
    major_category: Optional[str]=None
    gender: Optional[str]=None
    img_url: Optional[str]=None
    like_count: Optional[int]=0
    view_count: Optional[int]=0
    purchase_count: Optional[int]=0
    sub_category: Optional[str]=None
    rank: Optional[int]=None
    price: Optional[float]=0
    created_at: Optional[float]
    updated_at: Optional[float]
    brand_id: Optional[int] =None # brand_id는 필수


class CombinedProduct(ProductBase, Brand):
    # 브랜드 정보
    brand_kor: Optional[str] = None  # ← 이렇게
    brand_eng: Optional[str] = None
    brand_like_count: Optional[int] = 0  # 필드명 수정
