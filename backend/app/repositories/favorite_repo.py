"""收藏仓储层：仅封装 SQLAlchemy 查询与写入，不做业务判断（ARCHITECTURE §3）

计数维护必须与收藏行写入同事务，故本层只 flush 不 commit，
事务边界由 Service 层控制。
"""

from sqlalchemy import case, func, update
from sqlalchemy.orm import Session

from app.models.favorite import FavoriteItem
from app.models.tea import Tea


def get_favorite(db: Session, list_id: int, tea_id: int) -> FavoriteItem | None:
    """查询某清单内某茶品的收藏行。"""
    return (
        db.query(FavoriteItem)
        .filter(FavoriteItem.list_id == list_id, FavoriteItem.tea_id == tea_id)
        .first()
    )


def get_any_favorite(db: Session, user_id: int, tea_id: int) -> FavoriteItem | None:
    """查询用户任意清单中是否存在该茶（跨清单去重依据）。"""
    return (
        db.query(FavoriteItem)
        .filter(FavoriteItem.user_id == user_id, FavoriteItem.tea_id == tea_id)
        .first()
    )


def list_ids_for_tea(db: Session, user_id: int, tea_id: int) -> list[int]:
    """该茶品所在清单 ID 列表（升序）。"""
    rows = (
        db.query(FavoriteItem.list_id)
        .filter(FavoriteItem.user_id == user_id, FavoriteItem.tea_id == tea_id)
        .order_by(FavoriteItem.list_id.asc())
        .all()
    )
    return [list_id for (list_id,) in rows]


def create_favorite(db: Session, user_id: int, tea_id: int, list_id: int) -> FavoriteItem:
    """新增收藏行并 flush（唯一冲突由 Service 捕获 IntegrityError 处理）。"""
    item = FavoriteItem(user_id=user_id, tea_id=tea_id, list_id=list_id)
    db.add(item)
    db.flush()
    return item


def delete_favorite(db: Session, list_id: int, tea_id: int) -> int:
    """删除指定清单内的收藏行，返回受影响行数（0 表示本未收藏）。"""
    return (
        db.query(FavoriteItem)
        .filter(FavoriteItem.list_id == list_id, FavoriteItem.tea_id == tea_id)
        .delete(synchronize_session=False)
    )


def delete_all_for_tea(db: Session, user_id: int, tea_id: int) -> int:
    """删除用户所有清单中的该茶条目，返回受影响行数。"""
    return (
        db.query(FavoriteItem)
        .filter(FavoriteItem.user_id == user_id, FavoriteItem.tea_id == tea_id)
        .delete(synchronize_session=False)
    )


def increment_favorite_count(db: Session, tea_id: int) -> None:
    """原子 +1，避免并发读改写丢失更新。"""
    db.execute(update(Tea).where(Tea.id == tea_id).values(favorite_count=Tea.favorite_count + 1))


def decrement_favorite_count(db: Session, tea_id: int) -> None:
    """原子 −1，使用 CASE 保证不低于 0（unsigned 列不可出现负数）。"""
    db.execute(
        update(Tea)
        .where(Tea.id == tea_id)
        .values(
            favorite_count=case(
                (Tea.favorite_count > 0, Tea.favorite_count - 1),
                else_=0,
            )
        )
    )


def list_tea_ids(db: Session, user_id: int, *, for_update: bool = False) -> set[int]:
    """用户已收藏的茶品 ID 集合；for_update 用于并发 copy 的当前读。"""
    query = db.query(FavoriteItem.tea_id).filter(FavoriteItem.user_id == user_id)
    if for_update:
        query = query.with_for_update()
    return {tea_id for (tea_id,) in query.all()}


# ===== S15 用户统计 / S16 个性化推荐 =====


def count_by_user(db: Session, user_id: int) -> int:
    """用户收藏茶品数（S15 等级依据）：同一茶品跨清单只计 1 次。"""
    return int(
        db.query(func.count(func.distinct(FavoriteItem.tea_id)))
        .filter(FavoriteItem.user_id == user_id)
        .scalar()
        or 0
    )


def count_notes_by_user(db: Session, user_id: int) -> int:
    """用户非空品鉴笔记数（同一茶品跨清单只计 1 次）。"""
    return int(
        db.query(func.count(func.distinct(FavoriteItem.tea_id)))
        .filter(
            FavoriteItem.user_id == user_id,
            FavoriteItem.tasting_note.isnot(None),
            FavoriteItem.tasting_note != "",
        )
        .scalar()
        or 0
    )


def count_categories_by_user(db: Session, user_id: int) -> list[tuple[str, int]]:
    """用户收藏的茶类分布（S16 个性化推荐权重）：同一茶品跨清单只计 1 次。"""
    rows = (
        db.query(Tea.category, func.count(func.distinct(FavoriteItem.tea_id)))
        .join(Tea, Tea.id == FavoriteItem.tea_id)
        .filter(FavoriteItem.user_id == user_id)
        .group_by(Tea.category)
        .all()
    )
    return [(category, int(cnt)) for category, cnt in rows]
