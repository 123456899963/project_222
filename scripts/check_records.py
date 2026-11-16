#!/usr/bin/env python3
"""检查 build-log 顺序、ADR 索引，以及 PR 变更是否同步了记录/文档。"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_LOG = ROOT / "harness" / "build-log.md"
ADR_DIR = ROOT / "docs" / "development" / "ADR"
ADR_README = ADR_DIR / "README.md"
ENTRY_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})｜", re.M)


def git_diff(base_ref: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"WARN: 无法计算 diff（{exc}），跳过 PR 同步检查。")
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_build_log_order() -> list[str]:
    dates = ENTRY_RE.findall(BUILD_LOG.read_text(encoding="utf-8", errors="ignore"))
    errors = []
    for earlier, later in zip(dates, dates[1:]):
        if earlier < later:
            errors.append(f"build-log 日期未按倒序排列：{earlier} 在 {later} 之前")
    return errors


def check_adr_index() -> list[str]:
    errors = []
    readme = ADR_README.read_text(encoding="utf-8", errors="ignore")
    files = {p.name for p in ADR_DIR.glob("ADR-*.md")}
    for name in files:
        if name not in readme:
            errors.append(f"ADR 索引缺少 {name}")
    for link in re.findall(r"\((ADR-[^)]+\.md)\)", readme):
        if link not in files:
            errors.append(f"ADR 索引指向不存在的文件 {link}")
    return errors


def check_sync(changed: list[str]) -> list[str]:
    errors = []
    code_changed = any(
        p.startswith(("backend/app/", "frontend/src/")) for p in changed
    )
    if code_changed and "harness/build-log.md" not in changed:
        errors.append("代码有变更，但 harness/build-log.md 未更新")

    if any(p.startswith(("backend/app/models/", "backend/app/alembic/")) for p in changed):
        if "database/init.sql" not in changed or "docs/architecture/DATA_MODEL.md" not in changed:
            errors.append("模型/迁移有变更，但 init.sql 或 DATA_MODEL.md 未同步")

    if any(p.startswith(("backend/app/schemas/", "backend/app/routers/")) for p in changed):
        if "docs/api/API_CONTRACT.md" not in changed or "docs/api/openapi.yaml" not in changed:
            errors.append("Schema/路由有变更，但 API_CONTRACT.md 或 openapi.yaml 未同步")

    deps_changed = "backend/requirements.txt" in changed or "frontend/package.json" in changed
    adr_changed = any(p.startswith("docs/development/ADR/ADR-") for p in changed)
    if deps_changed and not adr_changed:
        errors.append("依赖有变更，但未新增或更新 ADR")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="")
    args = parser.parse_args()

    errors = check_build_log_order() + check_adr_index()
    if args.base_ref:
        changed = git_diff(args.base_ref)
        if changed is not None:
            errors.extend(check_sync(changed))

    if errors:
        print("FAIL: 记录与同步检查未通过：")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("OK: build-log 顺序、ADR 索引与 PR 同步检查通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
