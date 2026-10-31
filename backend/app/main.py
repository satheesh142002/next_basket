from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.database import connect_db, close_db
from .core.config import get_settings
from .routes import auth, admin, products, cart, orders, seller, customer

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await _seed_default_data()
    await _seed_dataset()
    yield
    await close_db()


async def _seed_default_data():
    """Insert default categories if none exist."""
    from .core.database import get_db
    from datetime import datetime

    db = get_db()
    count = await db.categories.count_documents({})
    if count == 0:
        default_categories = [
            "Electronics", "Clothing", "Books", "Home & Kitchen",
            "Sports & Outdoors", "Beauty & Personal Care", "Toys & Games",
            "Food & Grocery", "Automotive", "Health & Wellness",
        ]
        await db.categories.insert_many(
            [{"name": c, "created_at": datetime.utcnow()} for c in default_categories]
        )
        print(f"✅ Seeded {len(default_categories)} default categories")


async def _seed_dataset():
    """Seed the database with the Sample Superstore dataset on first startup."""
    from .seed_data import seed_database
    try:
        await seed_database()
    except Exception as e:
        print(f"⚠️ Dataset seeding skipped: {e}")


app = FastAPI(
    title="Next Basket API",
    description="Predictive Analytics and Personalized Recommendations for E-Commerce",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(seller.router, prefix="/api")
app.include_router(customer.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
