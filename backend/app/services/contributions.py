"""用户贡献业务层（S10–S13 / API_CONTRACT §4.8）

双层校验：
1. 系统层：表单完整性（Pydantic）、名品-茶类映射、名称相似度查重、字数边界
2. 管理员层：审核队列人工判断，通过 / 拒绝（附理由）

红线：审核动作仅管理员；用户只能查看与删除自己的待审核提交；不物理删除茶品。
"""

from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.orm import Session

from app.core.response import ContributionNotFound, TeaGuideError
from app.models.contribution import Contribution
from app.repositories import admin_repo, contribution_repo, tea_repo
from app.schemas.contribution import (
    STATUS_VALUES,
    TYPE_VALUES,
    ContributionCreateRequest,
    ContributionItem,
    ContributionListResponse,
)
from app.schemas.tea import TeaArticleItem

CATEGORY_LABELS = {
    "green": "绿茶",
    "white": "白茶",
    "yellow": "黄茶",
    "red": "红茶",
    "oolong": "乌龙茶",
    "dark": "黑茶",
    "reprocessed": "再加工茶",
}
TIPS_FIELDS = ("tips_history", "tips_suitable", "tips_misconception", "tips_official_note")
TIPS_FIELD_TO_COLUMN = {
    "tips_history": "history",
    "tips_suitable": "suitable",
    "tips_misconception": "misconception",
    "tips_official_note": "official_note",
}
SIMILARITY_THRESHOLD = 0.9
DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50


def _target_tea_name(db: Session, item: Contribution) -> str | None:
    if item.target_tea_id is None:
        return None
    tea = tea_repo.get_by_id(db, item.target_tea_id, with_tips=False)
    return tea.name if tea else None


def _to_item(db: Session, item: Contribution, username: str | None = None) -> ContributionItem:
    return ContributionItem(
        id=item.id,
        type=item.type,
        status=item.status,
        target_tea_id=item.target_tea_id,
        target_tea_name=_target_tea_name(db, item),
        payload=item.payload or {},
        reject_reason=item.reject_reason,
        reviewer_id=item.reviewer_id,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
        username=username,
    )


def _check_name_category(db: Session, name: str, category: str) -> None:
    """第一层校验：名品-茶类映射 + 名称相似度查重（PRD S10 / 附录 A）。"""
    mapping = contribution_repo.get_map_by_name(db, name)
    if mapping is not None and mapping.category != category:
        expected = CATEGORY_LABELS.get(mapping.category, mapping.category)
        raise TeaGuideError(40000, f"「{name}」属于{expected}，与所选茶类不一致")

    for _tea_id, existing in contribution_repo.list_tea_names(db):
        if SequenceMatcher(None, name, existing).ratio() > SIMILARITY_THRESHOLD:
            raise TeaGuideError(40000, f"茶品名称与已有茶品「{existing}」过于相似")


def submit(db: Session, *, user_id: int, req: ContributionCreateRequest) -> ContributionItem:
    """用户提交新茶或科普投稿，落库为 pending（§4.8.1）。"""
    if req.type == "new_tea":
        assert req.tea is not None  # Schema 已校验
        payload = req.tea.model_dump(mode="json")
        _check_name_category(db, payload["name"], payload["category"])
        item = contribution_repo.create(
            db, user_id=user_id, type="new_tea", target_tea_id=None, payload=payload
        )
    else:
        tea = tea_repo.get_by_id(db, req.target_tea_id, with_tips=False)  # type: ignore[arg-type]
        if tea is None:
            raise TeaGuideError(40000, "目标茶品不存在")
        if not tea.is_active:
            raise TeaGuideError(40000, "目标茶品暂不可用")
        payload = {"title": req.title, "content": req.content}
        item = contribution_repo.create(
            db, user_id=user_id, type="article", target_tea_id=tea.id, payload=payload
        )

    db.commit()
    db.refresh(item)
    return _to_item(db, item)


def list_mine(db: Session, user_id: int) -> list[ContributionItem]:
    """我的提交记录（§4.8.2）：按提交时间倒序。"""
    return [_to_item(db, item) for item in contribution_repo.list_by_user(db, user_id)]


