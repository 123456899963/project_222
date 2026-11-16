#!/usr/bin/env python3
"""
茶品图片下载脚本 v4（个人学习用途）

数据源：百度图片
筛选策略：
  1. 标题必须含"茶"，且命中茶名或茶名核心词
  2. 正向词加分：干茶/茶叶/散茶/茶汤/条索/芽/冲泡
  3. 负向词剔除：茶树/茶树苗/茶园/礼盒/包装/批发/价格/厂家/证书等
  4. 图片质量：宽度>=600、高宽比 0.55~2.2、白底文档剔除
  5. 覆盖写入同名文件，数据库 URL 不变
"""

import hashlib
import html
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR.parent.parent / "backend" / "uploads" / "2026" / "11"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://image.baidu.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

NEG_WORDS = [
    # 植物/产地风光
    "树", "苗", "种植", "园", "采摘", "鲜叶", "茶山", "山场", "海拔", "生态",
    # 包装/电商
    "礼盒", "包装", "盒装", "罐装", "袋装", "盒", "罐", "袋", "瓶", "礼",
    "价格", "批发", "供应", "厂家", "公司", "报价", "元", "网", "旗舰店",
    "淘宝", "京东", "天猫", "加盟", "代理", "店铺", "商品", "购买", "多少钱",
    # 文章/资讯截图
    "功效", "禁忌", "区别", "怎么", "如何", "哪些", "知识", "百科", "知乎",
    "搜狐", "百家号", "小红书", "简书", "图片", "素材", "海报", "图解", "大全",
    "排名", "推荐", "评测", "值得买", "新闻", "资讯", "视频",
    # 其他无关
    "证书", "石材", "招聘", "工厂", "机器", "茶具",
]
POS_WORDS = ["干茶", "散茶", "条索", "茶汤", "汤色", "叶底", "特写", "实拍",
             "冲泡", "茶叶", "成品茶", "毛茶", "高清"]

_print_lock = threading.Lock()


def log(msg: str):
    with _print_lock:
        print(msg, flush=True)


def safe_filename(name: str) -> str:
    h = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    keep = re.sub(r"[^\w一-龥]+", "_", name)
    return f"{keep}_{h}"


def search_baidu(word: str, pages: int = 2) -> list[dict]:
    results: list[dict] = []
    for page in range(pages):
        params = {
            "tn": "resultjson_com", "logid": "123", "ipn": "rj", "ct": "201326592",
            "is": "", "fp": "result", "fr": "", "word": word, "queryWord": word,
            "cl": "2", "lm": "-1", "ie": "utf-8", "oe": "utf-8", "st": "-1",
            "ic": "0", "face": "0", "istype": "2", "nc": "1",
            "pn": str(page * 30), "rn": "30",
        }
        try:
            resp = requests.get("https://image.baidu.com/search/acjson", params=params,
                                headers=HEADERS, timeout=15)
            data = json.loads(resp.text)
        except Exception:
            break
        items = [d for d in data.get("data", []) if d]
        if not items:
            break
        for d in items:
            url = d.get("middleURL") or d.get("thumbURL")
            # 优先取原图高清地址
            for rep in d.get("replaceUrl") or []:
                obj = rep.get("ObjURL") or rep.get("objURL")
                if obj:
                    url = obj
                    break
            if not url:
                continue
            results.append({
                "url": url,
                "title": d.get("fromPageTitleEnc") or "",
                "w": int(d.get("width") or 0),
                "h": int(d.get("height") or 0),
            })
    return results


def score_candidate(name: str, title: str) -> tuple[int, int, int]:
    """候选打分，返回 (相关性, 正向词数, 负向词数)"""
    t = html.unescape(title or "")
    if "茶" not in t and "tea" not in t.lower():
        return 0, 0, 0

    if name in t:
        rel = 3
    else:
        core = name[:-1] if name.endswith("茶") else name
        if len(core) >= 3 and core in t:
            rel = 2
        elif len(core) >= 2 and core in t:
            rel = 1
        else:
            return 0, 0, 0

    pos = sum(1 for w in POS_WORDS if w in t)
    t_clean = t.replace("古树", "")
    neg = sum(1 for w in NEG_WORDS if w in t_clean)
    return rel, pos, neg


def near_white_ratio(img: Image.Image) -> float:
    small = img.convert("RGB").resize((80, 80))
    px = list(small.getdata())
    white = sum(1 for r, g, b in px if r > 240 and g > 240 and b > 240)
    return white / len(px)


def download_and_save(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.content
        if len(data) < 15 * 1024:
            return False

        img = Image.open(BytesIO(data))
        img.load()
        w, h = img.size
        if w < 500 or h < 400:
            return False
        if not 0.5 <= w / h <= 2.4:
            return False

        img = img.convert("RGB")
        if near_white_ratio(img) > 0.7:
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


def process_tea(name: str) -> tuple[str, str]:
    dest = UPLOAD_DIR / f"{safe_filename(name)}.jpg"

    candidates: dict[str, dict] = {}
    queries = [f"{name} 干茶", f"{name} 茶叶", f"{name} 茶汤", f"{name} 条索", name]
    for q in queries:
        for item in search_baidu(q, pages=2):
            rel, pos, neg = score_candidate(name, item["title"])
            if rel == 0:
                continue
            candidates.setdefault(item["url"], {
                **item, "rel": rel, "pos": pos, "neg": neg,
            })

    # 分层尝试：先最像"茶叶实拍"的，再逐步放宽
    tiers = [
        lambda c: c["pos"] > 0 and c["neg"] == 0 and c["rel"] >= 2,
        lambda c: c["pos"] > 0 and c["neg"] == 0,
        lambda c: c["neg"] == 0 and c["rel"] >= 2,
        lambda c: c["neg"] == 0,
    ]
    for tier in tiers:
        pool = [c for c in candidates.values() if tier(c)]
        pool.sort(key=lambda c: (-c["pos"], -c["rel"]))
        for item in pool[:6]:
            if download_and_save(item["url"], dest):
                return "OK", html.unescape(item["title"])[:40]
    return "FAIL", f"{len(candidates)} candidates"


def main():
    sys.path.insert(0, str(BASE_DIR))
    from __init__ import ALL_TEAS

    report = {"success": [], "failed": []}
    total = len(ALL_TEAS)
    done = 0

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(process_tea, tea["name"]): tea["name"] for tea in ALL_TEAS}
        for fut in as_completed(futures):
            name = futures[fut]
            done += 1
            try:
                status, note = fut.result()
            except Exception as exc:
                status, note = "FAIL", str(exc)[:60]
            if status == "OK":
                report["success"].append(name)
                log(f"[{done}/{total}] OK  {name}  <- {note}")
            else:
                report["failed"].append(name)
                log(f"[{done}/{total}] FAIL {name}  {note}")

    report_path = BASE_DIR / "download_report_v4.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n成功 {len(report['success'])}，失败 {len(report['failed'])}")
    if report["failed"]:
        log("失败清单：" + "、".join(report["failed"]))


if __name__ == "__main__":
    main()
