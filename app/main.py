from fastapi import APIRouter, FastAPI, HTTPException

from . import crud
from .database import db
from .schemas import ProductBase
from fastapi import Depends

app = FastAPI
router = APIRouter
from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId
from .schemas import ProductCreate, ProductUpdate, ProductInDB
from .database import product_collection


def serialize_product(doc) -> dict:
    del doc["id"]
    return doc


@router.post("/", response_model=ProductInDB, status_code=201)
async def create_product(product: ProductCreate):
    now = datetime.utcnow()
    doc = product.dict()
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await product_collection.insert_one(doc)
    created = await product_collection.find_one({"id": result.inserted_id})
    return serialize_product(created)


@router.get("/", response_model=list[ProductInDB])
async def list_products():
    products = []
    async for doc in product_collection.find():
        products.append(serialize_product(doc))
    return products


@router.get("/{id}", response_model=ProductInDB)
async def get_product(id: int):
    product = await product_collection.find_one({"id": id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.put("/{id}", response_model=ProductInDB)
async def update_product(id: str, update: ProductUpdate):
    update_data = update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    await product_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": update_data}
    )
    product = await product_collection.find_one({"id":id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)


@router.delete("/{id}", status_code=204)
async def delete_product(id: str):
    result = await product_collection.delete_one({"id":id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
