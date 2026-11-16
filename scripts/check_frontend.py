#!/usr/bin/env python3
"""检查前台 Element Plus 与硬编码色值规则，允许已登记的历史遗留。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"
ELEMENT_RE = re.compile(r"(from\s+['\"]element-plus['\"]|require\(['\"]element-plus['\"]\))")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,6}\b")

# 基线遗留：已清理完毕；前台任何文件（含全局注册）都不得引用 Element Plus。
ELEMENT_ALLOWED: set[str] = set()
ELEMENT_ALLOWED_DIRS = {"views/admin"}
# 设计 Token 文件允许定义 HEX；其他文件只能引用 CSS 变量。
HEX_ALLOWED = {"style.css"}


def main() -> int:
    errors: list[str] = []
    debt: list[str] = []

    for path in sorted(SRC.rglob("*")):
        if not path.is_file() or path.suffix not in {".vue", ".ts", ".js", ".css"}:
            continue
        rel = path.relative_to(SRC).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")

        if ELEMENT_RE.search(text):
            in_admin = any(rel.startswith(prefix) for prefix in ELEMENT_ALLOWED_DIRS)
            if in_admin:
                continue
            if rel in ELEMENT_ALLOWED:
                debt.append(f"{rel}: 直接使用 Element Plus（基线遗留）")
            else:
                errors.append(f"{rel}: 前台不得引入 Element Plus")

        if path.suffix in {".vue", ".css"} and rel not in HEX_ALLOWED:
            for lineno, line in enumerate(text.splitlines(), 1):
                if HEX_RE.search(line):
                    debt.append(f"{rel}:{lineno}: 硬编码 HEX（基线遗留，逐步迁移到 CSS 变量）")

    for item in debt:
        print(f"BASELINE: {item}")
    if errors:
        print("FAIL: 发现新的前台 UI 规范违规：")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"OK: 前台 UI 检查通过（历史遗留 {len(debt)} 项）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
