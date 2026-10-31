from motor.motor_asyncio import AsyncIOMotorClient
from .config import get_settings

settings = get_settings()

client: AsyncIOMotorClient = None
db = None


async def connect_db(create_indexes: bool = True):
    global client, db
    client = AsyncIOMotorClient(
        settings.mongo_url,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
    )
    db = client[settings.db_name]
    if not create_indexes:
        return

    # Create indexes
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)
    await db.products.create_index("seller_username")
    await db.products.create_index("category")
    await db.orders.create_index("customer_username")
    await db.orders.create_index("seller_username")
    await db.cart.create_index("customer_username")
    await db.user_searches.create_index("customer_username")
    await db.reviews.create_index("product_id")
    print("✅ Connected to MongoDB")


async def ping_database():
    if client is None:
        raise RuntimeError("MongoDB client has not been initialized")
    await client.admin.command("ping")


async def close_db():
    global client
    if client:
        client.close()
        print("🔌 Disconnected from MongoDB")


def get_db():
    return db
