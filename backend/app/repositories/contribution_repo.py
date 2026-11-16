"""用户贡献仓储层：仅封装查询与写入（ARCHITECTURE §3）

事务边界由 Service 控制；create / delete 只 flush，不 commit。
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.contribution import Contribution, TeaNameCategoryMap
from app.models.tea import Tea
from app.models.user import User


def create(
    db: Session,
    *,
    user_id: int,
    type: str,
    target_tea_id: int | None,
    payload: dict,
) -> Contribution:
    item = Contribution(
        user_id=user_id,
        type=type,
        target_tea_id=target_tea_id,
        payload=payload,
        status="pending",
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def get_by_id(db: Session, contribution_id: int) -> Contribution | None:
    return db.query(Contribution).filter(Contribution.id == contribution_id).first()


def list_by_user(db: Session, user_id: int) -> list[Contribution]:
    return (
        db.query(Contribution)
        .filter(Contribution.user_id == user_id)
        .order_by(Contribution.created_at.desc(), Contribution.id.desc())
        .all()
    )


def admin_list(
    db: Session,
    *,
    status: str | None,
    type: str | None,
    offset: int,
    limit: int,
) -> tuple[list[tuple[Contribution, str]], int]:
    """管理端队列：按状态/类型过滤，附带提交者用户名（时间倒序）。"""
    query = db.query(Contribution, User.username).join(User, User.id == Contribution.user_id)
    if status:
        query = query.filter(Contribution.status == status)
    if type:
        query = query.filter(Contribution.type == type)
    total = query.count()
    rows = (
        query.order_by(Contribution.created_at.desc(), Contribution.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total


def list_approved_articles(db: Session, tea_id: int) -> list[tuple[Contribution, str]]:
    """茶品详情页展示的已通过科普投稿（时间倒序）。"""
    return (
        db.query(Contribution, User.username)
        .join(User, User.id == Contribution.user_id)
        .filter(
            Contribution.type == "article",
            Contribution.status == "approved",
            Contribution.target_tea_id == tea_id,
        )
        .order_by(Contribution.created_at.desc(), Contribution.id.desc())
        .all()
    )


def get_map_by_name(db: Session, name: str) -> TeaNameCategoryMap | None:
    return db.query(TeaNameCategoryMap).filter(TeaNameCategoryMap.name == name).first()


def list_tea_names(db: Session) -> list[tuple[int, str]]:
    """全部茶品（含下架）的名称，用于名称查重。"""
    return db.query(Tea.id, Tea.name).all()


def count_by_status(db: Session, status: str) -> int:
    return db.query(func.count(Contribution.id)).filter(Contribution.status == status).scalar() or 0


def delete(db: Session, item: Contribution) -> None:
    db.delete(item)
    db.flush()
