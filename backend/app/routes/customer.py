"""
Customer-specific routes: profile, recommendations, search tracking.
"""

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from typing import List

from ..core.database import get_db
from ..core.security import require_role
from ..services.recommendation_service import predict_next_categories, is_model_trained

router = APIRouter(prefix="/customer", tags=["Customer"])
customer_only = require_role("customer")


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/profile")
async def get_profile(current_user: dict = Depends(customer_only)):
    db = get_db()
    user = await db.users.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    return _serialize(user)


@router.put("/profile")
async def update_profile(updates: dict, current_user: dict = Depends(customer_only)):
    allowed = {"name", "mobile", "location", "email"}
    update_data = {k: v for k, v in updates.items() if k in allowed}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    db = get_db()
    await db.users.update_one(
        {"username": current_user["username"]}, {"$set": update_data}
    )
    return {"message": "Profile updated"}


@router.get("/recommendations")
async def get_recommendations(current_user: dict = Depends(customer_only)):
    """
    Returns up to 9 recommended products based on the user's purchase
    and browsing history using the trained Decision Tree model.
    Falls back to popular products if the model isn't trained.
    """
    db = get_db()
    uname = current_user["username"]

    # Build user purchase history
    purchases = await db.user_purchases.find({"customer_username": uname}).to_list(None)
    user_history = {p["category"]: p["count"] for p in purchases}

    # Get current cart categories
    cart_items = await db.cart.find({"customer_username": uname}).to_list(None)
    cart_categories = []
    for item in cart_items:
        product = await db.products.find_one({"_id": ObjectId(item["product_id"])})
        if product:
            cart_categories.append(product["category"])

    recommended_products = []

    if is_model_trained() and user_history:
        # Recency context: categories of the latest order and number of orders so far
        last_categories, n_orders = [], await db.orders.count_documents({"customer_username": uname})
        last_order = await db.orders.find_one({"customer_username": uname}, sort=[("created_at", -1)])
        if last_order:
            ids = [ObjectId(i["product_id"]) for i in last_order.get("items", []) if ObjectId.is_valid(i["product_id"])]
            last_categories = list({p["category"] async for p in db.products.find({"_id": {"$in": ids}}, {"category": 1})})
        top_categories = predict_next_categories(
            user_history, cart_categories, top_n=3, last_categories=last_categories, n_orders=n_orders
        )

        for cat in top_categories:
            # Fetch top-rated in-stock products for this category
            pipeline = [
                {"$match": {"category": cat, "quantity": {"$gt": 0}}},
                {"$lookup": {
                    "from": "reviews",
                    "let": {"pid": {"$toString": "$_id"}},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$product_id", "$$pid"]}}},
                        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
                    ],
                    "as": "rating_info",
                }},
                {"$addFields": {
                    "avg_rating": {"$ifNull": [{"$arrayElemAt": ["$rating_info.avg", 0]}, 0]},
                    "review_count": {"$ifNull": [{"$arrayElemAt": ["$rating_info.count", 0]}, 0]},
                }},
                {"$sort": {"avg_rating": -1}},
                {"$limit": 3},
            ]
            products = await db.products.aggregate(pipeline).to_list(3)
            for p in products:
                recommended_products.append({**_serialize(p), "recommendation_reason": f"Based on your {cat} purchases"})

    # Fallback: return top-rated products overall (excluding already purchased ones)
    if not recommended_products:
        purchased_ids = []
        orders = await db.orders.find({"customer_username": uname}).to_list(None)
        for order in orders:
            for item in order.get("items", []):
                purchased_ids.append(item["product_id"])

        pipeline = [
            {"$match": {"quantity": {"$gt": 0}}},
            {"$lookup": {
                "from": "reviews",
                "let": {"pid": {"$toString": "$_id"}},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$product_id", "$$pid"]}}},
                    {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
                ],
                "as": "rating_info",
            }},
            {"$addFields": {
                "avg_rating": {"$ifNull": [{"$arrayElemAt": ["$rating_info.avg", 0]}, 0]},
                "review_count": {"$ifNull": [{"$arrayElemAt": ["$rating_info.count", 0]}, 0]},
            }},
            {"$sort": {"avg_rating": -1, "review_count": -1}},
            {"$limit": 9},
        ]
        products = await db.products.aggregate(pipeline).to_list(9)
        recommended_products = [
            {**_serialize(p), "recommendation_reason": "Popular product"} for p in products
        ]

    return {"recommendations": recommended_products, "count": len(recommended_products)}


@router.post("/search-track")
async def track_search(keyword: str, current_user: dict = Depends(customer_only)):
    """Record a search keyword for recommendation training data."""
    db = get_db()
    await db.user_searches.update_one(
        {"customer_username": current_user["username"], "keyword": keyword.lower()},
        {"$inc": {"count": 1}},
        upsert=True,
    )
    return {"message": "Search tracked"}
