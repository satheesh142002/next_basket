import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from pymongo.errors import PyMongoError

from ..core.database import get_db
from ..core.security import hash_password, verify_password, create_access_token
from ..models.user import UserCreate, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", status_code=201)
async def register(user_in: UserCreate):
    db = get_db()

    # Check duplicates
    existing = await db.users.find_one(
        {"$or": [{"username": user_in.username}, {"email": user_in.email}]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user_doc = {
        "username": user_in.username,
        "name": user_in.name,
        "email": user_in.email,
        "password": hash_password(user_in.password),
        "mobile": user_in.mobile,
        "location": user_in.location,
        "role": user_in.role,
        "is_active": True,
        # seller-specific
        "address": user_in.address,
        "city": user_in.city,
        # sellers need admin approval
        "is_approved": user_in.role == "customer",
        "approval_status": "approved" if user_in.role == "customer" else "pending",
        "created_at": datetime.utcnow(),
    }

    await db.users.insert_one(user_doc)
    return {"message": f"Account created successfully. {'Awaiting admin approval.' if user_in.role == 'seller' else 'You can now log in.'}"}


@router.post("/login", response_model=TokenResponse)
async def login(role: Optional[str] = None, form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    deny = HTTPException(status_code=401, detail="Incorrect username or password")

    try:
        user = await db.users.find_one({"username": form_data.username})
    except PyMongoError as exc:
        logger.error("Login database lookup failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_unavailable",
                "message": "Login is temporarily unavailable because the database cannot be reached.",
            },
        ) from exc

    if not user or not verify_password(form_data.password, user["password"]):
        raise deny
    # A role-specific login page only accepts accounts of that role
    if role is not None and user["role"] != role:
        raise deny

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    if user["role"] == "seller" and not user.get("is_approved", False):
        raise HTTPException(status_code=403, detail="Seller account pending admin approval")

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["username"],
        name=user["name"],
    )
