from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime


async def create_product(db: Session, product: schemas.ProductCreate):
    product = models.Product(**product.dict(), created_at=datetime.now())
    db.add(product)
    db.commit()
    db.refresh(product)
    return await product


async def get_products(db: Session):
    return await db.query(models.Product).all()


def get_product(db: Session, id: int):
    return db.query(models.Product).filter(models.Product.id == id).first()


def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        db_product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
    return db_product