def delete_mine(db: Session, *, user_id: int, contribution_id: int) -> None:
    """删除待审核提交（§4.8.3）：非本人或非 pending 拒绝。"""
    item = contribution_repo.get_by_id(db, contribution_id)
    if item is None or item.user_id != user_id:
        raise ContributionNotFound
    if item.status != "pending":
        raise TeaGuideError(40000, "仅待审核的提交可以删除")
    contribution_repo.delete(db, item)
    db.commit()


def admin_list(
    db: Session,
    *,
    status: str | None,
    type: str | None,
    page: int,
    page_size: int,
) -> ContributionListResponse:
    """审核队列（§4.6.12）：默认 pending，按状态与类型过滤。"""
    status = (status or "pending").strip() or "pending"
    if status not in STATUS_VALUES:
        raise TeaGuideError(40000, "status 取值非法")
    type = (type or "").strip() or None
    if type is not None and type not in TYPE_VALUES:
        raise TeaGuideError(40000, "type 取值非法")

    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    rows, total = contribution_repo.admin_list(
        db,
        status=status,
        type=type,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ContributionListResponse(
        items=[_to_item(db, item, username) for item, username in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def approve(db: Session, *, admin_id: int, contribution_id: int) -> ContributionItem:
    """审核通过（§4.6.13）：new_tea 上架，article 在详情页展示。"""
    item = contribution_repo.get_by_id(db, contribution_id)
    if item is None:
        raise ContributionNotFound
    if item.status != "pending":
        raise TeaGuideError(40000, "该提交已处理，无法重复操作")

    payload: dict[str, Any] = item.payload or {}
    if item.type == "new_tea":
        fields = {k: v for k, v in payload.items() if k not in TIPS_FIELDS}
        tea = admin_repo.create_tea(db, fields)
        tips_values = {
            column: payload[field]
            for field, column in TIPS_FIELD_TO_COLUMN.items()
            if payload.get(field) is not None
        }
        if tips_values:
            admin_repo.create_tips(db, tea.id, tips_values)
        detail = f"通过用户贡献新茶：{tea.name}"
    else:
        detail = f"通过用户科普投稿：{payload.get('title') or '无标题'}"

    item.status = "approved"
    item.reviewer_id = admin_id
    item.reject_reason = None
    item.reviewed_at = datetime.now(timezone.utc)
    db.flush()

    admin_repo.add_operation_log(
        db,
        user_id=admin_id,
        action="approve_contribution",
        target_id=item.id,
        target_type="contribution",
        detail=detail,
    )
    db.commit()
    db.refresh(item)
    return _to_item(db, item)


def reject(db: Session, *, admin_id: int, contribution_id: int, reason: str) -> ContributionItem:
    """审核拒绝（§4.6.14）：记录理由，用户可在我的提交中查看。"""
    item = contribution_repo.get_by_id(db, contribution_id)
    if item is None:
        raise ContributionNotFound
    if item.status != "pending":
        raise TeaGuideError(40000, "该提交已处理，无法重复操作")

    normalized = (reason or "").strip()
    if not normalized:
        raise TeaGuideError(40000, "请填写拒绝理由")

    item.status = "rejected"
    item.reviewer_id = admin_id
    item.reject_reason = normalized
    item.reviewed_at = datetime.now(timezone.utc)
    db.flush()

    admin_repo.add_operation_log(
        db,
        user_id=admin_id,
        action="reject_contribution",
        target_id=item.id,
        target_type="contribution",
        detail=f"拒绝用户提交：{normalized}",
    )
    db.commit()
    db.refresh(item)
    return _to_item(db, item)


def approved_articles(db: Session, tea_id: int) -> list[TeaArticleItem]:
    """茶品详情页展示的已通过科普投稿（S11 / S12）。"""
    return [
        TeaArticleItem(
            id=item.id,
            title=(item.payload or {}).get("title"),
            content=(item.payload or {}).get("content") or "",
            contributor=username,
            created_at=item.created_at,
        )
        for item, username in contribution_repo.list_approved_articles(db, tea_id)
    ]
