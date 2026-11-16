#!/usr/bin/env python3
"""生成内容板块配图拼图，用于目检（python scripts/content_expand/make_montage.py --type teaware）"""

import argparse
import sys
from pathlib import Path

import pymysql
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR.parent.parent / "backend"

FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
CELL_W, CELL_H = 240, 190
COLS, ROWS = 6, 5
PER_SHEET = COLS * ROWS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True)
    args = parser.parse_args()

    conn = pymysql.connect(host="localhost", user="root", password="root1234",
                           database="tea_guide", charset="utf8mb4")
    cur = conn.cursor()
    cur.execute(
        "SELECT ci.id, ci.title, ci.cover_image FROM content_items ci "
        "JOIN content_types ct ON ct.id = ci.type_id "
        "WHERE ct.code = %s AND ci.is_active = 1 ORDER BY ci.sort_order",
        (args.type,),
    )
    rows = cur.fetchall()
    conn.close()

    out_dir = BASE_DIR / "montage"
    out_dir.mkdir(exist_ok=True)

    for idx in range(0, len(rows), PER_SHEET):
        chunk = rows[idx: idx + PER_SHEET]
        canvas = Image.new("RGB", (CELL_W * COLS, CELL_H * ROWS), (248, 248, 248))
        draw = ImageDraw.Draw(canvas)
        for i, (item_id, title, cover) in enumerate(chunk):
            r, c = divmod(i, COLS)
            x, y = c * CELL_W, r * CELL_H
            path = UPLOAD_ROOT / cover.lstrip("/") if cover else None
            try:
                img = Image.open(path).convert("RGB")
                img.thumbnail((CELL_W - 8, CELL_H - 26))
                canvas.paste(img, (x + (CELL_W - img.width) // 2, y + 4))
            except Exception:
                draw.rectangle([x + 4, y + 4, x + CELL_W - 4, y + CELL_H - 26],
                               fill=(225, 205, 205))
            draw.text((x + 4, y + CELL_H - 22), f"{item_id} {title[:11]}",
                      fill=(20, 20, 20), font=FONT)
        out = out_dir / f"{args.type}_{idx // PER_SHEET + 1}.jpg"
        canvas.save(out, "JPEG", quality=82)
        print(out, len(chunk))


if __name__ == "__main__":
    main()
