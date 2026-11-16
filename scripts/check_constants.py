#!/usr/bin/env python3
"""校验文档中的关键数量与契约文件是否一致。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "openapi_operations": 60,
    "test_cases": 100,
    "security_controls": 35,
    "database_tables": 14,
}

METHOD_RE = re.compile(r"^\s{4}(get|post|put|patch|delete):\s*$")
PATH_RE = re.compile(r"^\s{2}/[^:]+:\s*$")
CASE_RE = re.compile(r"TC-[A-Z]+-\d{2}")
SECURITY_RE = re.compile(r"\*\*S-(\d{2})\*\*")
TABLE_RE = re.compile(r"CREATE TABLE\s+\w+", re.I)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def openapi_operations() -> int:
    lines = read("docs/api/openapi.yaml").splitlines()
    in_paths = False
    count = 0
    for line in lines:
        if line.strip() == "paths:":
            in_paths = True
            continue
        if in_paths and line and not line.startswith(" ") and not line.startswith("#"):
            in_paths = False
        if in_paths and METHOD_RE.match(line):
            count += 1
    return count


def main() -> int:
    actual = {
        "openapi_operations": openapi_operations(),
        "test_cases": len(set(CASE_RE.findall(read("docs/testing/TEST_PLAN.md")))),
        "security_controls": len(set(SECURITY_RE.findall(read("docs/architecture/SECURITY.md")))),
        "database_tables": len(TABLE_RE.findall(read("database/init.sql"))),
    }

    errors: list[str] = []
    for key, expected in EXPECTED.items():
        if actual[key] != expected:
            errors.append(f"{key}: 期望 {expected}，实际 {actual[key]}")

    claims = [
        ("AGENTS.md", "60 个业务端点"),
        ("AGENTS.md", "100 条用例"),
        ("AGENTS.md", "35 项"),
        ("AGENTS.md", "14 张表"),
        ("docs/api/README.md", "60 个业务端点"),
        ("docs/testing/TEST_PLAN.md", "100 条"),
    ]
    for path, phrase in claims:
        if phrase not in read(path):
            errors.append(f"{path}: 未找到口径声明「{phrase}」")

    if not (ROOT / "frontend" / "package-lock.json").exists():
        errors.append("frontend/package-lock.json 缺失：npm 是唯一包管理器")
    if (ROOT / "frontend" / "pnpm-lock.yaml").exists():
        errors.append("发现 pnpm-lock.yaml：项目只允许一套 lockfile（npm）")
    for path in (
        "AGENTS.md",
        "docs/architecture/TECH_STACK.md",
        "docs/architecture/ARCHITECTURE.md",
        "docs/development/DEVELOPMENT_GUIDE.md",
        "harness/TASK_TEMPLATE.md",
    ):
        if "pnpm" in read(path).lower():
            errors.append(f"{path}: 权威文档仍包含 pnpm 口径")

    if errors:
        print("FAIL: 文档常量不一致：")
        for item in errors:
            print(f"  - {item}")
        print(f"实际值：{actual}")
        return 1

    print(f"OK: 常量一致 {actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
