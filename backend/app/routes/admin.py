import logging

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from pymongo.errors import PyMongoError
from typing import List, Optional

from ..core.database import get_db, ping_database
from ..core.security import require_role
from ..models.user import SellerApproval

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_only = require_role("admin")
logger = logging.getLogger(__name__)


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc.pop("password", None)
    return doc


# ── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get("/health/database")
async def database_health(_=Depends(admin_only)):
    try:
        await ping_database()
    except RuntimeError as exc:
        logger.error("MongoDB health check could not run: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_type": type(exc).__name__,
                "message": "MongoDB client is not initialized. Check backend startup.",
            },
        ) from exc
    except PyMongoError as exc:
        logger.exception("MongoDB health check failed")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error_type": type(exc).__name__,
                "message": (
                    "MongoDB ping failed. Check the backend MONGO_URL, "
                    "database credentials, and Atlas Network Access."
                ),
            },
        ) from exc

    return {"status": "ok", "database": "connected"}


@router.get("/stats")
async def get_stats(_=Depends(admin_only)):
    db = get_db()
    total_customers = await db.users.count_documents({"role": "customer"})
    total_sellers = await db.users.count_documents({"role": "seller"})
    pending_sellers = await db.users.count_documents({"role": "seller", "is_approved": False})
    total_products = await db.products.count_documents({})
    total_orders = await db.orders.count_documents({})
    total_revenue_pipeline = [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}},
    ]
    revenue_result = await db.orders.aggregate(total_revenue_pipeline).to_list(1)
    total_revenue = revenue_result[0]["total"] if revenue_result else 0.0

    return {
        "total_customers": total_customers,
        "total_sellers": total_sellers,
        "pending_sellers": pending_sellers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
    }


# ── Seller Management ─────────────────────────────────────────────────────────

def _seller_status(doc: dict) -> str:
    """pending | approved | rejected (older documents only have is_approved)."""
    if doc.get("approval_status"):
        return doc["approval_status"]
    return "approved" if doc.get("is_approved") else "pending"


@router.get("/sellers")
async def list_sellers(status: Optional[str] = None, approved: Optional[bool] = None, _=Depends(admin_only)):
    db = get_db()
    query = {"role": "seller"}
    if status == "approved" or approved is True:
        query["is_approved"] = True
    elif status == "rejected":
        query["approval_status"] = "rejected"
    elif status == "pending":
        query["is_approved"] = False
        query["approval_status"] = {"$ne": "rejected"}
    elif approved is False:
        query["is_approved"] = False
    sellers = await db.users.find(query).to_list(None)
    return [{**_serialize(s), "approval_status": _seller_status(s)} for s in sellers]


