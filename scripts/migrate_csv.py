"""
Script one-shot : importe history.csv dans la table SQLite `history`.

Usage :
    python scripts/migrate_csv.py [--csv PATH] [--db PATH] [--force]

Options :
    --csv PATH   Chemin vers history.csv (défaut : history.csv à la racine)
    --db  PATH   Chemin vers la base SQLite (défaut : backend/dl_bot.db)
    --force      Re-importe même si la table n'est pas vide
"""

import argparse
import csv
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path


def migrate(csv_path: Path, db_path: Path, force: bool = False) -> int:
    if not csv_path.exists():
        print(f"[SKIP] {csv_path} introuvable — rien à migrer.")
        return 0

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM history")
    count = cur.fetchone()[0]
    if count > 0 and not force:
        print(f"[SKIP] La table history contient déjà {count} ligne(s). Utilisez --force pour forcer.")
        con.close()
        return 0

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("[SKIP] history.csv est vide.")
        con.close()
        return 0

    now = datetime.now(UTC).isoformat()
    inserted = 0
    for row in rows:
        title = row.get("title", "").strip()
        url = row.get("url", "").strip()
        if not title or not url:
            continue
        cur.execute(
            """
            INSERT OR IGNORE INTO history
                (id, title, source_url, filename, media_type, source, downloaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), title, url, title, "unknown", "wawacity", now),
        )
        inserted += 1

    con.commit()
    con.close()
    print(f"[OK] {inserted} entrée(s) importée(s) depuis {csv_path} → {db_path}")
    return inserted


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="Migre history.csv vers SQLite.")
    parser.add_argument("--csv", type=Path, default=repo_root / "history.csv")
    parser.add_argument("--db", type=Path, default=repo_root / "backend" / "dl_bot.db")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"[ERROR] Base de données introuvable : {args.db}", file=sys.stderr)
        sys.exit(1)

    migrate(args.csv, args.db, force=args.force)


if __name__ == "__main__":
    main()
