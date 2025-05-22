# File: product/app/main.py

from typing import List, Optional
import time
import os
import logging

from fastapi import FastAPI, Query, Depends, Path, HTTPException, Header, status, Request
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime
from pymongo.errors import ServerSelectionTimeoutError
import asyncio

from .database import product_collection, brand_collection, db
from .schemas import CombinedProduct, ProductBase, PaginatedProducts, BulkProduct, BulkRequest

# Logging setup
from shared.logging_config import configure_logging

app = FastAPI()

# ───── 로깅 초기화 ─────
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
configure_logging(log_file=os.path.join(LOG_DIR, "product_service.log"))
logger = logging.getLogger("product")

# Dependency overrides
async def get_db() -> AsyncIOMotorCollection:
    return product_collection

async def get_brand_db() -> AsyncIOMotorCollection:
    return brand_collection

async def get_user_id(x_user_id: str = Header(..., description="사용자 ID")):
    return x_user_id

# Auxiliary collections for logging
view_collection = db["product_views"]
purchase_collection = db["product_purchases"]

# Middleware: 한 요청당 한 줄 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000

    # 탭 구분 api_request 로그
    params_info = ""
    if request.url.path == "/product":
        qp = request.query_params
        params_info = (
            f"\tname={qp.get('name','')}"
            f"\tmajor_category={qp.get('major_category','')}"
            f"\tgender={qp.get('gender','')}"
        )
    msg = (
        f"api_request"
        f"\tmethod={request.method}"
        f"\tpath={request.url.path}"
        f"\tstatus_code={response.status_code}"
        f"\tprocess_time_ms={elapsed_ms:.2f}"
        f"{params_info}"
    )
    logger.info(msg)
    return response

@app.on_event("startup")
async def ensure_mongo_indexes():
    for _ in range(5):
        try:
            await product_collection.create_index([("id", 1)], unique=True)
            await brand_collection.create_index([("id", 1)], unique=True)
            await product_collection.create_index([("major_category", 1)], name="idx_major_category")
            await product_collection.create_index([("gender", 1)], name="idx_gender")
            return
        except ServerSelectionTimeoutError:
            await asyncio.sleep(2)
    raise RuntimeError("MongoDB 연결 실패 - 인덱스 생성 불가")

# Endpoints
@app.get("/product", response_model=PaginatedProducts)
async def list_products(
    name: Optional[str] = Query(None, description="상품명 키워드"),
    major_category: Optional[str] = Query(None, description="메이저 카테고리"),
    gender: Optional[str] = Query(None, description="성별 (M/F/U 등)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if major_category:
        query["major_category"] = major_category
    if gender:
        query["gender"] = gender

    total = await collection.count_documents(query)
    skip = (page - 1) * size
    products = await collection.find(query).skip(skip).limit(size).to_list(length=size)

    brands = await brand_coll.find().to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    combined_list: List[CombinedProduct] = []
    for prod in products:
        data = prod.copy()
        if brand := brand_map.get(prod["brand_id"]):
            data.update({
                "brand_kor": brand["brand_kor"],
                "brand_eng": brand["brand_eng"],
                "brand_like_count": brand["like_count"],
            })
        combined_list.append(CombinedProduct(**data))

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
    await collection.update_one({"id": doc["id"]}, {"$setOnInsert": doc}, upsert=True)
    return ProductBase(**doc)

@app.put("/product/{id}", response_model=ProductBase)
async def update_product(
    id: int,
    update: ProductBase,
    collection: AsyncIOMotorCollection = Depends(get_db),
):
    update_data = {k: v for k, v in update.dict(exclude_unset=True).items() if v != ""}
    if not update_data:
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

@app.post("/product/bulk", response_model=List[BulkProduct])
async def bulk_products(
    req: BulkRequest,
    collection: AsyncIOMotorCollection = Depends(get_db),
):
    # 1) 상품 일괄 조회
    products = await collection.find({"id": {"$in": req.product_ids}}).to_list(length=None)

    # 2) 필요한 필드만 추출
    return [
        BulkProduct(
            id=prod["id"],
            name=prod.get("name"),
            img_url=prod.get("img_url"),
            discount=prod.get("discount", 0),
            price=prod.get("price", 0),
            discounted_price=prod.get("discounted_price", 0),
            brand_id=prod.get("brand_id"),
        ) for prod in products
    ]
