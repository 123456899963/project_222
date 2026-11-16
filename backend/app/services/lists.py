"""清单与品鉴笔记业务层（PRD FR-5.1 ~ FR-5.3 / API_CONTRACT §4.4，S9 多清单）

- 每用户默认清单惰性创建；UNIQUE(user_id, is_default) 并发冲突按已存在处理
- 单用户最多 10 个清单；默认清单不可删除
- 删除清单时条目迁移到默认清单，重复茶品合并笔记（默认清单非空笔记优先）
- 标题 trim 后 2–20 字；笔记 ≤20,000 字符；纯空白归一化为 NULL
"""

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.response import InternalError, ListNotFound, TeaGuideError
from app.models.collection_list import CollectionList
from app.repositories import list_repo, share_repo
from app.schemas.list import (
    ListData,
    ListItem,
    ListSummary,
    ListTitleData,
    NoteUpdateData,
    ShareBrief,
)

TITLE_MIN_LEN = 2
TITLE_MAX_LEN = 20
NOTE_MAX_LEN = 20000
MAX_LISTS = 10
DEFAULT_TITLE = "我的收藏"


def _validate_title(title: str) -> str:
    normalized = (title or "").strip()
    if not (TITLE_MIN_LEN <= len(normalized) <= TITLE_MAX_LEN):
        raise TeaGuideError(40000, "清单标题需为 2–20 个字符")
    return normalized


def _share_brief(db: Session, list_id: int) -> ShareBrief | None:
    active = share_repo.get_active_by_list(db, list_id)
    if active is None:
        return None
    return ShareBrief(
        token=active.token,
        url=f"/c/{active.token}",
        created_at=active.created_at,
    )


_RETRYABLE_DB_CODES = {1205, 1213}  # 锁等待超时 / 死锁


def _is_retryable(exc: OperationalError) -> bool:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    return bool(args) and args[0] in _RETRYABLE_DB_CODES


def get_or_create_default_list(db: Session, user_id: int) -> CollectionList:
    """取用户默认清单，不存在则创建（只 flush，事务由调用方提交）。

    并发创建同一默认清单时唯一索引会报重复键或死锁，回滚后重查即可。
    """
    list_obj = list_repo.get_default(db, user_id)
    if list_obj:
        return list_obj

    for _ in range(3):
        try:
            return list_repo.create(db, user_id=user_id, title=DEFAULT_TITLE, is_default=True)
        except IntegrityError:
            db.rollback()
            list_obj = list_repo.get_default(db, user_id)
            if list_obj:
                return list_obj
        except OperationalError as exc:
            if not _is_retryable(exc):
                raise
            db.rollback()
            list_obj = list_repo.get_default(db, user_id)
            if list_obj:
                return list_obj

    list_obj = list_repo.get_default(db, user_id)
    if list_obj is None:
        raise InternalError
    return list_obj


def _get_owned_list(db: Session, user_id: int, list_id: int) -> CollectionList:
    list_obj = list_repo.get_by_id(db, list_id)
    if list_obj is None or list_obj.user_id != user_id:
        raise ListNotFound
    return list_obj


def resolve_list(db: Session, user_id: int, list_id: int | None) -> CollectionList:
    """解析目标清单：未指定时返回默认清单，指定时校验归属。"""
    if list_id is None:
        return get_or_create_default_list(db, user_id)
    return _get_owned_list(db, user_id, list_id)


def _summary(db: Session, list_obj: CollectionList) -> ListSummary:
    return ListSummary(
        id=list_obj.id,
        title=list_obj.title,
        is_default=bool(list_obj.is_default),
        tea_count=list_repo.count_items(db, list_obj.id),
        created_at=list_obj.created_at,
        updated_at=list_obj.updated_at,
        share=_share_brief(db, list_obj.id),
    )


def list_summaries(db: Session, user_id: int) -> list[ListSummary]:
    """用户全部清单摘要（默认清单置顶）。"""
    get_or_create_default_list(db, user_id)
    db.commit()  # 惰性创建的默认清单落库；纯读事务提交无副作用
    return [_summary(db, item) for item in list_repo.list_by_user(db, user_id)]


def get_list_detail(db: Session, user_id: int, list_id: int) -> ListData:
    list_obj = _get_owned_list(db, user_id, list_id)
    rows = list_repo.list_items(db, list_obj.id)

    items = [
        ListItem(
            tea_id=tea.id,
            name=tea.name,
            category=tea.category,
            origin=tea.origin,
            season=tea.season,
            main_image_url=tea.main_image_url,
            favorite_count=int(tea.favorite_count or 0),
            is_available=bool(tea.is_active),
            tasting_note=fav.tasting_note,
            favorited_at=fav.created_at,
        )
        for fav, tea in rows
    ]

    return ListData(
        id=list_obj.id,
        title=list_obj.title,
        is_default=bool(list_obj.is_default),
        tea_count=len(items),
        created_at=list_obj.created_at,
        updated_at=list_obj.updated_at,
        share=_share_brief(db, list_obj.id),
        items=items,
    )


def create_list(db: Session, user_id: int, title: str) -> ListSummary:
    normalized = _validate_title(title)
    if list_repo.count_by_user(db, user_id) >= MAX_LISTS:
        raise TeaGuideError(40000, "最多创建 10 个清单")

    list_obj = list_repo.create(db, user_id=user_id, title=normalized, is_default=False)
    db.commit()
    db.refresh(list_obj)
    return _summary(db, list_obj)


def update_title(db: Session, user_id: int, list_id: int, title: str) -> ListTitleData:
    normalized = _validate_title(title)
    list_obj = _get_owned_list(db, user_id, list_id)
    list_obj = list_repo.update_title(db, list_obj, normalized)
    return ListTitleData(
        id=list_obj.id,
        title=list_obj.title,
        is_default=bool(list_obj.is_default),
        updated_at=list_obj.updated_at,
    )


def delete_list(db: Session, user_id: int, list_id: int) -> None:
    """删除非默认清单：条目迁入默认清单，重复茶品合并笔记，分享令牌随清单级联删除。"""
    list_obj = _get_owned_list(db, user_id, list_id)
    if list_obj.is_default:
        raise TeaGuideError(40000, "默认清单不可删除")

    default_list = get_or_create_default_list(db, user_id)
    default_tea_ids = {tea.id for _fav, tea in list_repo.list_items(db, default_list.id)}

    for fav, tea in list_repo.list_items(db, list_obj.id):
        if tea.id not in default_tea_ids:
            list_repo.move_item(db, fav, default_list.id)
            continue

        existing = list_repo.get_favorite_item(db, default_list.id, tea.id)
        if (
            existing is not None
            and not (existing.tasting_note or "").strip()
            and (fav.tasting_note or "").strip()
        ):
            existing.tasting_note = fav.tasting_note
        list_repo.delete_item(db, fav)

    list_repo.delete(db, list_obj)


def save_note(
    db: Session, *, user_id: int, list_id: int, tea_id: int, content: str | None
) -> NoteUpdateData:
    note = (content or "").strip() or None
    if note is not None and len(note) > NOTE_MAX_LEN:
        raise TeaGuideError(40000, "笔记过长")

    list_obj = _get_owned_list(db, user_id, list_id)
    item = list_repo.get_favorite_item(db, list_obj.id, tea_id)
    if item is None:
        raise TeaGuideError(40430, "该茶品不在当前清单中")

    item = list_repo.update_note(db, item, note)
    return NoteUpdateData(tea_id=tea_id, list_id=list_obj.id, tasting_note=item.tasting_note)
