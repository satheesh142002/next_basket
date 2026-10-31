"""
Seed MongoDB with the Sample Superstore dataset on first startup.

Dataset: Sample Superstore Sales (Kaggle)
  - 9,994 sales transactions (2015-2018)
  - 3 categories: Furniture, Office Supplies, Technology
  - 17 sub-categories, ~1,860 unique products
  - ~793 unique customers across 4 US regions

Images: Picsum Photos (https://picsum.photos) — completely free, CC0 licence.
  Deterministic keyword-seeded URLs ensure each sub-category gets consistent
  product images. Format: https://picsum.photos/seed/<keyword>/400/400
"""

import os
import csv
import random
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from bson import ObjectId

from .core.security import hash_password
from .core.database import get_db

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "superstore_sales.csv")

# ── Free Picsum stock images per sub-category ─────────────────────────────────
# Picsum Photos (picsum.photos) — free, open-source, CC0 licence.
# Uses keyword-seeded URLs: https://picsum.photos/seed/<seed>/400/400
# Multiple seeds per sub-category so products in the same sub-category
# get different (but consistent) images.

SUBCATEGORY_SEEDS: dict[str, list[str]] = {
    # Furniture
    "Bookcases":   ["bookcase1","bookshelf","shelf2","library1","bookcase2"],
    "Chairs":      ["officechair","ergonomic","deskchair","seating","chairwork"],
    "Tables":      ["officetable","desk1","conferenceroom","worktable","deskwork"],
    "Furnishings": ["officedecor","furnishing","interiordecor","officespace","workspace1"],
    # Office Supplies
    "Appliances":  ["officeappliance","printer1","scanner1","shreder","officemachine"],
    "Art":         ["artsupplies","colorpencil","markers","sketchbook","paintbrush"],
    "Binders":     ["binder1","ringbinder","officebinder","folderdoc","binderpro"],
    "Envelopes":   ["envelope1","mailing","paperenvelope","officeemail","stationery1"],
    "Fasteners":   ["paperclip","stapler","fastener1","officeclip","bindingclip"],
    "Labels":      ["labelmaker","sticker1","officelabel","adhesive","labelpaper"],
    "Paper":       ["officepaper","printpaper","a4paper","copysheet","paperdoc"],
    "Storage":     ["storagebox","filingcabinet","officebox","archivebox","deskbox"],
    "Supplies":    ["officesupply","stationery2","deskitem","officetool","supplykit"],
    # Technology
    "Accessories": ["techgadget","usbhub","keyboard2","monitor1","cabledesk"],
    "Copiers":     ["lasercopier","officecopy","printcopier","multifunc","docprinter"],
    "Machines":    ["officemachine2","laminator","shredder2","printmachine","techdevice"],
    "Phones":      ["voipphone","conferencephone","deskphone","ipphone","officephone2"],
}

CATEGORY_FALLBACK_SEEDS: dict[str, list[str]] = {
    "Furniture":       ["furniture1","woodfurniture","officefurniture"],
    "Office Supplies": ["officework","officesupply2","deskstuff"],
    "Technology":      ["technology1","techoffice","computergear"],
}

