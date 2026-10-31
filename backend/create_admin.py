import getpass
import sys
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.core.security import hash_password


def main() -> int:
    settings = get_settings()
    username = input("Admin username: ").strip()
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password (minimum 6 characters): ")
    confirmation = getpass.getpass("Confirm admin password: ")

    if not username or not name or not email:
        print("Username, name, and email are required.", file=sys.stderr)
        return 1
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < 6 or len(password.encode("utf-8")) > 72:
        print("Password must be 6-72 UTF-8 bytes.", file=sys.stderr)
        return 1

    client = MongoClient(
        settings.mongo_url,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000,
    )
    try:
        client.admin.command("ping")
        users = client[settings.db_name].users
        users.create_index("username", unique=True)
        users.create_index("email", unique=True)
        existing = users.find_one(
            {"$or": [{"username": username}, {"email": email}]},
            {"username": 1, "email": 1},
        )
        if existing:
            print("An account with that username or email already exists.", file=sys.stderr)
            return 1

        users.insert_one(
            {
                "username": username,
                "name": name,
                "email": email,
                "password": hash_password(password),
                "mobile": "0000000000",
                "role": "admin",
                "is_active": True,
                "is_approved": True,
                "approval_status": "approved",
                "created_at": datetime.utcnow(),
            }
        )
        print(f"Admin account {username!r} created in database {settings.db_name!r}.")
        return 0
    except PyMongoError as exc:
        print(
            f"Admin account creation failed ({type(exc).__name__}). "
            "Check MONGO_URL, DB_NAME, and MongoDB Network Access.",
            file=sys.stderr,
        )
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
