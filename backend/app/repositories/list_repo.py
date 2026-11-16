"""清单仓储层：仅封装 SQLAlchemy 查询与写入（ARCHITECTURE §3）

事务边界由 Service 控制；本层 create / move / delete 只 flush 不 commit，
标题更新与清单删除由 Service 显式 commit。
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.collection_list import CollectionList
from app.models.favorite import FavoriteItem
from app.models.tea import Tea


def get_by_id(db: Session, list_id: int) -> CollectionList | None:
    return db.query(CollectionList).filter(CollectionList.id == list_id).first()


def get_by_id_for_update(db: Session, list_id: int) -> CollectionList | None:
    """行锁读取指定清单（并发生成分享令牌时串行化）。"""
    return db.query(CollectionList).filter(CollectionList.id == list_id).with_for_update().first()


def get_default(db: Session, user_id: int) -> CollectionList | None:
    return (
        db.query(CollectionList)
        .filter(CollectionList.user_id == user_id, CollectionList.is_default.is_(True))
        .first()
    )


def get_default_for_update(db: Session, user_id: int) -> CollectionList | None:
    """行锁读取默认清单（并发生成分享令牌时串行化）。"""
    return (
        db.query(CollectionList)
        .filter(CollectionList.user_id == user_id, CollectionList.is_default.is_(True))
        .with_for_update()
        .first()
    )


def list_by_user(db: Session, user_id: int) -> list[CollectionList]:
    """用户全部清单：默认清单置顶，其余按创建时间升序（稳定）。"""
    return (
        db.query(CollectionList)
        .filter(CollectionList.user_id == user_id)
        .order_by(CollectionList.is_default.desc(), CollectionList.created_at.asc())
        .all()
    )


def count_by_user(db: Session, user_id: int) -> int:
    return db.query(CollectionList).filter(CollectionList.user_id == user_id).count()


def create(db: Session, *, user_id: int, title: str, is_default: bool = False) -> CollectionList:
    """新增清单并 flush；唯一冲突由 Service 捕获 IntegrityError。"""
    item = CollectionList(
        user_id=user_id,
        title=title,
        is_default=True if is_default else None,
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def update_title(db: Session, list_obj: CollectionList, title: str) -> CollectionList:
    list_obj.title = title
    list_obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(list_obj)
    return list_obj


def delete(db: Session, list_obj: CollectionList) -> None:
    db.delete(list_obj)
    db.commit()


def list_items(db: Session, list_id: int) -> list[tuple[FavoriteItem, Tea]]:
    """清单条目：按 favorited_at DESC, tea_id DESC（§4.4.1）。"""
    return (
        db.query(FavoriteItem, Tea)
        .join(Tea, Tea.id == FavoriteItem.tea_id)
        .filter(FavoriteItem.list_id == list_id)
        .order_by(FavoriteItem.created_at.desc(), FavoriteItem.tea_id.desc())
        .all()
    )


def count_items(db: Session, list_id: int) -> int:
    return db.query(FavoriteItem).filter(FavoriteItem.list_id == list_id).count()


def get_favorite_item(db: Session, list_id: int, tea_id: int) -> FavoriteItem | None:
    return (
        db.query(FavoriteItem)
        .filter(FavoriteItem.list_id == list_id, FavoriteItem.tea_id == tea_id)
        .first()
    )


def update_note(db: Session, item: FavoriteItem, note: str | None) -> FavoriteItem:
    item.tasting_note = note
    db.commit()
    db.refresh(item)
    return item


def move_item(db: Session, item: FavoriteItem, list_id: int) -> None:
    """把条目迁移到另一清单（只 flush，由 Service 统一提交）。"""
    item.list_id = list_id
    db.flush()


def delete_item(db: Session, item: FavoriteItem) -> None:
    db.delete(item)
    db.flush()
