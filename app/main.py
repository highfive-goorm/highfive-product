from asyncio.log import logger
from typing import List, Optional, Dict, Any, Union

from fastapi import FastAPI, HTTPException, Query, Depends, Path
from datetime import datetime
from typing import List, Dict, Any, Any as TypingAny
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from .database import MONGO_URI2
from .schemas import ProductBase, CombinedProduct, Brand

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
    response_model=List[CombinedProduct],
    status_code=status.HTTP_200_OK
)
@app.get("/product", response_model=List[CombinedProduct], status_code=status.HTTP_200_OK)
async def list_products(
        collection: AsyncIOMotorCollection = Depends(get_db),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db)
):
    """
    상품과 브랜드 컬렉션을 zip 으로 묶어 동시에 순회하며,
    CombinedProduct 형태로 합쳐진 리스트를 반환합니다.
    """
    if collection is None or brand_coll is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MongoDB 연결 오류"
        )

    combined_list: List[CombinedProduct] = []

    # 두 커서를 zip 으로 묶어 동시에 순회
    raw_products = await collection.find({}).to_list(length=None)
    raw_brands = await brand_coll.find({}).to_list(length=None)

    # 2) 리스트를 zip으로 묶어 순회
    for raw, br in zip(raw_products, raw_brands):
        # 1) 상품 _id → id
        oid = raw.pop("id", None)
        prod_id: TypingAny = str(oid) if oid is not None else None
        if isinstance(prod_id, str) and prod_id.isdigit():
            prod_id = int(prod_id)
        raw["id"] = prod_id

        # 2) 브랜드 _id → brand_id
        bid = br.pop("id", None)
        brand_id: TypingAny = bid if bid is not None else None
        if isinstance(brand_id, str) and brand_id.isdigit():
            brand_id = int(brand_id)
        # copy brand fields into raw
        raw["brand_id"] = brand_id
        raw["brand_kor"] = br.get("brand_kor")
        raw["brand_eng"] = br.get("brand_eng")
        raw["brand"] = br.get("brand") or br.get("name")
        raw["brand_likes"] = br.get("brand_likes")

        # 3) 합칠 모든 필드를 한번에 unpack
        #    CombinedProduct는 ProductBase + BrandModel 상속이므로
        #    raw 딕셔너리에 있는 모든 필드를 그대로 넘기면 됩니다.
        try:
            combined = CombinedProduct(**raw)
            combined_list.append(combined)
        except Exception as e:
            logger.error(f"Validation error for combined product {prod_id}: {e}")
            continue

    return combined_list


@app.get(
    "/product/{id}",
    response_model=CombinedProduct,
    status_code=status.HTTP_200_OK
)
async def get_combined_product(
        id: int = Path(..., description="조회할 상품의 ID"),
        collection: AsyncIOMotorCollection = Depends(get_db),
        brand_coll: AsyncIOMotorCollection = Depends(get_brand_db)
):
    """
    단일 상품과 해당 브랜드 정보를 합쳐서 반환합니다.
    """
    # 1) 상품 조회
    raw = await collection.find_one({"id": id})
    br = await brand_coll.find_one({"id": id})
    if not raw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    # a) MongoDB _id → raw["id"]
    oid = raw.pop("id", None)
    if oid is not None:
        raw_id = oid
        raw["id"] = raw_id

    if not br:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    # 2) 브랜드 조회

    b_id = br.pop("id", None)
    if b_id is not None:
        b_id = oid
        br["id"] = b_id
    # b) 브랜드 필드 삽입
    raw["brand_id"] = b_id
    raw["brand_kor"] = br.get("brand_kor")
    raw["brand_eng"] = br.get("brand_eng")
    raw["brand"] = (br.get("brand") or br.get("name"))
    raw["brand_likes"] = br.get("brand_likes")

    # 3) CombinedProduct 인스턴스화
    try:
        combined = CombinedProduct(**raw)
    except Exception as e:
        logger.error(f"Validation error for combined product {id}: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터 검증 중 오류가 발생했습니다"
        )

    return combined


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
