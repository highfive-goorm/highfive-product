# product/app/main.py
from typing import List, Optional
from fastapi import FastAPI, Query, Depends, Path, HTTPException, Header, status
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
from pydantic import BaseModel
from .database import product_collection, brand_collection, db
from .schemas import CombinedProduct, ProductBase, PaginatedProducts
from pymongo.errors import ServerSelectionTimeoutError
import asyncio


app = FastAPI()


# --- Request models ---
class BulkRequest(BaseModel):
    product_ids: List[int]


# --- Dependency overrides ---
async def get_db() -> AsyncIOMotorCollection:
    return product_collection

async def get_brand_db() -> AsyncIOMotorCollection:
    return brand_collection

async def get_user_id(x_user_id: str = Header(..., description="사용자 ID")):
    return x_user_id


@app.on_event("startup")
async def ensure_mongo_indexes():
    for _ in range(5):
        try:
            await product_collection.create_index([("id",1)], unique=True)
            await brand_collection.create_index([("id",1)], unique=True)
            return
        except ServerSelectionTimeoutError:
            await asyncio.sleep(2)
    raise RuntimeError("MongoDB 연결 실패 - 인덱스 생성 불가")


# --- Auxiliary collections for logging ---
view_collection     = db["product_views"]
purchase_collection = db["product_purchases"]


# --- Endpoints ---

@app.get("/product", response_model=PaginatedProducts)
async def list_products(
    name: Optional[str] = Query(None, description="상품명 키워드"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1) 필터링
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    # 2) 전체 개수 조회
    total = await collection.count_documents(query)

    # 3) 페이지네이션
    skip = (page - 1) * size
    products = await collection.find(query).skip(skip).limit(size).to_list(length=size)

    # 4) 브랜드 정보 한 번에 조회 (N+1 방지)
    brands = await brand_coll.find().to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    # 5) 상품·브랜드 결합
    combined_list: List[CombinedProduct] = []
    for prod in products:
        combined = {**prod}
        brand_info = brand_map.get(prod["brand_id"])
        if brand_info:
            combined.update({
                "brand_kor": brand_info["brand_kor"],
                "brand_eng": brand_info["brand_eng"],
                "brand_like_count": brand_info["like_count"],
            })
        combined_list.append(CombinedProduct(**combined))

    # 6) total 과 items 함께 반환
    return PaginatedProducts(total=total, items=combined_list)

@app.get("/product/{id}", response_model=CombinedProduct)
async def get_product(
    id: int = Path(..., description="조회할 상품의 ID"),
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    prod = await collection.find_one({"id": id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    brand_info = await brand_coll.find_one({"id": prod["brand_id"]})
    combined = {**prod}
    if brand_info:
        combined.update({
            "brand_kor": brand_info["brand_kor"],
            "brand_eng": brand_info["brand_eng"],
            "brand_like_count": brand_info["like_count"],
        })

    try:
        return CombinedProduct(**combined)
    except Exception as e:
        print(f"Error parsing CombinedProduct: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터 변환 오류")


@app.post("/product", response_model=ProductBase, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductBase,
    collection: AsyncIOMotorCollection = Depends(get_db),
):
    now = datetime.utcnow().timestamp()
    doc = product.dict(exclude_unset=True)
    doc.update({"created_at": now, "updated_at": now})
    # upsert: 같은 id가 있으면 무시, 없으면 삽입
    await collection.update_one({"id": doc["id"]}, {"$setOnInsert": doc}, upsert=True)
    return ProductBase(**doc)


@app.put("/product/{id}", response_model=ProductBase)
async def update_product(
    id: int,
    update: ProductBase,
    collection: AsyncIOMotorCollection = Depends(get_db),
):
    # 빈 문자열("")은 무시하고, unset 필드만 업데이트
    update_data = {k: v for k, v in update.dict(exclude_unset=True).items() if v != ""}
    if not update_data:
        # 아무 변경사항이 없으면 기존 문서 반환
        existing = await collection.find_one({"id": id})
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
        return ProductBase(**existing)

    update_data["updated_at"] = datetime.utcnow().timestamp()
    result = await collection.update_one({"id": id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    updated_doc = await collection.find_one({"id": id})
    return ProductBase(**updated_doc)


@app.delete("/product/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: int,
    collection: AsyncIOMotorCollection = Depends(get_db),
):
    result = await collection.delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")


@app.post("/product/{id}/view", status_code=status.HTTP_204_NO_CONTENT)
async def view_product(
    id: int,
    user_id: str = Depends(get_user_id),
):
    now = datetime.utcnow().timestamp()
    await view_collection.insert_one({
        "user_id": user_id,
        "product_id": id,
        "viewed_at": now
    })
    await product_collection.update_one({"id": id}, {"$inc": {"view_count": 1}})


@app.post("/product/{id}/purchase", status_code=status.HTTP_204_NO_CONTENT)
async def purchase_product(
    id: int,
    user_id: str = Depends(get_user_id),
):
    now = datetime.utcnow().timestamp()
    await purchase_collection.insert_one({
        "user_id": user_id,
        "product_id": id,
        "purchased_at": now
    })
    await product_collection.update_one({"id": id}, {"$inc": {"purchase_count": 1}})


@app.post("/product/bulk", response_model=List[dict])
async def bulk_products(
    req: BulkRequest,
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1) 상품 일괄 조회
    products = await collection.find({"id": {"$in": req.product_ids}}).to_list(length=None)

    # 2) 브랜드 정보 한 번에 조회
    brand_ids = list({p["brand_id"] for p in products})
    brands = await brand_coll.find(
        {"id": {"$in": brand_ids}}
    ).to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    # 3) 필요한 필드만 추출하여 반환
    result = []
    for prod in products:
        brand_info = brand_map.get(prod["brand_id"], {})
        result.append({
            "id": prod["id"],
            "name": prod["name"],
            "img_url": prod["img_url"],
            "discount": prod["discount"],
            "price": prod["price"],
            "discounted_price": prod["discounted_price"],
            "brand_id": prod["brand_id"],
            "brand_kor": brand_info.get("brand_kor", ""),
            "brand_eng": brand_info.get("brand_eng", ""),
        })
    return result
