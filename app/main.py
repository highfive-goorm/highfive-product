from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from product.app import crud
from product.app.auth import get_current_user
from product.app.database import SessionLocal
from product.app.schemas import ProductBase

app = FastAPI


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get('/products', response_model=ProductBase)
async def get_products(db: Session = Depends(get_db())):
    return await crud.get_products(db)
