from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# 기존 ProductBase 스키마 예시
class ProductBase(BaseModel):
    id: Optional[int]
    name: Optional[str]
    discounted_price: Optional[float]
    category_code: Optional[str]
    discount: Optional[float]
    major_category: Optional[str]
    gender: Optional[str]
    img_url: Optional[str]
    like_count: Optional[int]
    view_count: Optional[int]
    purchase_count:Optional[int]
    sub_category: Optional[str]
    rank: Optional[int]
    price: Optional[float]
    created_at: datetime
    updated_at: datetime


# 새로운 브랜드 관련 모델
class Brand(BaseModel):
    id: int
    brand_kor: Optional[str]
    brand_eng: Optional[str]
    brand: Optional[str]
    brand_likes: Optional[int]


# 상품과 브랜드를 하나의 객체로 합친 모델
class CombinedProduct(ProductBase, Brand):
    """
    ProductBase와 BrandModel을 상속받아
    모든 필드를 하나의 모델로 담습니다.
    """
    pass