@router.patch("/sellers/approve")
async def approve_seller(body: SellerApproval, _=Depends(admin_only)):
    db = get_db()
    result = await db.users.update_one(
        {"username": body.username, "role": "seller"},
        {"$set": {
            "is_approved": body.approved,
            "is_active": body.approved,
            "approval_status": "approved" if body.approved else "rejected",
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Seller not found")
    action = "approved" if body.approved else "rejected"
    return {"message": f"Seller {body.username} has been {action}"}


# ── Customer Management ───────────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(_=Depends(admin_only)):
    db = get_db()
    customers = await db.users.find({"role": "customer"}).to_list(None)
    return [_serialize(c) for c in customers]


@router.patch("/users/{username}/toggle-active")
async def toggle_user_active(username: str, _=Depends(admin_only)):
    db = get_db()
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_status = not user.get("is_active", True)
    await db.users.update_one({"username": username}, {"$set": {"is_active": new_status}})
    return {"message": f"User {username} is now {'active' if new_status else 'deactivated'}"}


# ── Product Management ────────────────────────────────────────────────────────

@router.get("/products")
async def list_all_products(_=Depends(admin_only)):
    db = get_db()
    products = await db.products.find({}).to_list(None)
    return [_serialize(p) for p in products]


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, _=Depends(admin_only)):
    db = get_db()
    result = await db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


# ── Category Management ────────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(_=Depends(admin_only)):
    db = get_db()
    cats = await db.categories.find({}).to_list(None)
    return [_serialize(c) for c in cats]


@router.post("/categories", status_code=201)
async def add_category(name: str, _=Depends(admin_only)):
    db = get_db()
    existing = await db.categories.find_one({"name": name})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    await db.categories.insert_one({"name": name, "created_at": datetime.utcnow()})
    return {"message": f"Category '{name}' created"}


@router.delete("/categories/{name}")
async def delete_category(name: str, _=Depends(admin_only)):
    db = get_db()
    result = await db.categories.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": f"Category '{name}' deleted"}


# ── Order Overview ─────────────────────────────────────────────────────────────

@router.get("/orders")
async def list_all_orders(_=Depends(admin_only)):
    db = get_db()
    orders = await db.orders.find({}).sort("created_at", -1).to_list(200)
    return [_serialize(o) for o in orders]


# ── ML Training Trigger ────────────────────────────────────────────────────────

@router.post("/ml/train")
async def trigger_ml_training(_=Depends(admin_only)):
    """
    Train the recommendation Decision Tree model.
    Returns a Server-Sent Events (SSE) stream so the UI shows a progress bar.
    """
    import asyncio
    import json
    from fastapi.responses import StreamingResponse
    from ..services.recommendation_service import train_model

    db = get_db()

    def _sse(msg: str, pct: int, done: bool = False, error: bool = False, result: dict = None) -> str:
        """Format one SSE event frame (sync — no await needed)."""
        payload = json.dumps(
            {"message": msg, "progress": pct, "done": done, "error": error, "result": result}
        )
        # Two trailing newlines terminate the event; leading newline separates events
        return f"data: {payload}\n\n"

    async def event_stream():
        try:
            # Each step: yield the event FIRST (so it flushes), then do the work,
            # then yield the result.  asyncio.sleep(0.05) gives the ASGI transport
            # time to flush the frame before the next blocking operation.

            # ── 1. Categories ──────────────────────────────────────────────────
            yield _sse("Fetching categories…", 5)
            await asyncio.sleep(0.05)
            categories = await db.categories.distinct("name")

            # ── 2. Bulk product → category map ─────────────────────────────────
            yield _sse("Loading product catalogue…", 10)
            await asyncio.sleep(0.05)
            product_cat_map: dict[str, str] = {}
            async for p in db.products.find({}, {"_id": 1, "category": 1}):
                product_cat_map[str(p["_id"])] = p.get("category", "")
            yield _sse(f"Loaded {len(product_cat_map):,} products.", 20)
            await asyncio.sleep(0.05)

            # ── 3. Orders ──────────────────────────────────────────────────────
            yield _sse("Loading order history…", 25)
            await asyncio.sleep(0.05)
            orders = await db.orders.find(
                {"status": {"$ne": "cancelled"}},
                {"customer_username": 1, "created_at": 1, "items.product_id": 1, "items.quantity": 1},
            ).to_list(None)
            yield _sse(f"Loaded {len(orders):,} orders.", 35)
            await asyncio.sleep(0.05)

            # ── 4. Time-ordered training samples ───────────────────────────────
            from ..services.recommendation_service import build_training_samples
            yield _sse("Building time-ordered training samples (history, cart context, recency)…", 45)
            await asyncio.sleep(0.05)
            training_data = build_training_samples(orders, product_cat_map)
            yield _sse(f"Built {len(training_data):,} samples from {len(orders):,} orders.", 70)
            await asyncio.sleep(0.05)

            # ── 5. Tune, benchmark and save (CPU-bound, runs in a worker thread) ─
            yield _sse("Splitting by time and starting model search…", 75)
            await asyncio.sleep(0.1)
            loop = asyncio.get_event_loop()
            updates: list = []
            future = loop.run_in_executor(
                None, lambda: train_model(training_data, categories, lambda pct, msg: updates.append((pct, msg)))
            )
            while not future.done():
                while updates:
                    pct, msg = updates.pop(0)
                    yield _sse(msg, pct)
                await asyncio.sleep(0.25)
            while updates:
                pct, msg = updates.pop(0)
                yield _sse(msg, pct)
            result = await future

            # ── 6. Done ────────────────────────────────────────────────────────
            st = result.get("status", "unknown")
            n = result.get("samples", 0)
            if st == "trained":
                msg = (f"Done - {n:,} samples | top-1 {result['top1']:.1%} | top-3 {result['top3']:.1%} "
                       f"| macro-F1 {result['macro_f1']:.2f}")
                yield _sse(msg, 100, done=True, result=result)
            elif st == "insufficient_data":
                yield _sse(f"Not enough data ({n} samples, need at least 30).", 100, done=True)
            elif st == "insufficient_classes":
                yield _sse("Need at least 2 categories in the training data.", 100, done=True)
            else:
                yield _sse(f"Finished: {st}", 100, done=True)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield _sse(f"Error: {exc}", 0, done=True, error=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


@router.post("/ml/arima")
async def run_arima_pipeline(product_id: Optional[str] = None, _=Depends(admin_only)):
    """
    Walk the ARIMA forecasting pipeline stage by stage on one product and stream
    each stage (with the data it produced) as Server-Sent Events, so the UI can
    draw a chart for the current stage.
    """
    import asyncio
    import json
    import numpy as np
    from fastapi.responses import StreamingResponse
    from ..services import arima_service as az

    db = get_db()

    def _sse(stage: str, msg: str, pct: int, chart: dict = None, done: bool = False,
             error: bool = False, info: dict = None) -> str:
        payload = json.dumps({"stage": stage, "message": msg, "progress": pct, "chart": chart,
                              "done": done, "error": error, "info": info})
        return f"data: {payload}\n\n"

    def _pts(index, values):
        return [{"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 3)} for d, v in zip(index, values)]

    async def event_stream():
        try:
            loop = asyncio.get_event_loop()

            # 1. Pick a product and load its demand history
            yield _sse("load", "Loading order history…", 5)
            await asyncio.sleep(0.05)
            pid = product_id
            if not pid:
                top = await db.orders.aggregate([
                    {"$match": {"status": {"$ne": "cancelled"}}},
                    {"$unwind": "$items"},
                    {"$group": {"_id": "$items.product_id", "n": {"$sum": 1}}},
                    {"$sort": {"n": -1}}, {"$limit": 1},
                ]).to_list(1)
                if not top:
                    yield _sse("load", "No orders found to forecast from.", 100, done=True, error=True)
                    return
                pid = top[0]["_id"]
            try:
                product = await db.products.find_one({"_id": ObjectId(pid)})
            except Exception:
                product = None
            if not product:
                yield _sse("load", "Product not found.", 100, done=True, error=True)
                return
            rows = await db.orders.aggregate([
                {"$match": {"items.product_id": pid, "status": {"$ne": "cancelled"}}},
                {"$unwind": "$items"}, {"$match": {"items.product_id": pid}},
                {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                            "q": {"$sum": "$items.quantity"}}},
                {"$sort": {"_id": 1}},
            ]).to_list(None)
            if len(rows) < az.MIN_ORDER_DAYS:
                yield _sse("load", f"Only {len(rows)} order days for this product - need at least {az.MIN_ORDER_DAYS}.",
                           100, done=True, error=True)
                return
            s = az.weekly_series([{"date": r["_id"], "quantity": r["q"]} for r in rows])
            info = {"product_name": product["name"], "current_stock": product["quantity"]}
            yield _sse("load", f"Loaded {len(rows)} order days for '{product['name']}' (weekly series, {len(s)} points).",
                       20, chart={"kind": "history", "history": _pts(s.index, s.values)}, info=info)
            await asyncio.sleep(1.2)

            # 2. Stationarity: choose d
            yield _sse("stationarity", "Testing stationarity (ADF) to choose d…", 28)
            await asyncio.sleep(0.05)
            d, pvals = az.choose_d(s)
            diff = s.diff(d).dropna() if d > 0 else s
            msg = (f"ADF p-value {pvals[0]:.3f} on the raw series" +
                   (f"; {pvals[d]:.4f} after differencing {d}x - using d = {d}." if d > 0 else " - already stationary, d = 0."))
            yield _sse("stationarity", msg, 40,
                       chart={"kind": "stationarity", "history": _pts(s.index, s.values),
                              "differenced": _pts(diff.index, diff.values)},
                       info={**info, "d": d, "adf_p_raw": round(pvals[0], 4), "adf_p_diff": round(pvals[min(d, len(pvals) - 1)], 4)})
            await asyncio.sleep(1.2)

            # 3. Order search (p, q) by AICc
            yield _sse("fit", f"Searching p,q for d = {d} (9 candidate models, lowest AICc wins)…", 48)
            await asyncio.sleep(0.05)
            fit, order, cands = await loop.run_in_executor(None, lambda: az.select_order(s, d))
            fitted = np.asarray(fit.fittedvalues, dtype=float).copy()
            fitted[0] = s.values[0]
            order = tuple(order)
            info = {**info, "order": list(order), "aic": round(float(fit.aic), 1), "candidates": cands[:5]}
            yield _sse("fit", f"Best model ARIMA{order} (AICc {cands[0]['aicc'] if cands else '-'}) out of {len(cands)} fitted.", 60,
                       chart={"kind": "fit", "history": _pts(s.index, s.values),
                              "fitted": _pts(s.index, np.maximum(fitted, 0))}, info=info)
            await asyncio.sleep(1.2)

            # 4. Back-test on the most recent weeks
            yield _sse("validate", "Back-testing on the most recent weeks…", 68)
            await asyncio.sleep(0.05)
            bt = await loop.run_in_executor(None, az.backtest, s)
            if bt:
                a, m = bt["arima"], bt["naive_mean"]
                verdict = "ARIMA beats the mean baseline" if bt["chosen"] == "arima" else "mean baseline is better, so the forecast will use it"
                tdates = [x["date"] for x in bt["train_tail"]]
                chart = {"kind": "validate", "history": bt["train_tail"],
                         "actual": [{"date": dt, "value": v} for dt, v in zip(bt["dates"], bt["actual"])],
                         "predicted": [{"date": dt, "value": v} for dt, v in zip(bt["dates"], bt["predicted"])]}
                yield _sse("validate", f"Hold-out {bt['horizon_weeks']} weeks: ARIMA MAE {a['mae']} vs mean {m['mae']} - {verdict}.", 80,
                           chart=chart, info={**info, "backtest": {k: bt[k] for k in ("horizon_weeks", "arima", "naive_mean", "naive_last", "chosen")}})
            else:
                yield _sse("validate", "Not enough history for a back-test; using ARIMA directly.", 80, chart=None, info=info)
            await asyncio.sleep(1.2)

            # 5. Forecast with a 95% interval
            yield _sse("forecast", "Forecasting the next 30 days…", 90)
            await asyncio.sleep(0.05)
            weeks = 5
            use_arima = bt is None or bt["chosen"] == "arima"
            res = fit.get_forecast(steps=weeks)
            fc = np.maximum(np.asarray(res.predicted_mean, dtype=float), 0)
            ci = np.asarray(res.conf_int(alpha=0.05), dtype=float)
            lo, hi = np.maximum(ci[:, 0], 0), np.maximum(ci[:, 1], fc)
            method = "arima"
            if not use_arima:
                base = float(s.iloc[-8:].mean()); sd = float(s.iloc[-26:].std() or 0)
                fc = np.full(weeks, base); lo = np.maximum(fc - 1.96 * sd, 0); hi = fc + 1.96 * sd
                method = "naive_mean"
            fidx = s.index[-1] + np.arange(1, weeks + 1) * np.timedelta64(7, "D")
            import pandas as pd
            fidx = pd.DatetimeIndex(fidx)
            total = float(fc.sum())
            tail = s.iloc[-26:]
            chart = {"kind": "forecast", "history": _pts(tail.index, tail.values),
                     "forecast": [{"date": dd.strftime("%Y-%m-%d"), "value": round(float(v), 3),
                                   "low": round(float(a), 3), "high": round(float(b), 3)}
                                  for dd, v, a, b in zip(fidx, fc, lo, hi)]}
            short = total > product["quantity"]
            yield _sse("forecast",
                       f"{'ARIMA' if method == 'arima' else 'Mean baseline'} forecast: ~{total:.0f} units in 30 days vs {product['quantity']} in stock"
                       f"{' - shortage predicted' if short else ' - stock is sufficient'}.",
                       100, chart=chart, done=True,
                       info={**info, "method": method, "forecast_total": round(total), "shortage": short})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield _sse("error", f"Error: {exc}", 0, done=True, error=True)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/ml/status")
async def ml_status(_=Depends(admin_only)):
    from ..services.recommendation_service import is_model_trained, get_model_info
    info = get_model_info()
    return {"recommendation_model_trained": info.get("trained", False), **info}
