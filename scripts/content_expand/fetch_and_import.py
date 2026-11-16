#!/usr/bin/env python3
"""
内容板块扩充：图片下载 + 入库（个人学习用途）

用法：
  python scripts/content_expand/fetch_and_import.py --type teaware --limit 3   # 小样本试跑
  python scripts/content_expand/fetch_and_import.py                            # 全量
  python scripts/content_expand/fetch_and_import.py --skip-images              # 只入库

图片来自百度图片，按条目关键词筛选；品牌板块只用品类/产地示意，不用商标与店面。
"""

import argparse
import hashlib
import html
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import pymysql
import requests
from dotenv import load_dotenv
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent / "tea_expand"))

from __init__ import TYPE_ITEMS  # noqa: E402
from detail_bodies import BODIES as DETAIL_BODIES  # noqa: E402
from tea_expand.download_images import HEADERS, search_baidu  # noqa: E402

load_dotenv(BASE_DIR.parent.parent / "backend" / ".env")

UPLOAD_DIR = BASE_DIR.parent.parent / "backend" / "uploads" / "2026" / "11"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root1234"),
    "database": os.getenv("MYSQL_DATABASE", "tea_guide"),
    "charset": "utf8mb4",
}

COMMON_NEG = [
    "价格", "批发", "供应", "厂家", "报价", "多少钱", "淘宝", "京东", "天猫",
    "旗舰店", "加盟", "代理", "招聘", "广告", "海报", "素材", "视频", "网店",
    "商品", "购买", "优惠", "券", "直播",
]

CONFIG = {
    "teaware": {
        "pos": ["茶具", "茶器", "茶杯", "茶壶", "茶盘", "盖碗", "茶席", "实拍"],
        "neg": COMMON_NEG + ["礼盒", "包装", "套装", "logo", "商标", "门店"],
        "white": 0.65,
    },
    "origin": {
        "pos": ["茶园", "茶山", "风景", "风光", "云雾", "梯田", "山", "古镇"],
        "neg": COMMON_NEG + ["茶叶", "干茶", "茶汤", "包装", "礼盒", "logo", "商标"],
        "white": 0.5,
    },
    "culture": {
        "pos": ["茶", "文化", "古籍", "画", "茶馆", "茶道", "民俗"],
        "neg": COMMON_NEG + ["logo", "商标", "门店", "招牌"],
        "white": 0.92,
    },
    "brand": {
        "pos": ["茶", "茶叶", "茶汤", "干茶", "茶饼", "茶具"],
        "neg": COMMON_NEG + ["门店", "店面", "招牌", "logo", "商标", "礼盒", "包装", "加盟"],
        "white": 0.6,
    },
    "knowledge": {
        "pos": ["茶叶", "茶汤", "制茶", "冲泡", "茶园", "茶具", "茶树"],
        "neg": COMMON_NEG + ["logo", "商标", "门店", "招牌"],
        "white": 0.65,
    },
}

_print_lock = threading.Lock()


def log(msg: str):
    with _print_lock:
        print(msg, flush=True)


def image_name(code: str, title: str) -> str:
    return hashlib.md5(f"{code}:{title}".encode("utf-8")).hexdigest()


def near_white_ratio(img: Image.Image) -> float:
    small = img.convert("RGB").resize((80, 80))
    pixels = list(small.getdata())
    white = sum(1 for r, g, b in pixels if r > 240 and g > 240 and b > 240)
    return white / len(pixels)


def download_image(url: str, dest: Path, white_limit: float) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.content
        if len(data) < 15 * 1024:
            return False

        img = Image.open(BytesIO(data))
        img.load()
        w, h = img.size
        if w < 600 or h < 400:
            return False
        if not 0.55 <= w / h <= 2.2:
            return False

        img = img.convert("RGB")
        if near_white_ratio(img) > white_limit:
            return False
        if max(w, h) > 1920:
            scale = 1920 / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        tmp = dest.with_suffix(".tmp")
        img.save(tmp, "JPEG", quality=86, optimize=True)
        tmp.replace(dest)
        return True
    except Exception:
        return False


def score(key: str, title: str, pos_words: list[str], neg_words: list[str]):
    """返回 (相关性, 正向词数, 负向词数)；相关性为 0 表示剔除"""
    t = html.unescape(title or "")
    if not t:
        return 0, 0, 0
    if key and key in t:
        rel = 3
    elif any(p in t for p in pos_words):
        rel = 1
    else:
        return 0, 0, 0
    pos = sum(1 for w in pos_words if w in t)
    t_clean = t.replace("古树", "").replace("老树", "")
    neg = sum(1 for w in neg_words if w in t_clean)
    return rel, pos, neg


