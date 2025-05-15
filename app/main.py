# product/app/main.py
from typing import List, Optional
from fastapi import FastAPI, Query, Depends, Path, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorClient
from datetime import datetime
from .schemas import CombinedProduct, ProductBase, Brand

app = FastAPI()

def get_db() -> AsyncIOMotorCollection:
    client = AsyncIOMotorClient("mongodb://root:mongodb_product@mongodb_product:27017")
    return client.product.product

def get_brand_db() -> AsyncIOMotorCollection:
    client2 = AsyncIOMotorClient("mongodb://root:mongodb_brand@mongodb_brand:27017")
    return client2.brand.brand

@app.get("/product", response_model=List[CombinedProduct])
async def list_products(
    name: Optional[str] = Query(None, description="상품명 키워드"),
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1. 이름 검색 조건 생성
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    products = await collection.find(query).to_list(length=None)
    brands = await brand_coll.find({}).to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    combined_list = []
    for prod in products:
        # 브랜드 정보 합치기 (brand_id 기준)
        brand_info = brand_map.get(prod.get("brand_id"))
        combined = {**prod}
        if brand_info:
            combined.update({
                "brand_kor": brand_info.get("brand_kor"),
                "brand_eng": brand_info.get("brand_eng"),
                "like_count": brand_info.get("like_count"),
            })
        try:
            combined_list.append(CombinedProduct(**combined))
        except Exception:
            continue
    return combined_list

@app.get("/product/{id}", response_model=CombinedProduct)
async def get_product(
    id: int = Path(..., description="조회할 상품의 ID"),
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db)
):
    prod = await collection.find_one({"id": id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    brand_info = None
    if prod.get("brand_id") is not None:
        brand_info = await brand_coll.find_one({"id": prod["brand_id"]})

    combined = {**prod}
    if brand_info:
        combined.update({
            "brand_kor": brand_info.get("brand_kor"),
            "brand_eng": brand_info.get("brand_eng"),
            "like_count": brand_info.get("like_count"),
        })

    try:
        return CombinedProduct(**combined)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터 변환 오류")

@app.post("/product", response_model=ProductBase, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductBase,
    collection: AsyncIOMotorCollection = Depends(get_db)
):
    now = datetime.utcnow()
    doc = product.dict(exclude_unset=True)
    doc.update({"created_at": now, "updated_at": now})
    result = await collection.insert_one(doc)
    if not result.inserted_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DB 삽입 실패")
    doc["id"] = doc.get("id") or None
    return ProductBase(**doc)

@app.put("/product/{id}", response_model=ProductBase)
async def update_product(
    id: int,
    update: ProductBase,
    collection: AsyncIOMotorCollection = Depends(get_db)
):
    update_data = update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    result = await collection.update_one({"id": id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    updated_doc = await collection.find_one({"id": id})
    return ProductBase(**updated_doc)

@app.delete("/product/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: int,
    collection: AsyncIOMotorCollection = Depends(get_db)
):
    result = await collection.delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return

