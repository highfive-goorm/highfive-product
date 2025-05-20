from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = (
    "mongodb://root:mongodb_product@mongodb_product:27017"
    "/product?authSource=admin"
)
MONGO_URI2 = (
    "mongodb://root:mongodb_brand@mongodb_brand:27017"
    "/brand?authSource=admin"
)

client = AsyncIOMotorClient(MONGO_URI)
client2 = AsyncIOMotorClient(MONGO_URI2)

db = client["product"]
db2 = client2["brand"]

product_collection = db["product"]
brand_collection = db2["brand"]