# Description templates per sub-category
SUBCATEGORY_DESCRIPTIONS: dict[str, list[str]] = {
    "Bookcases": [
        "Sturdy wooden bookcase with adjustable shelves for home or office.",
        "Elegant bookcase with ample storage space for books and décor.",
        "Multi-shelf bookcase in contemporary design, easy assembly.",
    ],
    "Chairs": [
        "Ergonomic office chair with lumbar support and adjustable height.",
        "Comfortable padded chair ideal for long working hours.",
        "Modern swivel chair with breathable mesh back.",
    ],
    "Tables": [
        "Spacious office desk with cable management and smooth finish.",
        "Rectangular conference table for professional meeting rooms.",
        "Adjustable-height work table, durable laminate top.",
    ],
    "Furnishings": [
        "Premium office furnishing accessory for a polished workspace.",
        "Decorative office item blending style and functionality.",
        "Compact furnishing piece for home or corporate offices.",
    ],
    "Appliances": [
        "Reliable office appliance for everyday productivity tasks.",
        "Compact, energy-efficient appliance for modern offices.",
        "High-performance appliance with quiet operation.",
    ],
    "Art": [
        "Professional-grade art supply set for creative projects.",
        "High-quality drawing materials for office presentations.",
        "Vibrant markers and pens for whiteboards and documents.",
    ],
    "Binders": [
        "Durable ring binder with clear label holder and strong spine.",
        "Heavy-duty binder for organising important documents.",
        "Colourful binders available in multiple sizes.",
    ],
    "Envelopes": [
        "Self-sealing envelopes for professional correspondence.",
        "Pack of security envelopes with tamper-proof lining.",
        "Padded envelopes for safely mailing documents.",
    ],
    "Fasteners": [
        "Assorted fasteners including binder clips and paper clips.",
        "Heavy-duty staples and binding fasteners set.",
        "Reusable binder clips in a variety of sizes.",
    ],
    "Labels": [
        "Easy-peel adhesive labels for printers and label makers.",
        "Colour-coded filing labels for organised document management.",
        "Durable waterproof labels for storage boxes.",
    ],
    "Paper": [
        "80 gsm multipurpose printer paper, 500-sheet ream.",
        "Bright white copy paper compatible with all laser and inkjet printers.",
        "Recycled office paper, eco-friendly and FSC certified.",
    ],
    "Storage": [
        "Stackable storage box with lid, ideal for archiving documents.",
        "Lateral filing cabinet with smooth-glide drawers.",
        "Desktop document organiser with multiple compartments.",
    ],
    "Supplies": [
        "Essential office supplies bundle for a productive workspace.",
        "Value pack of everyday stationery and desk accessories.",
        "Premium quality office consumables for daily use.",
    ],
    "Accessories": [
        "High-performance USB hub with multiple ports.",
        "Wireless keyboard and mouse combo, ergonomic design.",
        "Monitor stand with storage and cable organiser.",
    ],
    "Copiers": [
        "High-speed laser copier with duplex printing capability.",
        "Multifunction copier, scanner and fax all-in-one.",
        "Compact desktop copier for small to medium offices.",
    ],
    "Machines": [
        "Professional-grade binding machine for office documents.",
        "Electric paper shredder with auto-feed and cross-cut blades.",
        "Heavy-duty laminator for A4/A3 documents.",
    ],
    "Phones": [
        "VoIP conference phone with HD audio and 360° microphone.",
        "IP desk phone with full HD display and Bluetooth.",
        "Wireless DECT office phone with long-range coverage.",
    ],
}


def _get_image_url(sub_category: str, category: str, idx: int) -> str:
    """Return the bundled illustration for the product's sub-category (frontend/public/products)."""
    slug = (sub_category or "").lower().replace(" ", "-")
    return f"/products/{slug}.svg" if slug else "/products/default.svg"


def _get_description(sub_category: str, seed: int) -> str:
    """Pick a deterministic description for a product."""
    pool = SUBCATEGORY_DESCRIPTIONS.get(
        sub_category,
        [f"{sub_category} product for professional use."]
    )
    return pool[seed % len(pool)]

# ── Seller accounts — one per category ───────────────────────────────────────────
SELLER_ACCOUNTS = [
    {
        "username": "furniture_seller",
        "name": "Furniture Hub",
        "email": "furniture@nextbasket.com",
        "password": "seller123",
        "mobile": "1111111111",
        "role": "seller",
        "address": "100 Furniture Ave",
        "city": "New York",
        "location": "New York",
        "category": "Furniture",
    },
    {
        "username": "office_seller",
        "name": "Office Supplies Co",
        "email": "office@nextbasket.com",
        "password": "seller123",
        "mobile": "2222222222",
        "role": "seller",
        "address": "200 Office Blvd",
        "city": "Chicago",
        "location": "Chicago",
        "category": "Office Supplies",
    },
    {
        "username": "tech_seller",
        "name": "Tech World",
        "email": "tech@nextbasket.com",
        "password": "seller123",
        "mobile": "3333333333",
        "role": "seller",
        "address": "300 Tech Park",
        "city": "San Francisco",
        "location": "San Francisco",
        "category": "Technology",
    },
]

# Default password for seeded customers
CUSTOMER_PASSWORD = "customer123"


def _read_csv():
    """Read the Superstore CSV and return list of row dicts."""
    rows = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


