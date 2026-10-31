"""Restore one mongodump database to the Atlas URI configured in backend/.env."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import get_settings


def _is_local_uri(uri: str) -> bool:
    return urlsplit(uri).hostname in {"localhost", "127.0.0.1", "::1"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore a mongodump database to MONGO_URL in backend/.env."
    )
    parser.add_argument(
        "--dump-dir",
        required=True,
        type=Path,
        help="mongodump root directory containing a subdirectory named for the database.",
    )
    parser.add_argument(
        "--database",
        help="Database directory and target database (defaults to DB_NAME in .env).",
    )
    parser.add_argument(
        "--tool",
        help="Path to mongorestore executable (defaults to mongorestore on PATH).",
    )
    parser.add_argument(
        "--tls-ca-file",
        type=Path,
        help="Trusted CA bundle for a private TLS inspection CA; verification remains enabled.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ask mongorestore to validate and summarize without importing documents.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the restore. Requires --confirm-database to match the target database.",
    )
    parser.add_argument(
        "--confirm-database",
        help="Confirmation safeguard for --apply; must exactly match the target database.",
    )
    args = parser.parse_args()

    settings = get_settings()
    database = args.database or settings.db_name
    dump_dir = args.dump_dir.expanduser().resolve()
    db_dump = dump_dir / database
    if not db_dump.is_dir():
        print(
            f"Backup database folder not found: {db_dump}",
            file=sys.stderr,
        )
        return 2
    if _is_local_uri(settings.mongo_url):
        print("Refusing to restore to a local MONGO_URL.", file=sys.stderr)
        return 2
    if args.apply and args.dry_run:
        print("Choose either --dry-run or --apply, not both.", file=sys.stderr)
        return 2
    if args.apply and args.confirm_database != database:
        print(
            f"To restore, pass --confirm-database {database}.",
            file=sys.stderr,
        )
        return 2
    if not args.apply and not args.dry_run:
        print("Use --dry-run to validate or --apply to import the backup.", file=sys.stderr)
        return 2

    tool = args.tool or shutil.which("mongorestore")
    if not tool:
        print(
            "mongorestore was not found. Pass its path using --tool.",
            file=sys.stderr,
        )
        return 2

    config_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".yaml", delete=False
        ) as config:
            config_path = Path(config.name)
            config.write("uri: " + json.dumps(settings.mongo_url) + "\n")

        command = [
            str(tool),
            "--config",
            str(config_path),
            f"--nsInclude={database}.*",
            f"--dir={dump_dir}",
        ]
        if args.tls_ca_file:
            command.append(f"--sslCAFile={args.tls_ca_file.expanduser().resolve()}")
        if args.dry_run:
            command.append("--dryRun")

        if args.dry_run:
            print(f"Validating backup restore for database '{database}' (no data will be written).")
        else:
            print(f"Restoring backup into database '{database}'. No collections will be dropped.")
        result = subprocess.run(command, check=False)
        return result.returncode
    except OSError as exc:
        print(f"Could not run mongorestore: {exc}", file=sys.stderr)
        return 1
    finally:
        if config_path and config_path.exists():
            config_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
