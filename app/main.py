from asyncio.log import logger
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Query, Depends
from datetime import datetime
from typing import List, Dict, Any, Any as TypingAny
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from .database import MONGO_URI2
from .schemas import ProductBase, Brand

app = FastAPI()


def get_db() -> AsyncIOMotorCollection:
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient("mongodb://root:mongodb_product@mongodb_product:27017")
    return client.product.product  # db.product, collection `product`


def get_brand_db() -> AsyncIOMotorCollection:
    from motor.motor_asyncio import AsyncIOMotorClient
    client2 = AsyncIOMotorClient(MONGO_URI2)
    return client2.brand.brand  # db.product, collection `product`


@app.post(
    "/product",
    response_model=ProductBase,
    status_code=status.HTTP_201_CREATED
)
async def create_product(
        product: ProductBase,
        collection: AsyncIOMotorCollection = Depends(get_db),
        b_coll: AsyncIOMotorCollection = Depends(get_brand_db),
):
    # 1) 컬렉션 연결 확인
    if collection is None or b_coll is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB 연결 오류"
        )

    # 2) 문서 준비
    now = datetime.utcnow()
    doc = product.dict(exclude_unset=True)  # 클라이언트가 보낸 필드만
    doc.update({"created_at": now, "updated_at": now})

    # 3) DB 삽입
    result = await collection.insert_one(doc)
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 삽입 실패"
        )

    # 4) 반환용 ID 세팅: ObjectId → 문자열
    new_id = str(result.inserted_id)
    doc["id"] = new_id

    # 5) Brand 조회 & Pydantic 변환
    brand_schema: Optional[Brand] = None
    brand_id = doc.get("id")
    if brand_id is not None:
        brand_doc = await b_coll.find_one({"id": brand_id})
        if not brand_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand not found"
            )
        # Mongo dict → Brand 모델
        brand_schema = Brand(**brand_doc)

    # 6) 최종 ProductBase 응답 생성
    return ProductBase(**{**doc, "brand": brand_schema})


@app.get(
    "/product",
    response_model=List[ProductBase],
    status_code=status.HTTP_200_OK
)
async def list_products(
    collection: AsyncIOMotorCollection = Depends(get_db),
    brand_coll: AsyncIOMotorCollection = Depends(get_brand_db)
):
    """
    모든 상품 문서와 브랜드 문서를 조회하여 브랜드 요소를 병합한 후 리스트로 반환합니다.
    """
    if not collection or not brand_coll:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB 연결 오류"
        )

    try:
        products: List[ProductBase] = []

        # 각 product 문서 순회
        async for raw in collection.find({}):
            # a) MongoDB _id → id
            oid = raw.pop("_id", None)
            raw_id: TypingAny = str(oid) if oid is not None else None
            if isinstance(raw_id, str) and raw_id.isdigit():
                raw_id = int(raw_id)
            raw["id"] = raw_id

            # b) brand_id로 브랜드 문서 조회
            b_id = raw.get("brand_id")
            if isinstance(b_id, str) and b_id.isdigit():
                b_id = int(b_id)
            raw["brand_id"] = b_id
            try:
                brand_doc = await brand_coll.find_one({"brand_id": b_id})
            except Exception as e:
                logger.error(f"Brand lookup error for id {b_id}: {e}")
                brand_doc = None
            raw["brand"] = brand_doc.get("name") if brand_doc and "name" in brand_doc else None

            # c) 필드 필터링
            filtered: Dict[str, TypingAny] = {k: raw.get(k) for k in ProductBase.__fields__.keys()}

            # d) Pydantic 모델 생성
            try:
                product = ProductBase(**filtered)
                products.append(product)
            except Exception as e:
                logger.error(f"Validation error for product {filtered.get('id')}: {e}")
                continue

        return products

    except Exception as e:
        logger.error("Error in list_products", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상품 목록 조회 중 오류: {e}"
        )

@app.get(
    "/product/{id}",
    response_model=ProductBase,
)
async def get_product(
        id: int,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB 연결 오류"
        )
    product = await collection.find_one({"id": id})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    brand_coll = collection.database.get_collection("brand")
    if product.get("brand_id"):
        brand_doc = await brand_coll.find_one({"brand_id": product.get("brand_id")})
        product["brand"] = brand_doc.get("name") if brand_doc else None
    product["id"] = int(product.get("id")) if isinstance(product.get("id"), str) and product.get(
        "id").isdigit() else product.get("id")

    return ProductBase(**product)


@app.put(
    "/product/{id}",
    response_model=ProductBase
)
async def update_product(
        id: int,
        update: ProductBase,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 연결 오류"
        )

    update_data = update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    result = await collection.update_one(
        {"id": id}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    updated_doc = await collection.find_one({"id": id})
    if updated_doc.get("brand_id"):
        brand_coll = collection.database.get_collection("brand")
        brand_doc = await brand_coll.find_one({"brand_id": updated_doc.get("brand_id")})
        updated_doc["brand"] = brand_doc.get("name") if brand_doc else None
    updated_doc["id"] = int(updated_doc.get("id")) if isinstance(updated_doc.get("id"), str) and updated_doc.get(
        "id").isdigit() else updated_doc.get("id")

    return ProductBase(**updated_doc)


@app.delete(
    "/product/{id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_product(
        id: int,
        collection: AsyncIOMotorCollection = Depends(get_db)
):
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DB 연결 오류"
        )

    result = await collection.delete_one({"id": id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
