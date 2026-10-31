"""
Seller-specific routes: analytics, stock forecast, alerts, profile.
"""

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List

from ..core.database import get_db
from ..core.security import require_role
from ..services.arima_service import forecast_product, get_stock_alerts

router = APIRouter(prefix="/seller", tags=["Seller"])
seller_only = require_role("seller")


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Seller Dashboard Stats ────────────────────────────────────────────────────

@router.get("/stats")
async def seller_stats(current_user: dict = Depends(seller_only)):
    db = get_db()
    uname = current_user["username"]

    total_products = await db.products.count_documents({"seller_username": uname})
    total_orders = await db.orders.count_documents(
        {"items.seller_username": uname, "status": {"$ne": "cancelled"}}
    )

    # Revenue (sum of items belonging to this seller)
    pipeline = [
        {"$match": {"items.seller_username": uname, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$match": {"items.seller_username": uname}},
        {"$group": {"_id": None, "revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}}}},
    ]
    rev_result = await db.orders.aggregate(pipeline).to_list(1)
    revenue = rev_result[0]["revenue"] if rev_result else 0.0

    # Low stock products (quantity <= 10)
    low_stock = await db.products.count_documents({"seller_username": uname, "quantity": {"$lte": 10}})

    return {
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": round(revenue, 2),
        "low_stock_products": low_stock,
    }


# ── Sales Analytics ────────────────────────────────────────────────────────────

@router.get("/analytics/sales")
async def sales_analytics(current_user: dict = Depends(seller_only)):
    db = get_db()
    uname = current_user["username"]

    # Last 12 months monthly sales
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    pipeline = [
        {"$match": {
            "items.seller_username": uname,
            "status": {"$ne": "cancelled"},
            "created_at": {"$gte": twelve_months_ago},
        }},
        {"$unwind": "$items"},
        {"$match": {"items.seller_username": uname}},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
            },
            "revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
            "units": {"$sum": "$items.quantity"},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    monthly = await db.orders.aggregate(pipeline).to_list(None)
    monthly_data = [
        {
            "month": f"{r['_id']['year']}-{r['_id']['month']:02d}",
            "revenue": round(r["revenue"], 2),
            "units": r["units"],
            "orders": r["orders"],
        }
        for r in monthly
    ]

    # Sales by category
    cat_pipeline = [
        {"$match": {"items.seller_username": uname, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$match": {"items.seller_username": uname}},
        {"$lookup": {
            "from": "products",
            "let": {"pid": {"$toObjectId": "$items.product_id"}},
            "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", "$$pid"]}}}],
            "as": "product_info",
        }},
        {"$unwind": {"path": "$product_info", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$product_info.category",
            "revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
            "units": {"$sum": "$items.quantity"},
        }},
        {"$sort": {"revenue": -1}},
    ]
    by_category = await db.orders.aggregate(cat_pipeline).to_list(None)
    category_data = [
        {"category": r["_id"] or "Unknown", "revenue": round(r["revenue"], 2), "units": r["units"]}
        for r in by_category
    ]

    # Top products
    top_pipeline = [
        {"$match": {"items.seller_username": uname, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$match": {"items.seller_username": uname}},
        {"$group": {
            "_id": "$items.product_id",
            "product_name": {"$first": "$items.product_name"},
            "units_sold": {"$sum": "$items.quantity"},
            "revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
        }},
        {"$sort": {"units_sold": -1}},
        {"$limit": 10},
    ]
    top_products = await db.orders.aggregate(top_pipeline).to_list(None)
    top_data = [
        {
            "product_id": r["_id"],
            "product_name": r["product_name"],
            "units_sold": r["units_sold"],
            "revenue": round(r["revenue"], 2),
        }
        for r in top_products
    ]

    return {
        "monthly_sales": monthly_data,
        "by_category": category_data,
        "top_products": top_data,
    }


# ── Stock Forecast (ARIMA) ─────────────────────────────────────────────────────

@router.get("/forecast/{product_id}")
async def get_product_forecast(product_id: str, current_user: dict = Depends(seller_only)):
    db = get_db()
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid, "seller_username": current_user["username"]})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Pull order history for this product
    pipeline = [
        {"$match": {"items.product_id": product_id, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$match": {"items.product_id": product_id}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "quantity": {"$sum": "$items.quantity"},
        }},
        {"$sort": {"_id": 1}},
    ]
    history = await db.orders.aggregate(pipeline).to_list(None)
    order_history = [{"date": r["_id"], "quantity": r["quantity"]} for r in history]

    forecast = forecast_product(order_history, product["quantity"])
    forecast["product_id"] = product_id
    forecast["product_name"] = product["name"]
    return forecast


@router.get("/alerts")
async def get_stock_alert_list(current_user: dict = Depends(seller_only)):
    """
    Fast bulk stock-alert check using a single aggregation pipeline.
    Projects 30-day demand from average daily sales, then flags products
    where projected demand exceeds current stock.
    """
    db = get_db()
    uname = current_user["username"]

    # Single aggregation: total units sold + days with sales per product
    pipeline = [
        {"$match": {"items.seller_username": uname, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {"$match": {"items.seller_username": uname}},
        {"$group": {
            "_id": {
                "product_id": "$items.product_id",
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            },
            "daily_qty": {"$sum": "$items.quantity"},
        }},
        {"$group": {
            "_id": "$_id.product_id",
            "total_sold": {"$sum": "$daily_qty"},
            "days_with_sales": {"$sum": 1},
        }},
    ]
    sales_stats = await db.orders.aggregate(pipeline).to_list(None)

    # Build a lookup: product_id → (total_sold, days_with_sales)
    stats_map = {r["_id"]: (r["total_sold"], r["days_with_sales"]) for r in sales_stats}

    # Get all seller products and check for shortages
    products = await db.products.find({"seller_username": uname}).to_list(None)
    alerts = []
    for product in products:
        pid = str(product["_id"])
        total_sold, days_with_sales = stats_map.get(pid, (0, 0))

        # Average daily demand (fallback to 0 if no sales history)
        if days_with_sales > 0:
            avg_daily = total_sold / days_with_sales
        else:
            avg_daily = 0

        # Project 30-day demand
        projected_demand_30d = round(avg_daily * 30)
        current_stock = product["quantity"]

        if projected_demand_30d > current_stock and avg_daily > 0:
            alerts.append({
                "product_id": pid,
                "product_name": product["name"],
                "current_stock": current_stock,
                "forecasted_demand_30d": projected_demand_30d,
                "shortage_units": max(0, projected_demand_30d - current_stock),
                "avg_daily_sales": round(avg_daily, 2),
                "total_sold": total_sold,
                "days_with_sales": days_with_sales,
            })

    # Sort by shortage severity (most urgent first)
    alerts.sort(key=lambda a: a["shortage_units"], reverse=True)

    return {"alerts": alerts, "count": len(alerts)}


# ── Seller's Own Products ──────────────────────────────────────────────────────

@router.get("/products")
async def my_products(current_user: dict = Depends(seller_only)):
    db = get_db()
    products = await db.products.find(
        {"seller_username": current_user["username"]}
    ).to_list(None)
    return [_serialize(p) for p in products]


# ── Profile ────────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(current_user: dict = Depends(seller_only)):
    db = get_db()
    user = await db.users.find_one({"username": current_user["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    return _serialize(user)


@router.put("/profile")
async def update_profile(updates: dict, current_user: dict = Depends(seller_only)):
    allowed = {"name", "mobile", "address", "city", "email"}
    update_data = {k: v for k, v in updates.items() if k in allowed}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    db = get_db()
    await db.users.update_one(
        {"username": current_user["username"]}, {"$set": update_data}
    )
    return {"message": "Profile updated"}
