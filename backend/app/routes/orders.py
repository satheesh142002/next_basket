from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime

from ..core.database import get_db
from ..core.security import require_role, get_current_user
from ..models.order import OrderCreate, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Customer: Place & view orders ─────────────────────────────────────────────

@router.post("", status_code=201)
async def place_order(
    body: OrderCreate,
    current_user: dict = Depends(require_role("customer")),
):
    db = get_db()

    # Validate stock and reserve quantities
    for item in body.items:
        try:
            oid = ObjectId(item.product_id)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.product_id}")

        product = await db.products.find_one({"_id": oid})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        if product["quantity"] < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for '{product['name']}'. Available: {product['quantity']}",
            )

    # Deduct stock and record purchase for recommendations
    for item in body.items:
        oid = ObjectId(item.product_id)
        await db.products.update_one({"_id": oid}, {"$inc": {"quantity": -item.quantity}})

        # Track purchase behavior
        product = await db.products.find_one({"_id": oid})
        if product:
            await db.user_purchases.update_one(
                {
                    "customer_username": current_user["username"],
                    "category": product["category"],
                },
                {"$inc": {"count": item.quantity}},
                upsert=True,
            )

    # Create order
    order_doc = {
        "customer_username": current_user["username"],
        "items": [item.model_dump() for item in body.items],
        "total_amount": body.total_amount,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db.orders.insert_one(order_doc)

    # Clear cart
    await db.cart.delete_many({"customer_username": current_user["username"]})

    return {"order_id": str(result.inserted_id), "message": "Order placed successfully"}


@router.get("/my")
async def get_my_orders(current_user: dict = Depends(require_role("customer"))):
    db = get_db()
    orders = (
        await db.orders.find({"customer_username": current_user["username"]})
        .sort("created_at", -1)
        .to_list(None)
    )
    return [_serialize(o) for o in orders]


# ── Seller: View orders for their products ─────────────────────────────────────

@router.get("/seller")
async def get_seller_orders(current_user: dict = Depends(require_role("seller"))):
    db = get_db()
    # Find orders that contain at least one item from this seller
    orders = (
        await db.orders.find({"items.seller_username": current_user["username"]})
        .sort("created_at", -1)
        .to_list(None)
    )
    # Filter items to only this seller's
    result = []
    for order in orders:
        seller_items = [
            i for i in order["items"] if i["seller_username"] == current_user["username"]
        ]
        order["items"] = seller_items
        result.append(_serialize(order))
    return result


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    body: OrderStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = await db.orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Sellers can only update their own orders
    if current_user["role"] == "seller":
        if not any(
            i["seller_username"] == current_user["username"] for i in order.get("items", [])
        ):
            raise HTTPException(status_code=403, detail="Not your order")

    await db.orders.update_one(
        {"_id": oid},
        {"$set": {"status": body.status, "updated_at": datetime.utcnow()}},
    )
    return {"message": f"Order status updated to '{body.status}'"}
