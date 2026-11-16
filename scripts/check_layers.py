#!/usr/bin/env python3
"""用 AST 检查后端五层红线，允许已知历史遗留，阻止新增违规。"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"

# 已知遗留：这些文件允许暂时直连查询，但不得新增到其他文件。
# 历史遗留已清理完毕，当前为空集合；如再次出现需在评审中登记并限期修复。
KNOWN_DEBT: set[str] = set()


class QueryVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.hits: list[int] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "query":
            self.hits.append(node.lineno)
        self.generic_visit(node)


def imports_models(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app.models" or node.module.startswith("app.models."):
                lines.append(node.lineno)
    return lines


def main() -> int:
    errors: list[str] = []
    debt: list[str] = []

    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
        is_router = rel.startswith("routers/")
        is_service = rel.startswith("services/")
        is_schema = rel.startswith("schemas/")

        if is_router:
            model_imports = imports_models(tree)
            if model_imports:
                errors.append(f"{rel}: Router 不得 import Model（第 {model_imports} 行）")
            visitor = QueryVisitor()
            visitor.visit(tree)
            if visitor.hits:
                errors.append(f"{rel}: Router 不得直接查询数据库（第 {visitor.hits} 行）")

        if is_service:
            visitor = QueryVisitor()
            visitor.visit(tree)
            if visitor.hits:
                message = f"{rel}: Service 应调用 Repository，不应直接 db.query（第 {visitor.hits} 行）"
                if rel in KNOWN_DEBT:
                    debt.append(message)
                else:
                    errors.append(message)

        if is_schema:
            model_imports = imports_models(tree)
            if model_imports:
                errors.append(f"{rel}: Schema 不得 import Model（第 {model_imports} 行）")

    for item in debt:
        print(f"BASELINE: {item}")
    if errors:
        print("FAIL: 发现新的五层红线违规：")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"OK: 五层检查通过（历史遗留 {len(debt)} 项，未新增违规）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
