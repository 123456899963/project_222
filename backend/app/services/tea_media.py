"""茶品图片集业务层（ADR-0003 S4 / PRD S4）

- 公开查询：茶品不存在 40400，已下架 40401（与详情一致）
- 管理写入：单茶上限 9 张；删除为物理删除（ADR-0003 §6）
- 写入与 operation_logs 同事务（S-28）
"""

from sqlalchemy.orm import Session

from app.core.response import TeaGuideError, TeaNotFound, TeaOffShelf
from app.repositories import admin_repo, tea_media_repo, tea_repo
from app.schemas.tea import TeaMediaCreateRequest, TeaMediaItem

MAX_IMAGES_PER_TEA = 9


def list_images(db: Session, tea_id: int) -> list[TeaMediaItem]:
    """公开图片集（IR-4.2.7）：仅上架茶品可见。"""
    tea = tea_repo.get_by_id(db, tea_id, with_tips=False)
    if tea is None:
        raise TeaNotFound
    if not tea.is_active:
        raise TeaOffShelf
    return [TeaMediaItem.model_validate(row) for row in tea_media_repo.list_by_tea(db, tea_id)]


def add_image(
    db: Session, *, admin_id: int, tea_id: int, req: TeaMediaCreateRequest
) -> TeaMediaItem:
    """管理员追加图片（上限 9 张，超出 40000）。"""
    tea = tea_repo.get_by_id(db, tea_id, with_tips=False)
    if tea is None:
        raise TeaNotFound
    if tea_media_repo.count_by_tea(db, tea_id) >= MAX_IMAGES_PER_TEA:
        raise TeaGuideError(40000, f"图片集最多 {MAX_IMAGES_PER_TEA} 张")

    sort_order = (
        req.sort_order if req.sort_order is not None else tea_media_repo.next_sort_order(db, tea_id)
    )
    try:
        row = tea_media_repo.create(
            db, tea_id=tea_id, image_url=req.image_url, sort_order=sort_order
        )
        admin_repo.add_operation_log(
            db,
            user_id=admin_id,
            action="add_tea_media",
            target_id=tea_id,
            detail=req.image_url,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(row)
    return TeaMediaItem.model_validate(row)


def delete_image(db: Session, *, admin_id: int, tea_id: int, image_id: int) -> None:
    """管理员删除图片（物理删除，ADR-0003 §6）。"""
    tea = tea_repo.get_by_id(db, tea_id, with_tips=False)
    if tea is None:
        raise TeaNotFound
    row = tea_media_repo.get_by_id(db, image_id)
    if row is None or row.tea_id != tea_id:
        raise TeaGuideError(40400, "图片不存在")

    image_url = row.image_url
    try:
        tea_media_repo.delete(db, row)
        admin_repo.add_operation_log(
            db,
            user_id=admin_id,
            action="delete_tea_media",
            target_id=tea_id,
            detail=image_url,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
