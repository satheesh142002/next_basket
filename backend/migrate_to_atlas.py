"""Copy a local MongoDB database to the destination configured in backend/.env."""

import argparse
import sys
from urllib.parse import urlsplit

from pymongo import MongoClient, ReplaceOne
from pymongo.errors import PyMongoError

from app.core.config import get_settings

BATCH_SIZE = 500
LOCAL_URI = "mongodb://localhost:27017"


def _is_local_uri(uri: str) -> bool:
    hostname = urlsplit(uri).hostname
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _copy_collection(source_db, target_db, name: str, dry_run: bool) -> int:
    source = source_db[name]
    target = target_db[name]
    copied = 0

    if not dry_run and name not in target_db.list_collection_names():
        target_db.create_collection(name)

    batch = []
    cursor = source.find({}, no_cursor_timeout=True).batch_size(BATCH_SIZE)
    try:
        for document in cursor:
            batch.append(document)
            if len(batch) == BATCH_SIZE:
                if not dry_run:
                    target.bulk_write(
                        [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in batch],
                        ordered=False,
                    )
                copied += len(batch)
                batch.clear()

        if batch:
            if not dry_run:
                target.bulk_write(
                    [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in batch],
                    ordered=False,
                )
            copied += len(batch)
    finally:
        cursor.close()

    if not dry_run:
        indexes = []
        for index in source.list_indexes():
            spec = dict(index)
            spec.pop("v", None)
            spec.pop("ns", None)
            key = spec.pop("key")
            indexes.append((key, spec))
        for key, options in indexes:
            target.create_index(list(key.items()), **options)

        target_count = target.count_documents({})
        if target_count < copied:
            raise RuntimeError(
                f"Verification failed for '{name}': copied {copied} source documents "
                f"but found only {target_count} documents at the destination."
            )

    return copied


def _copy_views(source_db, target_db, view_names: list[str], dry_run: bool) -> None:
    for view_name in view_names:
        view_info = source_db.command("listCollections", filter={"name": view_name})[
            "cursor"
        ]["firstBatch"][0]
        options = view_info["options"]
        if not dry_run:
            target_db.create_collection(
                view_name,
                viewOn=options["viewOn"],
                pipeline=options["pipeline"],
                **({"collation": options["collation"]} if "collation" in options else {}),
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Copy all collections, documents, indexes, and views from local MongoDB "
            "to MONGO_URL in backend/.env."
        )
    )
    parser.add_argument(
        "--source-uri",
        default=LOCAL_URI,
        help="Local MongoDB connection URI (default: mongodb://localhost:27017).",
    )
    parser.add_argument("--source-db", help="Source database (defaults to DB_NAME in .env).")
    parser.add_argument("--target-db", help="Target database (defaults to DB_NAME in .env).")
    parser.add_argument(
        "--tls-ca-file",
        help="Trusted CA certificate bundle for Atlas TLS when using a custom/private CA.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Allow existing destination collections; matching _id documents will be replaced.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check connections and report source contents without writing to Atlas.",
    )
    args = parser.parse_args()

    settings = get_settings()
    source_name = args.source_db or settings.db_name
    target_name = args.target_db or settings.db_name
    if _is_local_uri(settings.mongo_url):
        print("Refusing to use a local MONGO_URL as the migration destination.", file=sys.stderr)
        return 2

    source_client = MongoClient(args.source_uri, serverSelectionTimeoutMS=10000)
    target_options = {"serverSelectionTimeoutMS": 10000}
    if args.tls_ca_file:
        target_options["tlsCAFile"] = args.tls_ca_file
    target_client = MongoClient(settings.mongo_url, **target_options)
    try:
        source_client.admin.command("ping")
        source_db = source_client[source_name]
        collection_info = list(source_db.list_collections())
        collections = [item["name"] for item in collection_info if item["type"] == "collection"]
        views = [item["name"] for item in collection_info if item["type"] == "view"]
        source_counts = {name: source_db[name].count_documents({}) for name in collections}

        print(
            f"Source database: {source_name} "
            f"({len(collections)} collections, {len(views)} views)"
        )
        for name, count in source_counts.items():
            print(f"  {name}: {count} documents")

        target_client.admin.command("ping")
        target_db = target_client[target_name]
        destination_names = set(target_db.list_collection_names())

        if destination_names and not args.merge:
            print(
                "Destination database is not empty. No data was changed. "
                "Use --merge to upsert source documents by _id.",
                file=sys.stderr,
            )
            return 2

        print(f"Destination database: {target_name}")

        if args.dry_run:
            print("Dry run complete; no destination data was changed.")
            return 0

        for name in collections:
            copied = _copy_collection(source_db, target_db, name, dry_run=False)
            print(f"  Migrated {name}: {copied} documents")

        _copy_views(source_db, target_db, views, dry_run=False)
        print(
            f"Migration complete: {len(collections)} collections and "
            f"{len(views)} views copied to {target_name}."
        )
        return 0
    except PyMongoError as exc:
        print(
            f"MongoDB migration failed ({type(exc).__name__}). Check the Atlas URI, "
            "database-user credentials, Network Access allowlist, and cluster availability.",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as exc:
        print(f"Migration stopped: {exc}", file=sys.stderr)
        return 1
    finally:
        source_client.close()
        target_client.close()


if __name__ == "__main__":
    raise SystemExit(main())
