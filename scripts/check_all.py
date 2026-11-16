#!/usr/bin/env python3
"""本地一键运行全部静态检查，CI 也复用同一入口。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "scripts/check_links.py",
    "scripts/check_constants.py",
    "scripts/check_layers.py",
    "scripts/check_frontend.py",
    "scripts/check_records.py",
    "scripts/check_secrets.py",
]


def main() -> int:
    failed = 0
    for script in CHECKS:
        print(f"\n=== {script} ===")
        result = subprocess.run([sys.executable, script], cwd=ROOT)
        if result.returncode != 0:
            failed += 1

    if failed:
        print(f"\nFAIL: {failed} 项检查未通过。")
        return 1
    print("\nOK: 全部静态检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
