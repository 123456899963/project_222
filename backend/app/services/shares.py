"""分享业务层（PRD FR-5.4 ~ FR-5.6 / API_CONTRACT §4.5）

- 令牌 8 位 URL-safe、大小写敏感、全局唯一、无过期
- 已有生效令牌复用；撤销软失效且不可复活
- 公开页不返回笔记与所有者身份
- 一键收藏跳过已收藏/下架，返回 added / skipped / total
"""

import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.response import (
    InternalError,
    ShareAlreadyRevoked,
    ShareNotFound,
    UserForbidden,
)
from app.repositories import favorite_repo, list_repo, share_repo, tea_repo
from app.schemas.share import (
    CopyResult,
    ShareGenerateData,
    ShareRevokeData,
    ShareViewData,
    ShareViewItem,
)
from app.services import lists as lists_service

TOKEN_BYTES = 6  # token_urlsafe(6) → 8 位 URL-safe 字符
TOKEN_MAX_ATTEMPTS = 5


def _new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def generate(db: Session, user_id: int, list_id: int | None = None) -> ShareGenerateData:
    """生成或复用分享令牌（并发下同一清单仅一条生效令牌）。"""
    target = lists_service.resolve_list(db, user_id, list_id)

    # 行锁串行化同一清单的并发生成，避免产生多条 is_active=1
    list_obj = list_repo.get_by_id_for_update(db, target.id)
    if list_obj is None:  # pragma: no cover - resolve_list 已保证存在
        raise ShareNotFound

    existing = share_repo.get_active_by_list(db, list_obj.id, for_update=True)
    if existing:
        db.commit()  # 释放行锁
        return ShareGenerateData(
            token=existing.token,
            url=f"/c/{existing.token}",
            created_at=existing.created_at,
            is_new=False,
        )

    for _ in range(TOKEN_MAX_ATTEMPTS):
        token = _new_token()
        try:
            item = share_repo.create(db, list_obj.id, token)
            db.commit()
            db.refresh(item)
            return ShareGenerateData(
                token=item.token,
                url=f"/c/{item.token}",
                created_at=item.created_at,
                is_new=True,
            )
        except IntegrityError:
            # token 全局唯一冲突（概率极低）：回滚后重试
            db.rollback()
            list_obj = list_repo.get_by_id_for_update(db, target.id)
            if list_obj is None:  # pragma: no cover
                raise ShareNotFound
            existing = share_repo.get_active_by_list(db, list_obj.id, for_update=True)
            if existing:
                db.commit()
                return ShareGenerateData(
                    token=existing.token,
                    url=f"/c/{existing.token}",
                    created_at=existing.created_at,
                    is_new=False,
                )

    raise InternalError


def revoke(db: Session, *, user_id: int, token: str) -> ShareRevokeData:
    item = share_repo.get_by_token(db, token)
    if item is None:
        raise ShareNotFound

    list_obj = list_repo.get_by_id(db, item.list_id)
    if list_obj is None:  # pragma: no cover
        raise ShareNotFound
    if list_obj.user_id != user_id:
        raise UserForbidden
    if not item.is_active:
        raise ShareAlreadyRevoked

    item = share_repo.revoke(db, item)
    return ShareRevokeData(
        token=item.token,
        is_active=False,
        revoked_at=item.revoked_at,
    )


def view(db: Session, *, token: str, viewer_id: int | None) -> ShareViewData:
    item = share_repo.get_by_token(db, token)
    if item is None:
        raise ShareNotFound

    list_obj = list_repo.get_by_id(db, item.list_id)
    if list_obj is None:  # pragma: no cover
        raise ShareNotFound

    is_owner = viewer_id is not None and list_obj.user_id == viewer_id

    if not item.is_active:
        return ShareViewData(
            token=item.token,
            title=list_obj.title,
            tea_count=0,
            created_at=item.created_at,
            revoked=True,
            is_owner=is_owner,
            items=[],
        )

    rows = list_repo.list_items(db, list_obj.id)
    items = [
        ShareViewItem(
            tea_id=tea.id,
            name=tea.name,
            category=tea.category,
            origin=tea.origin,
            season=tea.season,
            main_image_url=tea.main_image_url,
            favorite_count=int(tea.favorite_count or 0),
            is_available=bool(tea.is_active),
        )
        for _fav, tea in rows
    ]
    return ShareViewData(
        token=item.token,
        title=list_obj.title,
        tea_count=len(items),
        created_at=item.created_at,
        revoked=False,
        is_owner=is_owner,
        items=items,
    )


def copy_all(db: Session, *, token: str, user_id: int) -> CopyResult:
    """一键收藏全部：跳过已收藏与下架茶，返回 added / skipped / total。"""
    item = share_repo.get_by_token(db, token)
    if item is None:
        raise ShareNotFound
    if not item.is_active:
        raise ShareAlreadyRevoked

    source_list = list_repo.get_by_id(db, item.list_id)
    if source_list is None:  # pragma: no cover
        raise ShareNotFound
    if source_list.user_id == user_id:
        raise UserForbidden

    rows = list_repo.list_items(db, source_list.id)
    total = len(rows)

    lists_service.get_or_create_default_list(db, user_id)
    # 串行化同一用户的并发 copy，锁内使用当前读获取已收藏集合（跨清单去重）
    default_list = list_repo.get_default_for_update(db, user_id)
    if default_list is None:  # pragma: no cover - get_or_create 已保证存在
        raise ShareNotFound
    existing_ids = favorite_repo.list_tea_ids(db, user_id, for_update=True)

    added = 0
    skipped = 0
    # 按 id 升序锁定待插入茶品，统一加锁顺序，避免多用户并发 copy 死锁
    tea_repo.lock_by_ids(
        db,
        [tea.id for _fav, tea in rows if tea.is_active and tea.id not in existing_ids],
    )
    for _fav, tea in rows:
        if not tea.is_active or tea.id in existing_ids:
            skipped += 1
            continue

        savepoint = db.begin_nested()
        try:
            favorite_repo.create_favorite(db, user_id, tea.id, default_list.id)
            favorite_repo.increment_favorite_count(db, tea.id)
            savepoint.commit()
            added += 1
            existing_ids.add(tea.id)
        except IntegrityError:
            # 并发下另一请求已插入：回滚到保存点，计入 skipped
            savepoint.rollback()
            skipped += 1

    db.commit()
    return CopyResult(added=added, skipped=skipped, total=total)
