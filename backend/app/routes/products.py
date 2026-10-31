from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId
from datetime import datetime
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_user, require_role
from ..models.product import ProductCreate, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Public: Browse products ───────────────────────────────────────────────────

@router.get("")
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query: dict = {}

    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    if min_price is not None:
        query.setdefault("price", {})["$gte"] = min_price
    if max_price is not None:
        query.setdefault("price", {})["$lte"] = max_price

    total = await db.products.count_documents(query)
    products = (
        await db.products.find(query)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(page_size)
    )

    # Enrich with ratings
    result = []
    for p in products:
        reviews = await db.reviews.find({"product_id": str(p["_id"])}).to_list(None)
        p["avg_rating"] = (
            round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else 0.0
        )
        p["review_count"] = len(reviews)
        result.append(_serialize(p))

    return {"total": total, "page": page, "page_size": page_size, "products": result}


@router.get("/categories")
async def list_categories():
    db = get_db()
    cats = await db.categories.find({}).to_list(None)
    return [c["name"] for c in cats]


@router.get("/{product_id}")
async def get_product(product_id: str):
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews = await db.reviews.find({"product_id": product_id}).to_list(None)
    product["avg_rating"] = (
        round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else 0.0
    )
    product["review_count"] = len(reviews)
    return _serialize(product)


# ── Seller: Manage own products ───────────────────────────────────────────────

@router.post("", status_code=201)
async def create_product(
    product_in: ProductCreate,
    current_user: dict = Depends(require_role("seller")),
):
    db = get_db()
    doc = {
        **product_in.model_dump(),
        "seller_username": current_user["username"],
        "created_at": datetime.utcnow(),
    }
    result = await db.products.insert_one(doc)
    return {"id": str(result.inserted_id), "message": "Product created"}


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    current_user: dict = Depends(require_role("seller")),
):
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["seller_username"] != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not your product")

    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.products.update_one({"_id": oid}, {"$set": update_data})
    return {"message": "Product updated"}


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(require_role("seller")),
):
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["seller_username"] != current_user["username"]:
        raise HTTPException(status_code=403, detail="Not your product")

    await db.products.delete_one({"_id": oid})
    return {"message": "Product deleted"}


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.get("/{product_id}/reviews")
async def get_reviews(product_id: str):
    db = get_db()
    reviews = await db.reviews.find({"product_id": product_id}).to_list(None)
    return [_serialize(r) for r in reviews]


@router.post("/{product_id}/reviews", status_code=201)
async def add_review(
    product_id: str,
    rating: int,
    comment: Optional[str] = None,
    current_user: dict = Depends(require_role("customer")),
):
    db = get_db()
    # Only one review per user per product
    existing = await db.reviews.find_one(
        {"product_id": product_id, "customer_username": current_user["username"]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    await db.reviews.insert_one({
        "product_id": product_id,
        "customer_username": current_user["username"],
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow(),
    })
    return {"message": "Review submitted"}
