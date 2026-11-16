"""收藏业务层（PRD FR-5.1 / API_CONTRACT §4.3，S9 多清单）

- 收藏与取消幂等；可指定目标清单，未指定时归入默认清单
- 同一茶品可存在于多个清单，但 teas.favorite_count 只在跨清单首次收藏时 +1、
  最后一条被移除时 −1
- 下架茶不可新增收藏，但允许取消/状态查询
- 并发依赖 UNIQUE(list_id, tea_id) 兜底，撞唯一冲突按「已收藏」处理；
  同时通过茶品行锁串行化同一茶品的跨清单计数
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.response import TeaNotFound, TeaOffShelf
from app.models.tea import Tea
from app.repositories import favorite_repo, tea_repo
from app.schemas.favorite import FavoriteState
from app.services import lists as lists_service


def _state(db: Session, tea: Tea, user_id: int) -> FavoriteState:
    list_ids = favorite_repo.list_ids_for_tea(db, user_id, tea.id)
    return FavoriteState(
        tea_id=tea.id,
        is_favorited=bool(list_ids),
        favorite_count=int(tea.favorite_count or 0),
        list_ids=list_ids,
    )


def _get_tea_or_404(db: Session, tea_id: int) -> Tea:
    # 收藏状态只需 is_active / favorite_count，无需加载 tea_tips
    tea = tea_repo.get_by_id(db, tea_id, with_tips=False)
    if not tea:
        raise TeaNotFound
    return tea


def _lock_tea_or_404(db: Session, tea_id: int) -> Tea:
    tea = tea_repo.get_by_id_for_update(db, tea_id)
    if not tea:
        raise TeaNotFound
    return tea


def add_favorite(
    db: Session, *, user_id: int, tea_id: int, list_id: int | None = None
) -> FavoriteState:
    """收藏茶品（幂等）。下架茶返回 40401；目标清单不存在/越权返回 40420。"""
    # 先解析清单（可能创建默认清单），再锁茶品行：与 copy_all 保持「清单 → 茶品」锁序
    _get_tea_or_404(db, tea_id)
    target = lists_service.resolve_list(db, user_id, list_id)

    # 锁父行：同茶品的收藏/取消全局串行化，保证跨清单计数正确
    tea = _lock_tea_or_404(db, tea_id)
    if not tea.is_active:
        raise TeaOffShelf

    already_favorited = favorite_repo.get_any_favorite(db, user_id, tea_id) is not None

    if favorite_repo.get_favorite(db, target.id, tea_id):
        db.commit()  # 释放行锁
        tea = _get_tea_or_404(db, tea_id)
        return _state(db, tea, user_id)

    try:
        favorite_repo.create_favorite(db, user_id, tea_id, target.id)
        if not already_favorited:
            favorite_repo.increment_favorite_count(db, tea_id)
        db.commit()
    except IntegrityError:
        # 并发下另一请求已插入同一 (list_id, tea_id)：按已收藏幂等处理
        db.rollback()
        tea = _get_tea_or_404(db, tea_id)
        return _state(db, tea, user_id)

    tea = _get_tea_or_404(db, tea_id)
    return _state(db, tea, user_id)


def remove_favorite(
    db: Session, *, user_id: int, tea_id: int, list_id: int | None = None
) -> FavoriteState:
    """取消收藏（幂等）。

    指定 list_id 时仅移除该清单条目；未指定时移除该茶在所有清单中的条目。
    只有跨清单全部移除后才递减 teas.favorite_count。
    """
    target = lists_service.resolve_list(db, user_id, list_id) if list_id is not None else None
    tea = _lock_tea_or_404(db, tea_id)

    if list_id is None:
        removed = favorite_repo.delete_all_for_tea(db, user_id, tea_id)
    else:
        removed = favorite_repo.delete_favorite(db, target.id, tea_id)

    if removed and favorite_repo.get_any_favorite(db, user_id, tea_id) is None:
        favorite_repo.decrement_favorite_count(db, tea_id)
    db.commit()

    tea = _get_tea_or_404(db, tea_id)
    return _state(db, tea, user_id)


def get_status(db: Session, *, user_id: int, tea_id: int) -> FavoriteState:
    """查询收藏状态；允许已下架茶（清单占位场景）。"""
    tea = _get_tea_or_404(db, tea_id)
    return _state(db, tea, user_id)
