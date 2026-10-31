from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime

from ..core.database import get_db
from ..core.security import require_role
from ..models.cart import CartItemAdd, CartItemUpdate

router = APIRouter(prefix="/cart", tags=["Cart"])
customer_only = require_role("customer")


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("")
async def get_cart(current_user: dict = Depends(customer_only)):
    db = get_db()
    items = await db.cart.find({"customer_username": current_user["username"]}).to_list(None)
    result = []
    for item in items:
        product = await db.products.find_one({"_id": ObjectId(item["product_id"])})
        if not product:
            continue
        result.append({
            "id": str(item["_id"]),
            "product_id": item["product_id"],
            "product_name": product["name"],
            "price": product["price"],
            "quantity": item["quantity"],
            "image_url": product.get("image_url"),
            "seller_username": product["seller_username"],
            "available_quantity": product["quantity"],
            "subtotal": round(product["price"] * item["quantity"], 2),
        })
    total = round(sum(i["subtotal"] for i in result), 2)
    return {"items": result, "total": total, "item_count": len(result)}


@router.post("/add", status_code=201)
async def add_to_cart(body: CartItemAdd, current_user: dict = Depends(customer_only)):
    db = get_db()
    try:
        oid = ObjectId(body.product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")

    product = await db.products.find_one({"_id": oid})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product["quantity"] < body.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product['quantity']} units available",
        )

    # Check if already in cart
    existing = await db.cart.find_one(
        {"customer_username": current_user["username"], "product_id": body.product_id}
    )
    if existing:
        new_qty = existing["quantity"] + body.quantity
        if new_qty > product["quantity"]:
            raise HTTPException(
                status_code=400, detail=f"Cannot add more than {product['quantity']} units"
            )
        await db.cart.update_one(
            {"_id": existing["_id"]}, {"$set": {"quantity": new_qty}}
        )
        return {"message": "Cart updated"}

    # Track user search/browse behavior for recommendations
    await db.user_searches.update_one(
        {"customer_username": current_user["username"], "category": product["category"]},
        {"$inc": {"count": 1}},
        upsert=True,
    )

    await db.cart.insert_one({
        "customer_username": current_user["username"],
        "product_id": body.product_id,
        "quantity": body.quantity,
        "added_at": datetime.utcnow(),
    })
    return {"message": "Item added to cart"}


@router.put("/{item_id}")
async def update_cart_item(
    item_id: str, body: CartItemUpdate, current_user: dict = Depends(customer_only)
):
    db = get_db()
    cart_item = await db.cart.find_one(
        {"_id": ObjectId(item_id), "customer_username": current_user["username"]}
    )
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = await db.products.find_one({"_id": ObjectId(cart_item["product_id"])})
    if product and body.quantity > product["quantity"]:
        raise HTTPException(
            status_code=400, detail=f"Only {product['quantity']} units available"
        )

    await db.cart.update_one({"_id": ObjectId(item_id)}, {"$set": {"quantity": body.quantity}})
    return {"message": "Cart updated"}


@router.delete("/{item_id}")
async def remove_from_cart(item_id: str, current_user: dict = Depends(customer_only)):
    db = get_db()
    result = await db.cart.delete_one(
        {"_id": ObjectId(item_id), "customer_username": current_user["username"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return {"message": "Item removed"}


@router.delete("")
async def clear_cart(current_user: dict = Depends(customer_only)):
    db = get_db()
    await db.cart.delete_many({"customer_username": current_user["username"]})
    return {"message": "Cart cleared"}
