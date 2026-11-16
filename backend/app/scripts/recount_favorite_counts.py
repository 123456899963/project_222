"""重算 teas.favorite_count，使其与 favorite_items 的真实收藏一致。

历史导入脚本曾随机生成收藏数；本脚本用于一次性校正既有数据。
计数口径与业务一致：同一用户把同一茶品收进多个清单只算 1 次。

用法：
    python -m app.scripts.recount_favorite_counts [--dry-run]
"""

from __future__ import annotations

import argparse

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.favorite import FavoriteItem
from app.models.tea import Tea


def recount(db: Session, *, dry_run: bool = False) -> tuple[int, int]:
    """返回 (发生变化的茶品数, 茶品总数)。dry_run 时不写库。"""
    rows = (
        db.query(
            FavoriteItem.tea_id,
            func.count(func.distinct(FavoriteItem.user_id)),
        )
        .group_by(FavoriteItem.tea_id)
        .all()
    )
    expected = {tea_id: int(count) for tea_id, count in rows}

    changed = 0
    teas = db.query(Tea).all()
    for tea in teas:
        target = expected.get(tea.id, 0)
        if int(tea.favorite_count or 0) != target:
            changed += 1
            if not dry_run:
                tea.favorite_count = target

    if not dry_run:
        db.commit()
    return changed, len(teas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="重算茶品收藏数")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        changed, total = recount(db, dry_run=args.dry_run)
    finally:
        db.close()

    action = "待修正" if args.dry_run else "已修正"
    print(f"{action} {changed} / {total} 款茶品的 favorite_count")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
