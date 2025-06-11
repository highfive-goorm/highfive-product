# File: product/app/main.py

# File: product/app/main.py

from typing import List, Optional
import time
import os
import logging

from fastapi import FastAPI, Query, Depends, Path, HTTPException, Header, status, Request
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from datetime import datetime
from pymongo.errors import ServerSelectionTimeoutError
import asyncio

# from redis.asyncio import Redis

from .database import product_collection, brand_collection, db, likes_coll, brand_likes_coll # redis
from .schemas import CombinedProduct, ProductBase, PaginatedProducts, BulkProduct, BulkRequest, LikeRequest, \
    UserLikedProductsResponse, UserLikedBrandsResponse

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


async def get_brand_likes_coll() -> AsyncIOMotorCollection:
    return brand_likes_coll


# async def get_redis() -> Redis:
#     return redis


async def get_likes_db() -> AsyncIOMotorCollection:
    return likes_coll


async def get_user_id(x_user_id: str = Header(..., description="사용자 ID")):
    return x_user_id


# Auxiliary collections for logging
view_collection = db["product_views"]
purchase_collection = db["product_purchases"]


# Middleware: 한 요청당 한 줄 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path == "/health":
        response = await call_next(request)
        return response
    
    start = time.time()
    response = await call_next(request)
    elapsed_ms = (time.time() - start) * 1000

    # 탭 구분 api_request 로그
    params_info = ""
    if request.url.path == "/product":
        qp = request.query_params
        params_info = (
            f"\tname={qp.get('name', '')}"
            f"\tmajor_category={qp.get('major_category', '')}"
            f"\tgender={qp.get('gender', '')}"
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

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}

# Endpoints
@app.get("/product", response_model=PaginatedProducts)
async def list_products(
        name: Optional[str] = Query(None, description="상품명 키워드"),
        major_category: Optional[str] = Query(None, description="메이저 카테고리"),
        gender: Optional[str] = Query(None, description="성별 (M/F/U 등)"),
        brand_id: Optional[int] = Query(None, description="브랜드 ID"),
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
    if brand_id is not None:
        query["brand_id"] = brand_id

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


@app.post(
    "/product/{id}/like",
    status_code=status.HTTP_201_CREATED,
    summary="상품 좋아요"
)
async def like_product(
        id: int,
        body: LikeRequest,
        like_coll: AsyncIOMotorDatabase = Depends(get_likes_db),
        # redis: Redis = Depends(get_redis),
        product_collection: AsyncIOMotorDatabase = Depends(get_db)
):
    # 1) 이미 좋아요 했는지 확인
    exists = await like_coll.find_one({
        "id": id,
        "user_id": body.user_id
    })
    if exists:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="이미 좋아요한 상태입니다.")

    # 2) MongoDB에 기록
    await likes_coll.insert_one({
        "id": id,
        "user_id": body.user_id,
        "created_at": datetime.utcnow()
    })
    update_result = await product_collection.update_one(
        {"id": id},
        {"$inc": {"like_count": 1}}
    )
    if update_result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "상품을 찾을 수 없습니다.")
    # 3) Redis set에 추가
    # await redis.sadd(f"likes:{id}", body.user_id)

    return {"message": "좋아요 처리되었습니다."}


@app.delete(
    "/product/{id}/like/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="상품 좋아요 취소"
)
async def unlike_product(
        id: int,
        user_id: str,
        likes_coll: AsyncIOMotorCollection = Depends(get_likes_db),
        # redis: Redis = Depends(get_redis),
        product_collection: AsyncIOMotorCollection = Depends(get_db)
):
    delete_result = await likes_coll.delete_one({"id": id, "user_id": user_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="좋아요 내역이 없습니다."
        )
    update_result = await product_collection.update_one(
        {"id": id},
        {"$inc": {"like_count": -1}}
    )
    if update_result.matched_count == 0:
        # 삭제는 됐지만, 상품 자체가 없으면 복구용으로 1 되돌리기
        await product_collection.update_one({"id": id}, {"$inc": {"like_count": -1}})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="상품을 찾을 수 없습니다."
        )
    # await redis.srem(f"likes:{id}", user_id)
    return {"message": "좋아요가 취소되었습니다."}


