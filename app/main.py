from fastapi import APIRouter, FastAPI, HTTPException

from . import crud
from .database import db
from .schemas import ProductBase
from fastapi import Depends

app = FastAPI

router = APIRouter()


def get_db():
    return db


@router.get('/products/{keyword}', response_model=ProductBase)
async def get_products(keyword: str, collection=Depends(get_db())):
    product = await collection.find({"name": keyword})
    return product

@router.get("/product/{id}", response_model=ProductBase)
async def get_product(id: int, product: ProductBase, collection=Depends(get_db)):
    result = await crud.get_product(collection, id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result
@router.put("/product/{id}", response_model=ProductBase)
async def update_product(id: int, product: ProductBase, collection=Depends(get_db)):
    result = await crud.update_product(collection, id, product.dict())
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/product/{id}")
async def delete_product(id: int, collection=Depends(get_db)):
    result = await crud.delete_product(collection, id)
    if result["deleted"] == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return result
