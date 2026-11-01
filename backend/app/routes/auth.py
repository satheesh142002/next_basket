from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

from ..core.database import get_db
from ..core.security import hash_password, verify_password, create_access_token, get_settings
from ..models.user import UserCreate, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


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

    # Admin shortcut
    if role not in (None, "admin") and form_data.username == settings.admin_username:
        raise deny
    if (
        role in (None, "admin")
        and form_data.username == settings.admin_username
        and form_data.password == settings.admin_password
    ):
        token = create_access_token({"sub": form_data.username, "role": "admin"})
        return TokenResponse(
            access_token=token,
            role="admin",
            username=form_data.username,
            name="Administrator",
        )

    user = await db.users.find_one({"username": form_data.username})
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
