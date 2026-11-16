"""茶品图片集仓储层（ADR-0003 S4）

只封装 SQLAlchemy 查询，不做业务判断。
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tea import TeaMedia


def list_by_tea(db: Session, tea_id: int) -> list[TeaMedia]:
    return (
        db.query(TeaMedia)
        .filter(TeaMedia.tea_id == tea_id)
        .order_by(TeaMedia.sort_order.asc(), TeaMedia.id.asc())
        .all()
    )


def count_by_tea(db: Session, tea_id: int) -> int:
    return db.query(TeaMedia).filter(TeaMedia.tea_id == tea_id).count()


def get_by_id(db: Session, image_id: int) -> TeaMedia | None:
    return db.query(TeaMedia).filter(TeaMedia.id == image_id).first()


def next_sort_order(db: Session, tea_id: int) -> int:
    max_order = db.query(func.max(TeaMedia.sort_order)).filter(TeaMedia.tea_id == tea_id).scalar()
    return 0 if max_order is None else int(max_order) + 1


def create(db: Session, *, tea_id: int, image_url: str, sort_order: int) -> TeaMedia:
    row = TeaMedia(tea_id=tea_id, image_url=image_url, sort_order=sort_order)
    db.add(row)
    db.flush()
    return row


def delete(db: Session, row: TeaMedia) -> None:
    db.delete(row)
