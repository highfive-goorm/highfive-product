from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)

db = client["product"]  # 데이터베이스 이름
products_collection = db["product"]  # 컬렉션 (테이블에 해당)

