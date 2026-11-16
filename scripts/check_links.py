#!/usr/bin/env python3
"""校验 Markdown 相对链接是否指向真实文件。CI 与本地均可运行。"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    "node_modules",
    ".git",
    ".git_backup_prd_only",
    ".trae-html-share-packages",
    "dist",
    "coverage",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".venv",
    "venv",
}
LINK_RE = re.compile(r"[!]?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"```.*?```", re.S)


def markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def main() -> int:
    errors: list[str] = []
    checked = 0
    for path in markdown_files():
        text = FENCE_RE.sub("", path.read_text(encoding="utf-8", errors="ignore"))
        for raw in LINK_RE.findall(text):
            target = raw.strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#", "file://")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target or target.startswith("/"):
                continue
            checked += 1
            if not (path.parent / target).resolve().exists():
                errors.append(f"{path.relative_to(ROOT)} -> {raw}")

    if errors:
        print("FAIL: 以下 Markdown 相对链接指向不存在的文件：")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"OK: 已检查 {checked} 条相对链接，全部有效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
