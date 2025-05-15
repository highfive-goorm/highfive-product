from bson import ObjectId
from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


Base = declarative_base()


class ProductBase(BaseModel):
    id: Union[str, int]
    name: str
    discounted_price: Optional[int]
    category_code: str
    discount: Optional[int] = 0
    purchase_total: Optional[int] = 0
    major_category: Optional[str] =None
    gender: Optional[str]
    img_url: Optional[str]
    product_like: Optional[int] = 0
    sub_category: Optional[str]

    rank: Optional[int]
    price: Optional[int]

    created_at: datetime
    updated_at: datetime

    brand_id:Optional[int]=0
    brand_kor:Optional[str]=''
    brand_eng:Optional[str]=''
    brand_like:Optional[int]=''
class Brand(BaseModel):  # MySQL 테이블명

    brand_id :Optional[str]
    brand_kor :Optional[str]
    brand_eng :Optional[str]
    brand_like :Optional[int]
    created_at :datetime
    updated_at : datetime
