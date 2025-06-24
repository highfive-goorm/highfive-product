import os
from pathlib import Path
# from redis.asyncio import Redis
from dotenv import load_dotenv, find_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(find_dotenv(usecwd=True))

user = os.getenv('MONGO_USER')
password = os.getenv('MONGO_PASSWORD')
hosts = os.getenv('MONGO_HOSTS')
db_name = os.getenv('MONGO_DB')
replica_set = os.getenv('MONGO_REPLICA_SET')

MONGO_URI = (
    f"mongodb://{user}:{password}@{hosts}/{db_name}?authSource=admin&replicaSet={replica_set}"
)

# # 로컬에서 테스트할 때 쓸 코드
# # 위의 코드 안 먹히면 그냥 아래 꺼 주석 풀고 쓸 생각
# single_host = "localhost:27017" # 테스트하려는 노드의 로컬 주소

# MONGO_URI = (
#     f"mongodb://{user}:{password}@{single_host}/{db_name}"
#     f"?authSource=admin&directConnection=true"
# )

client = AsyncIOMotorClient(MONGO_URI)

db = client[os.getenv('MONGO_DB')]

product_collection = db['product']
brand_collection = db['brand']
likes_coll = db['likes']
brand_likes_coll = db['brand_likes']
# redis_url = f"redis://{os.getenv('REDIS_URL')}"
# redis = Redis.from_url(redis_url, decode_responses=True)