def process_item(code: str, item: dict) -> dict:
    dest = UPLOAD_DIR / f"{image_name(code, item['title'])}.jpg"
    if dest.exists():
        return {"ok": True, "cover": f"/uploads/2026/11/{dest.name}", "note": "已存在"}

    conf = CONFIG[code]
    key = item.get("key") or item["title"][:2]
    candidates: dict[str, dict] = {}
    for query in [item["img"], key]:
        for found in search_baidu(query, pages=2):
            rel, pos, neg = score(key, found["title"], conf["pos"], conf["neg"])
            if rel == 0:
                continue
            candidates.setdefault(found["url"], {**found, "rel": rel, "pos": pos, "neg": neg})

    tiers = [
        lambda c: c["rel"] >= 3 and c["neg"] == 0,
        lambda c: c["rel"] >= 3 and c["neg"] <= 1,
        lambda c: c["neg"] == 0,
        lambda c: c["neg"] <= 1,
        lambda c: True,
    ]
    for tier in tiers:
        pool = [c for c in candidates.values() if tier(c)]
        pool.sort(key=lambda c: (-c["rel"], -c["pos"], c["neg"]))
        for cand in pool[:6]:
            if download_image(cand["url"], dest, conf["white"]):
                return {
                    "ok": True,
                    "cover": f"/uploads/2026/11/{dest.name}",
                    "note": html.unescape(cand["title"])[:40],
                }
    return {"ok": False, "cover": None, "note": f"{len(candidates)} candidates"}


def run(items: list[dict], workers: int = 3) -> list[dict]:
    results = [None] * len(items)

    def task(idx: int):
        return idx, process_item(items[idx]["code"], items[idx])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, i) for i in range(len(items))]
        done = 0
        for fut in as_completed(futures):
            idx, res = fut.result()
            results[idx] = res
            done += 1
            status = "OK  " if res["ok"] else "FAIL"
            title = items[idx]["title"]
            log(f"[{done}/{len(items)}] {status} {items[idx]['code']} {title}  {res['note']}")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=list(TYPE_ITEMS), help="只处理某个板块")
    parser.add_argument("--limit", type=int, help="每个板块最多处理多少条（试跑用）")
    parser.add_argument("--skip-images", action="store_true", help="不下载图片，只入库")
    parser.add_argument("--dry-run", action="store_true", help="只下载不写库")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT ct.code, COALESCE(MAX(ci.sort_order), 0) "
        "FROM content_items ci JOIN content_types ct ON ct.id = ci.type_id "
        "GROUP BY ct.code"
    )
    max_sort = {row[0]: row[1] for row in cur.fetchall()}

    cur.execute(
        "SELECT ct.code, ci.title FROM content_items ci "
        "JOIN content_types ct ON ct.id = ci.type_id"
    )
    existing = {(row[0], row[1]) for row in cur.fetchall()}

    codes = [args.type] if args.type else list(TYPE_ITEMS)
    pending = []
    for code in codes:
        items = [dict(it, code=code) for it in TYPE_ITEMS[code]]
        items = [it for it in items if (code, it["title"]) not in existing]
        if args.limit:
            items = items[: args.limit]
        pending.extend(items)

    log(f"待处理 {len(pending)} 条")
    if not pending:
        return

    if args.skip_images:
        results = [{"ok": True, "cover": None, "note": "跳过图片"} for _ in pending]
    else:
        results = run(pending, workers=args.workers)

    if args.dry_run:
        log("dry-run：不写库")
        return

    cur.execute("SELECT id, code FROM content_types")
    type_ids = {row[1]: row[0] for row in cur.fetchall()}

    inserted = 0
    no_image = []
    for item, res in zip(pending, results):
        code = item["code"]
        body = DETAIL_BODIES.get(code, {}).get(item["title"], item["body"])
        max_sort[code] = max_sort.get(code, 0) + 1
        cur.execute(
            """
            INSERT INTO content_items
              (type_id, title, summary, body, cover_image, meta, sort_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            """,
            (
                type_ids[code],
                item["title"],
                item["summary"],
                body,
                res["cover"],
                json.dumps(item["meta"], ensure_ascii=False),
                max_sort[code],
            ),
        )
        inserted += 1
        if not res["cover"]:
            no_image.append(f"{code}: {item['title']}")

    conn.commit()
    conn.close()

    report = {
        "inserted": inserted,
        "image_failed": no_image,
        "items": [
            {"code": it["code"], "title": it["title"], "cover": r["cover"], "note": r["note"]}
            for it, r in zip(pending, results)
        ],
    }
    (BASE_DIR / "content_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log(f"\n入库 {inserted} 条，缺图 {len(no_image)} 条")
    for line in no_image:
        log("  缺图 " + line)


if __name__ == "__main__":
    main()
