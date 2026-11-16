"""用户统计业务层（S15）

等级四档，按收藏数实时计算，不落库：
- 茶客 0–4
- 茶友 5–19
- 茶人 20–49
- 茶师 ≥50
"""

from sqlalchemy.orm import Session

from app.repositories import favorite_repo, share_repo
from app.schemas.stats import LevelInfo, UserStats

# (等级名, 达到该等级所需收藏数)；顺序敏感，阈值必须递增
LEVELS: tuple[tuple[str, int], ...] = (
    ("茶客", 0),
    ("茶友", 5),
    ("茶人", 20),
    ("茶师", 50),
)


def resolve_level(favorite_count: int) -> LevelInfo:
    """按收藏数解析等级与下一级差距（纯函数，便于边界测试）。"""
    count = max(0, int(favorite_count))
    index = 0
    for i, (_, threshold) in enumerate(LEVELS):
        if count >= threshold:
            index = i
        else:
            break

    name = LEVELS[index][0]
    next_pair = LEVELS[index + 1] if index + 1 < len(LEVELS) else None
    if next_pair is None:
        return LevelInfo(name=name, index=index + 1, remaining=0)
    return LevelInfo(
        name=name,
        index=index + 1,
        next_name=next_pair[0],
        next_threshold=next_pair[1],
        remaining=next_pair[1] - count,
    )


def get_stats(db: Session, user_id: int) -> UserStats:
    favorite_count = favorite_repo.count_by_user(db, user_id)
    note_count = favorite_repo.count_notes_by_user(db, user_id)
    share_count = share_repo.count_active_by_user(db, user_id)
    return UserStats(
        favorite_count=favorite_count,
        note_count=note_count,
        share_count=share_count,
        level=resolve_level(favorite_count),
    )