async def seed_database():
    """
    Populate MongoDB with the Superstore dataset if the database is empty.
    Creates sellers, products, customers, orders, reviews, and purchase history.
    """
    db = get_db()

    # Only seed if no products exist
    if await db.products.count_documents({}) > 0:
        logger.info("Database already has data — skipping seed")
        return False

    csv_path = DATA_FILE
    if not os.path.exists(csv_path):
        logger.warning(f"Dataset file not found at {csv_path} — skipping seed")
        return False

    logger.info("🌱 Seeding database from Superstore dataset...")
    rows = _read_csv()
    logger.info(f"   Read {len(rows)} rows from CSV")

    # ── Step 1: Update categories to match the dataset ──────────────────────────
    dataset_categories = ["Furniture", "Office Supplies", "Technology"]
    existing_cats = set()
    async for c in db.categories.find({}):
        existing_cats.add(c["name"])
    for cat in dataset_categories:
        if cat not in existing_cats:
            await db.categories.insert_one({"name": cat, "created_at": datetime.utcnow()})
    # Also keep the generic categories for the shop UI

    # ── Step 2: Create seller accounts ──────────────────────────────────────────
    seller_id_map = {}  # category → seller username
    for seller in SELLER_ACCOUNTS:
        existing = await db.users.find_one({"username": seller["username"]})
        if existing:
            seller_id_map[seller["category"]] = seller["username"]
            continue
        doc = {
            "username": seller["username"],
            "name": seller["name"],
            "email": seller["email"],
            "password": hash_password(seller["password"]),
            "mobile": seller["mobile"],
            "role": "seller",
            "is_active": True,
            "is_approved": True,
            "address": seller["address"],
            "city": seller["city"],
            "location": seller["location"],
            "created_at": datetime.utcnow(),
        }
        await db.users.insert_one(doc)
        seller_id_map[seller["category"]] = seller["username"]
    logger.info(f"   Created {len(seller_id_map)} seller accounts")

    # ── Step 3: Create products from unique Product IDs ──────────────────────────
    # Map: product_id_str → MongoDB product doc
    product_map = {}  # CSV Product ID → ObjectId string
    unique_products = {}  # CSV Product ID → row data
    for row in rows:
        pid = row["Product ID"]
        if pid not in unique_products:
            unique_products[pid] = row

    product_docs = []
    sub_cat_counters: dict[str, int] = {}
    for pid, row in unique_products.items():
        category = row["Category"]
        sub_category = row["Sub-Category"]
        seller_username = seller_id_map.get(category, "tech_seller")
        stock = random.randint(5, 100)

        # Round-robin image index per sub-category
        img_idx = sub_cat_counters.get(sub_category, 0)
        sub_cat_counters[sub_category] = img_idx + 1

        doc = {
            "name": row["Product Name"],
            "category": category,
            "sub_category": sub_category,
            "price": round(float(row["Sales"]) / max(int(row["Quantity"]), 1), 2),
            "quantity": stock,
            "description": _get_description(sub_category, img_idx),
            "image_url": _get_image_url(sub_category, category, img_idx),
            "seller_username": seller_username,
            "created_at": datetime.utcnow(),
        }
        product_docs.append(doc)

    if product_docs:
        result = await db.products.insert_many(product_docs)
        for i, pid in enumerate(unique_products.keys()):
            product_map[pid] = str(result.inserted_ids[i])
    logger.info(f"   Created {len(product_map)} products")

    # ── Step 4: Create customer accounts ───────────────────────────────────────
    unique_customers = {}  # Customer ID → row data
    for row in rows:
        cid = row["Customer ID"]
        if cid not in unique_customers:
            unique_customers[cid] = row

    customer_docs = []
    customer_usernames = {}  # Customer ID → username
    for cid, row in unique_customers.items():
        # Create a username from customer name (lowercase, no spaces)
        name_parts = row["Customer Name"].lower().replace("'", "").split()
        username = "_".join(name_parts) + "_" + cid.lower().replace("-", "")
        username = username[:25]  # Keep under 30 chars
        customer_usernames[cid] = username
        doc = {
            "username": username,
            "name": row["Customer Name"],
            "email": f"{username}@nextbasket.com",
            "password": hash_password(CUSTOMER_PASSWORD),
            "mobile": f"{random.randint(100, 999)}{random.randint(100000, 999999)}",
            "role": "customer",
            "is_active": True,
            "is_approved": True,
            "location": f"{row['City']}, {row['State']}",
            "created_at": datetime.utcnow(),
        }
        customer_docs.append(doc)

    if customer_docs:
        await db.users.insert_many(customer_docs)
    logger.info(f"   Created {len(customer_usernames)} customer accounts")

    # ── Step 5: Create orders from transactions ─────────────────────────────────
    # Group rows by Order ID
    orders_by_id = defaultdict(list)
    for row in rows:
        orders_by_id[row["Order ID"]].append(row)

    order_docs = []
    review_docs = []
    purchase_docs = {}  # (customer_username, category) → count

    for order_id, order_rows in orders_by_id.items():
        first_row = order_rows[0]
        customer_username = customer_usernames.get(first_row["Customer ID"])
        if not customer_username:
            continue

        # Parse order date
        try:
            order_date = datetime.strptime(first_row["Order Date"], "%Y-%m-%d")
        except ValueError:
            order_date = datetime.utcnow()

        # Build line items
        items = []
        total_amount = 0.0
        categories_in_order = set()

        for row in order_rows:
            pid = row["Product ID"]
            product_mongo_id = product_map.get(pid)
            if not product_mongo_id:
                continue

            qty = int(row["Quantity"])
            sales = float(row["Sales"])
            unit_price = round(sales / qty, 2) if qty > 0 else 0
            seller_username = seller_id_map.get(row["Category"], "tech_seller")
            category = row["Category"]

            items.append({
                "product_id": product_mongo_id,
                "product_name": row["Product Name"],
                "quantity": qty,
                "price": unit_price,
                "seller_username": seller_username,
            })
            total_amount += unit_price * qty
            categories_in_order.add(category)

            # Track purchases per category for recommendation training
            key = (customer_username, category)
            purchase_docs[key] = purchase_docs.get(key, 0) + qty

        if not items:
            continue

        # Determine order status (most are delivered, some pending/shipped)
        days_old = (datetime.utcnow() - order_date).days
        if days_old > 30:
            status = "delivered"
        elif days_old > 7:
            status = "shipped"
        else:
            status = "confirmed"

        order_docs.append({
            "customer_username": customer_username,
            "items": items,
            "total_amount": round(total_amount, 2),
            "status": status,
            "created_at": order_date,
            "updated_at": order_date,
        })

        # Generate reviews for some orders (30% chance)
        if random.random() < 0.3:
            for row in order_rows[:1]:  # Review first item only
                pid = row["Product ID"]
                product_mongo_id = product_map.get(pid)
                if not product_mongo_id:
                    continue
                # Higher profit → higher rating
                profit = float(row.get("Profit", 0))
                if profit > 50:
                    rating = 5
                elif profit > 10:
                    rating = random.choice([4, 5])
                elif profit > 0:
                    rating = random.choice([3, 4])
                else:
                    rating = random.choice([1, 2, 3])

                review_docs.append({
                    "product_id": product_mongo_id,
                    "customer_username": customer_username,
                    "rating": rating,
                    "comment": random.choice([
                        "Great product, exactly as described!",
                        "Fast delivery, good quality.",
                        "Satisfied with the purchase.",
                        "Works well, would recommend.",
                        "Decent product for the price.",
                        "Could be better but overall okay.",
                        "Excellent value!",
                        "Very happy with this.",
                        None,
                    ]),
                    "created_at": order_date + timedelta(days=random.randint(1, 10)),
                })

    # Insert orders in batches (MongoDB has a 1000-doc insert limit per call)
    batch_size = 1000
    total_orders = 0
    for i in range(0, len(order_docs), batch_size):
        batch = order_docs[i : i + batch_size]
        await db.orders.insert_many(batch)
        total_orders += len(batch)
    logger.info(f"   Created {total_orders} orders")

    # Insert reviews
    if review_docs:
        for i in range(0, len(review_docs), batch_size):
            await db.reviews.insert_many(review_docs[i : i + batch_size])
    logger.info(f"   Created {len(review_docs)} reviews")

    # ── Step 6: Track user purchases per category ─────────────────────────────────
    purchase_tracking_docs = []
    for (username, category), count in purchase_docs.items():
        purchase_tracking_docs.append({
            "customer_username": username,
            "category": category,
            "count": count,
        })
    if purchase_tracking_docs:
        for i in range(0, len(purchase_tracking_docs), batch_size):
            await db.user_purchases.insert_many(purchase_tracking_docs[i : i + batch_size])
    logger.info(f"   Created {len(purchase_tracking_docs)} purchase tracking records")

    # ── Step 7: Auto-train the recommendation model ──────────────────────────────
    try:
        from .services.recommendation_service import train_model

        from .services.recommendation_service import build_training_samples

        # Time-ordered samples from the seeded orders (history, cart context, recency)
        cat_by_pid = {str(d["_id"]): d["category"] async for d in db.products.find({}, {"category": 1})}
        seeded_orders = await db.orders.find(
            {"status": {"$ne": "cancelled"}},
            {"customer_username": 1, "created_at": 1, "items.product_id": 1, "items.quantity": 1},
        ).to_list(None)
        training_data = build_training_samples(seeded_orders, cat_by_pid)
        result = train_model(training_data, list(dataset_categories))
        result = {k: result.get(k) for k in ("status", "top1", "top3", "macro_f1", "samples")}
        logger.info(f"   ML model trained: {result}")
    except Exception as e:
        logger.warning(f"   Could not auto-train ML model: {e}")

    logger.info("✅ Database seeding complete!")
    logger.info(f"   Demo sellers: furniture_seller/seller123, office_seller/seller123, tech_seller/seller123")
    logger.info(f"   Demo customer: any customer / customer123")
    return True
