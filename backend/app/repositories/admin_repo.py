"""管理员后台仓储层：仅封装查询与写入，不做业务判断（ARCHITECTURE §3）

事务边界由 Service 层控制：本层只 add/flush，不 commit。
"""

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.operation_log import OperationLog
from app.models.tea import Tea, TeaBrewingGuide, TeaTips
from app.models.user import User
from app.repositories._common import escape_like


def list_teas(
    db: Session,
    *,
    categories: list[str] | None = None,
    keyword: str | None = None,
    is_active: bool | None = None,
    sort: str = "newest",
    offset: int = 0,
    limit: int = 12,
) -> tuple[list[Tea], int]:
    """后台列表：包含下架茶品；is_active 省略时不过滤（API_CONTRACT §4.6.1）。"""
    query = db.query(Tea)

    if categories:
        query = query.filter(Tea.category.in_(categories))
    if is_active is not None:
        query = query.filter(Tea.is_active.is_(is_active))
    if keyword:
        pattern = f"%{escape_like(keyword)}%"
        query = query.filter(
            or_(
                Tea.name.like(pattern, escape="\\"),
                Tea.origin.like(pattern, escape="\\"),
            )
        )

    if sort == "favorite":
        query = query.order_by(Tea.favorite_count.desc(), Tea.created_at.desc(), Tea.id.desc())
    else:
        query = query.order_by(Tea.created_at.desc(), Tea.id.desc())

    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total


def count_stats(db: Session) -> tuple[int, int, int]:
    """返回 (总数, 上架数, 下架数)，统计全部茶品。"""
    total = db.query(func.count(Tea.id)).scalar() or 0
    active = db.query(func.count(Tea.id)).filter(Tea.is_active.is_(True)).scalar() or 0
    return total, active, total - active


def count_by_category_all(db: Session) -> dict[str, int]:
    """七大茶类分布（含下架），缺失由 Service 补 0。"""
    rows = db.query(Tea.category, func.count(Tea.id)).group_by(Tea.category).all()
    return {category: count for category, count in rows}


def create_tea(db: Session, fields: dict) -> Tea:
    tea = Tea(**fields)
    db.add(tea)
    db.flush()
    return tea


def update_tea(db: Session, tea: Tea, fields: dict) -> None:
    for key, value in fields.items():
        setattr(tea, key, value)
    db.flush()


def set_active(db: Session, tea: Tea, is_active: bool) -> None:
    tea.is_active = is_active
    db.flush()


def get_tips(db: Session, tea_id: int) -> TeaTips | None:
    return db.query(TeaTips).filter(TeaTips.tea_id == tea_id).first()


def create_tips(db: Session, tea_id: int, values: dict) -> TeaTips:
    tips = TeaTips(tea_id=tea_id, **values)
    db.add(tips)
    db.flush()
    return tips


def update_tips(db: Session, tips: TeaTips, values: dict) -> None:
    for key, value in values.items():
        setattr(tips, key, value)
    db.flush()


def get_brewing_guide(db: Session, tea_id: int) -> TeaBrewingGuide | None:
    return db.query(TeaBrewingGuide).filter(TeaBrewingGuide.tea_id == tea_id).first()


def create_brewing_guide(db: Session, tea_id: int, values: dict) -> TeaBrewingGuide:
    guide = TeaBrewingGuide(tea_id=tea_id, **values)
    db.add(guide)
    db.flush()
    return guide


def update_brewing_guide(db: Session, guide: TeaBrewingGuide, values: dict) -> None:
    for key, value in values.items():
        setattr(guide, key, value)
    db.flush()


def delete_brewing_guide(db: Session, guide: TeaBrewingGuide) -> None:
    db.delete(guide)
    db.flush()


def list_operation_logs(
    db: Session,
    *,
    action: str | None = None,
    target_type: str | None = None,
    admin_id: int | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[tuple[OperationLog, str | None]], int]:
    """操作日志查询（API_CONTRACT §4.6.12）：附操作人用户名，时间倒序。

    左连 users：账号删除后 user_id 为 NULL，日志仍保留（admin_username 为 NULL）。
    """
    query = db.query(OperationLog, User.username).outerjoin(User, User.id == OperationLog.user_id)

    if action:
        query = query.filter(OperationLog.action == action)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)
    if admin_id is not None:
        query = query.filter(OperationLog.user_id == admin_id)
    if start_at is not None:
        query = query.filter(OperationLog.created_at >= start_at)
    if end_at is not None:
        query = query.filter(OperationLog.created_at < end_at)

    total = query.count()
    rows = (
        query.order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def add_operation_log(
    db: Session,
    *,
    user_id: int,
    action: str,
    target_id: int | None,
    detail: str,
    target_type: str = "tea",
) -> OperationLog:
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail[:500],
    )
    db.add(log)
    return log
