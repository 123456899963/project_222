#!/usr/bin/env python3
"""
茶品批量入库脚本

- 读取本目录数据文件（data_*.py）
- 跳过已存在茶名，按字段入库
- 更新 main_image_url（若图片已下载）
- 自动补 price_min / price_max（根据品类默认值）
- 事务提交，失败回滚
"""

import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from __init__ import ALL_TEAS

load_dotenv(BASE_DIR.parent.parent / "backend" / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root1234")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "tea_guide")

# 品类默认价格区间（元/斤），用于回填 price_min/max
PRICE_RANGES = {
    "green": (200, 1500),
    "red": (300, 2000),
    "oolong": (400, 3000),
    "dark": (200, 2500),
    "white": (300, 2000),
    "yellow": (200, 1200),
    "reprocessed": (150, 1000),
}


def import_teas():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
    )
    cur = conn.cursor()

    cur.execute("SELECT name FROM teas")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    skipped = 0
    for tea in ALL_TEAS:
        name = tea["name"]
        if name in existing:
            skipped += 1
            continue

        price_min, price_max = PRICE_RANGES.get(tea["category"], (200, 1500))
        # 收藏数只能由 favorite_items 推导，导入脚本不得伪造热度（演示种子见 init.sql 注释）
        fav_count = 0

        sql = """
            INSERT INTO teas
              (name, category, origin, season, fermentation,
               price_range, price_min, price_max, representative_variety,
               shape_desc, soup_desc, aroma_desc, taste_desc,
               water_temp, tea_amount, brew_time,
               main_image_url, is_active, favorite_count)
            VALUES (%s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s)
        """
        cur.execute(
            sql,
            (
                name,
                tea["category"],
                tea["origin"],
                tea["season"],
                tea["fermentation"],
                tea.get("price_range"),
                price_min,
                price_max,
                tea.get("representative_variety"),
                tea["shape_desc"],
                tea["soup_desc"],
                tea["aroma_desc"],
                tea["taste_desc"],
                tea["water_temp"],
                tea["tea_amount"],
                tea["brew_time"],
                tea.get("main_image_url"),
                1,
                fav_count,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"导入完成：新增 {inserted} 款，跳过（已存在）{skipped} 款")


if __name__ == "__main__":
    import_teas()
