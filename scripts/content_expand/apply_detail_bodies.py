#!/usr/bin/env python3
"""将 detail_bodies.py 中的详细正文写回 content_items（按板块 + 标题匹配）。

用法：
  python scripts/content_expand/apply_detail_bodies.py --dry-run
  python scripts/content_expand/apply_detail_bodies.py
"""

import argparse
import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from detail_bodies import BODIES  # noqa: E402

load_dotenv(BASE_DIR.parent.parent / "backend" / ".env")

DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root1234"),
    "database": os.getenv("MYSQL_DATABASE", "tea_guide"),
    "charset": "utf8mb4",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只检查匹配情况，不写库")
    args = parser.parse_args()

    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT id, code FROM content_types")
    type_ids = {code: tid for tid, code in cur.fetchall()}

    total = 0
    missing: list[str] = []
    for code, items in BODIES.items():
        type_id = type_ids.get(code)
        if type_id is None:
            missing.append(f"未知板块 {code}")
            continue
        for title, body in items.items():
            cur.execute(
                "UPDATE content_items SET body=%s, updated_at=UTC_TIMESTAMP() "
                "WHERE type_id=%s AND title=%s",
                (body, type_id, title),
            )
            if cur.rowcount == 0:
                missing.append(f"{code}: {title}")
            total += cur.rowcount

    if args.dry_run:
        conn.rollback()
        print(f"dry-run：匹配 {total} 条，未匹配 {len(missing)} 条")
    else:
        conn.commit()
        print(f"更新 {total} 条，未匹配 {len(missing)} 条")

    for line in missing:
        print("  未匹配 " + line)
    conn.close()
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
