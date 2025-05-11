from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorCollection


async def create_product(db: Session, product: schemas.ProductCreate):
    product = models.Product(**product.dict(), created_at=datetime.now())
    db.add(product)
    db.commit()
    db.refresh(product)
    return await product


async def get_products(collection: AsyncIOMotorCollection, keyword: str):
    cursor = collection.find({"name": {"$regex": keyword, "$options": "i"}})
    products = []
    async for doc in cursor:
        products.append(doc)
    return products


async def get_product(collection: AsyncIOMotorCollection, id: int):
    return await collection.find_one({"id": id})


async def update_product(collection: AsyncIOMotorCollection, id: int, update_data: dict):
    await collection.update_one({"id": id}, {"$set": update_data})
    return await collection.find_one({"id": id})


async def delete_product(collection: AsyncIOMotorCollection,id:int):
    result = await collection.delete_one({"id": id})
    return {"deleted": result.deleted_count}
