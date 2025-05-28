import os
from pathlib import Path
from redis.asyncio import Redis
from dotenv import load_dotenv, find_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(find_dotenv(usecwd=True))
MONGO_URI = (
    f"mongodb://{os.getenv('DB_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_URL')}:{os.getenv('MONGO_PORT')}/{os.getenv('MONGO_DB')}?authSource=admin"
)

client = AsyncIOMotorClient(MONGO_URI)

db = client["product"]

product_collection = db["product"]
brand_collection = db["brand"]
likes_coll = db['likes']
brand_likes_coll = db['brand_likes']
redis_url = "redis://host.docker.internal:6379"
redis = Redis.from_url(redis_url, decode_responses=True)
