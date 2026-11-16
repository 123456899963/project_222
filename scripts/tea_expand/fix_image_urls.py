#!/usr/bin/env python3
"""为已入库茶品回填 main_image_url（根据下载文件名规则）"""

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from __init__ import ALL_TEAS
from download_images import safe_filename

load_dotenv(BASE_DIR.parent.parent / "backend" / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root1234")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "tea_guide")

UPLOAD_DIR = BASE_DIR.parent.parent / "backend" / "uploads" / "2026" / "11"


def main():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
    )
    cur = conn.cursor()

    updated = 0
    missing = 0
    for tea in ALL_TEAS:
        name = tea["name"]
        filename = f"{safe_filename(name)}.jpg"
        filepath = UPLOAD_DIR / filename
        if filepath.exists():
            url = f"/uploads/2026/11/{filename}"
            cur.execute("UPDATE teas SET main_image_url = %s WHERE name = %s", (url, name))
            updated += 1
        else:
            missing += 1
            print(f"missing: {name}")

    conn.commit()
    conn.close()
    print(f"updated: {updated}, missing: {missing}")


if __name__ == "__main__":
    main()
