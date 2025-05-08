from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from .database import Base

class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer)
    category_code = Column(String(100))
    discount = Column(Integer)
    payment_id = Column(Integer, ForeignKey("payment.id"), nullable=True)
    purchase_total = Column(Integer, default=0)
    major_category = Column(Text)
    gender = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    img_url = Column(String(500))
    page_view_total = Column(Integer, default=0)
    product_likes = Column(Integer, default=0)
    sub_category = Column(String(45))
    brand = Column(String(45))
    brand_likes = Column(Integer, default=0)
    rank = Column(String(45))
    hits = Column(String(45))
    ori_price = Column(Integer)