@app.get(
    "/product/like/count/{user_id}",
    response_model=UserLikedProductsResponse,
    summary="사용자가 좋아요한 상품 ID 리스트 조회"
)
async def get_user_liked_products(
        user_id: str,
        likes_coll: AsyncIOMotorDatabase = Depends(get_likes_db),
        product_collection: AsyncIOMotorCollection = Depends(get_db)
):
    like_docs = await likes_coll.find({"user_id": user_id}).to_list()
    if not like_docs:
        raise HTTPException(status_code=200, detail="좋아요 내역이 없습니다.")

    # 2) ID 리스트 추출 (중복 제거를 원하면 set(...) 사용)
    ids = [doc["id"] for doc in like_docs]

    # 3) products 컬렉션에서 id, name, img_url 필드만 Projection 하여 조회
    prod_docs = await product_collection.find(
        {"id": {"$in": ids}},
        {"id": 1, "name": 1, "img_url": 1}
    ).to_list(length=None)

    # 4) 원래 users liked 순으로 정렬하려면:
    prod_map = {p["id"]: p for p in prod_docs}
    ordered = [prod_map[i] for i in ids if i in prod_map]

    return UserLikedProductsResponse(user_id=user_id, like_products=ordered)


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
        prod_coll: AsyncIOMotorCollection = Depends(get_db),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1) 상품 일괄 조회
    products = await prod_coll.find({"id": {"$in": req.product_ids}}).to_list(length=None)

    # 2) 관련 브랜드 일괄 조회
    brand_ids = [p["brand_id"] for p in products if p.get("brand_id") is not None]
    brands = await brand_coll.find({"id": {"$in": brand_ids}}).to_list(length=None)
    brand_map = {b["id"]: b for b in brands}

    # 3) BulkProduct 객체 생성 (brand_kor, brand_eng, brand_like_count 포함)
    result: List[BulkProduct] = []
    for p in products:
        b = brand_map.get(p["brand_id"], {})
        combined = {
            **p,
            "brand_kor": b.get("brand_kor"),
            "brand_eng": b.get("brand_eng"),
        }
        try:
            result.append(BulkProduct(**combined))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"데이터 직렬화 오류: {e}"
            )
    return result


# brand 좋아요
@app.post(
    "/brand/{id}/like",
    status_code=status.HTTP_201_CREATED,
    summary="브랜드 좋아요"
)
async def like_brand(
        id: int,
        body: LikeRequest,
        brand_likes_coll: AsyncIOMotorCollection = Depends(get_brand_likes_coll),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
        # redis: Redis = Depends(get_redis),
):
    # 이미 좋아요했는지
    if await brand_likes_coll.find_one({"id": id, "user_id": body.user_id}):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "이미 좋아요한 상태입니다.")

    # 1) 좋아요 기록
    await brand_likes_coll.insert_one({
        "id": id,
        "user_id": body.user_id,
        "created_at": datetime.utcnow()
    })

    # 2) brands 컬렉션 like_count 증가
    res = await brand_coll.update_one(
        {"id": id},
        {"$inc": {"like_count": 1}}
    )
    if res.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "브랜드를 찾을 수 없습니다.")

    # 3) Redis에도 추가
    # await redis.sadd(f"brand:{id}:like_count", body.user_id)

    return {"message": "브랜드 좋아요 처리되었습니다."}


# ─── 브랜드 좋아요 취소 ─────────────────────────────────

@app.delete(
    "/brand/{id}/like/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="브랜드 좋아요 취소"
)
async def unlike_brand(
        id: int,
        user_id: str,
        brand_likes_coll: AsyncIOMotorCollection = Depends(get_brand_likes_coll),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
        # redis: Redis = Depends(get_redis),
):
    # 1) 좋아요 기록 삭제
    result = await brand_likes_coll.delete_one({"id": id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "좋아요 내역이 없습니다.")

    # 2) like_count 감소
    res = await brand_coll.update_one(
        {"id": id},
        {"$inc": {"like_count": -1}}
    )
    if res.matched_count == 0:
        # 삭제는 됐지만 브랜드가 없으면 복구
        await brand_likes_coll.insert_one({
            "id": id,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        })
        raise HTTPException(status.HTTP_404_NOT_FOUND, "브랜드를 찾을 수 없습니다.")

    # 3) Redis에서도 제거
    # await redis.srem(f"brand:{id}:like_count", user_id)

    return {"message": "브랜드 좋아요가 취소되었습니다."}


# ─── 사용자가 좋아요한 브랜드 리스트 조회 ────────────────────────

@app.get(
    "/brand/like/count/{user_id}",
    response_model=UserLikedBrandsResponse,
    summary="사용자가 좋아요한 브랜드 리스트 조회"
)
async def get_user_liked_brands(
        user_id: str,
        brand_likes_coll: AsyncIOMotorCollection = Depends(get_brand_likes_coll),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1) 사용자의 좋아요 기록 조회
    docs = await brand_likes_coll.find({"user_id": user_id}).to_list(length=None)
    if not docs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "좋아요 내역이 없습니다.")

    # 2) 브랜드 ID 리스트
    ids = [doc["id"] for doc in docs]

    # 3) brands 컬렉션에서 id, name, img_url 프로젝션하여 조회
    prods = await brand_coll.find(
        {"id": {"$in": ids}},
        {"id": 1, "brand_kor": 1, "brand_eng": 1,"like_count":1}
    ).to_list(length=None)

    # 4) 좋아요 순(저장 순) 그대로 정렬
    prod_map = {b["id"]: b for b in prods}
    ordered = [prod_map[i] for i in ids if i in prod_map]

    return UserLikedBrandsResponse(user_id=user_id, like_brands=ordered)
