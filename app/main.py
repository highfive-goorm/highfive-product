# product/app/main.py
from typing import List, Optional
from fastapi import FastAPI, Query, Depends, Path, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorClient
from datetime import datetime
from .schemas import CombinedProduct, ProductBase

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
    # 2. 상품 및 브랜드 데이터 조회
        products = await collection.find(query).to_list(length=None)
    else:
        products= await collection.find().to_list(length=None)
    brands = await brand_coll.find().to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    # 3. 상품과 브랜드 결합
    combined_list = []
    for prod in products:
        brand_info = brand_map.get(prod.get("id"))
        combined = {**prod}

        # 브랜드 필드 추가
        if brand_info:
            combined.update({
                "brand_kor": brand_info.get("brand_kor", ""),
                "brand_eng": brand_info.get("brand_eng", ""),
                "brand_like_count": brand_info.get("like_count", 0),  # 🛠 수정
            })

        try:
            combined_list.append(CombinedProduct(**combined))
        except Exception as e:
            print(f"Error parsing CombinedProduct: {e}")
            continue

    return combined_list


@app.get("/product/{id}", response_model=CombinedProduct)
async def get_product(
        id: int = Path(..., description="조회할 상품의 ID"),
        collection: AsyncIOMotorCollection = Depends(get_db),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db)
):
    # 1. 단일 상품 조회
    prod = await collection.find_one({"id": id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    # 2. 브랜드 정보 결합
    brand_info = await brand_coll.find_one({"id": prod["brand_id"]}) if prod.get("brand_id") else {}
    combined = {**prod}
    if brand_info:
        combined.update({
            "brand_kor": brand_info.get("brand_kor", ""),
            "brand_eng": brand_info.get("brand_eng", ""),
            "brand_like_count": brand_info.get("like_count", 0),  # 🛠 수정
        })

    try:
        return CombinedProduct(**combined)
    except Exception as e:
        print(f"Error parsing CombinedProduct: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터 변환 오류")


@app.post("/product", response_model=ProductBase, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductBase,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    now = datetime.utcnow().timestamp()
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
    update_data["updated_at"] = datetime.utcnow().timestamp()
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
