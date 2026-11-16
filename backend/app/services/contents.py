"""内容板块业务层（批次五 R1–R5）

- 前台只读：游客可访问板块分类 + 条目列表 + 详情（仅 is_active=1）
- 管理员 CRUD：创建/更新/软删（is_active=0），与 operation_logs 同事务写入
- meta JSON 校验在 Schema.validate_meta_for_type 执行
"""

from sqlalchemy.orm import Session

from app.core.response import (
    ContentItemNotFound,
    ContentTypeNotFound,
    TeaGuideError,
)
from app.models.content import ContentItem
from app.repositories import admin_repo
from app.repositories.content_repo import ContentRepository
from app.schemas.content import (
    CONTENT_TYPES,
    AdminContentListItem,
    AdminContentListResponse,
    ContentCreateRequest,
    ContentItemOut,
    ContentListResponse,
    ContentTypeOut,
    ContentUpdateRequest,
)

DEFAULT_PAGE_SIZE = 12
MAX_PAGE_SIZE = 50
MAX_KEYWORD_LEN = 100


# === 前台只读 ===


def list_content_types(db: Session) -> list[ContentTypeOut]:
    """板块分类列表（API_CONTRACT §4.2.10）。"""
    repo = ContentRepository(db)
    return [ContentTypeOut.model_validate(t, from_attributes=True) for t in repo.list_types()]


def list_contents(
    db: Session,
    *,
    type_code: str | None,
    keyword: str | None,
    page: int,
    page_size: int,
) -> ContentListResponse:
    """前台内容列表（API_CONTRACT §4.2.11）。

    - type_code 为空则返回所有板块的活跃条目（不推荐但允许）
    - keyword 非空时对 title / summary 模糊匹配（通配符转义在 Repository）
    - 按 sort_order ASC, created_at DESC 排序
    """
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    kw = (keyword or "").strip() or None
    if kw is not None and len(kw) > MAX_KEYWORD_LEN:
        raise TeaGuideError(40000, "keyword 长度不能超过 100 字符")

    repo = ContentRepository(db)

    type_id: int | None = None
    if type_code is not None:
        if type_code not in CONTENT_TYPES:
            raise TeaGuideError(40000, "type 参数取值非法")
        ct = repo.get_type_by_code(type_code)
        if ct is None:
            raise ContentTypeNotFound
        type_id = ct.id

    items, total = repo.list_public_items(
        type_id=type_id, keyword=kw, page=page, page_size=page_size
    )

    return ContentListResponse(
        items=[_to_out(i, type_code) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_content(db: Session, item_id: int) -> ContentItemOut:
    """内容详情（API_CONTRACT §4.2.11 GET /contents/{id}）。"""
    repo = ContentRepository(db)
    item = repo.get_public_item(item_id)
    if item is None:
        raise ContentItemNotFound

    # 附带 type_code 到输出
    ct = repo.get_type_by_id(item.type_id)
    return _to_out(item, ct.code if ct else "")


def _to_out(item: ContentItem, type_code: str) -> ContentItemOut:
    """ORM → 前台 DTO。"""
    out = ContentItemOut.model_validate(item, from_attributes=True)
    out.type_code = type_code
    # is_active 仅后台详情有意义；item 是后台查询结果时它是 int
    out.is_active = None
    return out


def _to_admin_out(item: ContentItem, type_code: str) -> ContentItemOut:
    """ORM → 后台 DTO（含 is_active）。"""
    out = _to_out(item, type_code)
    out.is_active = bool(item.is_active)
    return out


# === 管理员 CRUD ===


def admin_list_contents(
    db: Session,
    *,
    type_code: str | None,
    is_active: bool | None,
    page: int,
    page_size: int,
) -> AdminContentListResponse:
    """后台列表（含下架；API_CONTRACT §4.6.12）。"""
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    repo = ContentRepository(db)

    type_id: int | None = None
    if type_code is not None:
        if type_code not in CONTENT_TYPES:
            raise TeaGuideError(40000, "type 参数取值非法")
        ct = repo.get_type_by_code(type_code)
        if ct is None:
            raise ContentTypeNotFound
        type_id = ct.id

    items, total = repo.list_admin_items(
        type_id=type_id, is_active=is_active, page=page, page_size=page_size
    )

    # 批量获取 type_code 映射
    type_map = {t.id: t.code for t in repo.list_types()}

    return AdminContentListResponse(
        items=[
            AdminContentListItem(
                id=i.id,
                type_code=type_map.get(i.type_id, ""),
                title=i.title,
                summary=i.summary,
                is_active=bool(i.is_active),
                sort_order=i.sort_order,
                created_at=i.created_at,
                updated_at=i.updated_at,
            )
            for i in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def admin_create_content(
    db: Session, *, admin_id: int, req: ContentCreateRequest
) -> ContentItemOut:
    """管理员创建条目（API_CONTRACT §4.6.12 POST）。"""
    repo = ContentRepository(db)

    # 校验板块存在
    ct = repo.get_type_by_code(req.type_code)
    if ct is None:
        raise ContentTypeNotFound

    # meta 按板块校验已在 Schema model_validator 中自动执行

    item = ContentItem(
        type_id=ct.id,
        title=req.title,
        summary=req.summary,
        body=req.body,
        cover_image=req.cover_image,
        meta=req.meta,
        sort_order=req.sort_order,
        is_active=1,
    )
    repo.add(item)
    admin_repo.add_operation_log(
        db,
        user_id=admin_id,
        action="create_content",
        target_type="content_item",
        target_id=item.id,
        detail=f"[{ct.code}] {req.title}",
    )
    db.commit()
    db.refresh(item)
    return _to_admin_out(item, ct.code)


def admin_update_content(
    db: Session,
    *,
    admin_id: int,
    item_id: int,
    req: ContentUpdateRequest,
) -> ContentItemOut:
    """管理员更新条目（全量替换；API_CONTRACT §4.6.13 PUT）。"""
    repo = ContentRepository(db)
    item = repo.get_by_id(item_id)
    if item is None:
        raise ContentItemNotFound

    update_data = req.model_dump(exclude_unset=True)
    # 如果 meta 在请求中，按 item 当前 type_code 校验
    if "meta" in update_data and update_data["meta"] is not None:
        ct = repo.get_type_by_id(item.type_id)
        if ct is None:
            raise ContentTypeNotFound
        from app.schemas.content import _validate_meta

        update_data["meta"] = _validate_meta(update_data["meta"], ct.code)

    for key, value in update_data.items():
        # is_active 从 bool 转 tinyint
        if key == "is_active":
            setattr(item, key, 1 if value else 0)
        else:
            setattr(item, key, value)
    db.flush()

    ct = repo.get_type_by_id(item.type_id)
    admin_repo.add_operation_log(
        db,
        user_id=admin_id,
        action="update_content",
        target_type="content_item",
        target_id=item.id,
        detail=f"[{ct.code if ct else '?'}] {item.title}",
    )
    db.commit()
    db.refresh(item)
    return _to_admin_out(item, ct.code if ct else "")


def admin_get_content(db: Session, *, item_id: int) -> ContentItemOut:
    """后台详情（编辑回填用；软删条目也能访问）。"""
    repo = ContentRepository(db)
    item = repo.get_by_id(item_id)
    if item is None:
        raise ContentItemNotFound
    ct = repo.get_type_by_id(item.type_id)
    return _to_admin_out(item, ct.code if ct else "")


def admin_delete_content(db: Session, *, admin_id: int, item_id: int) -> None:
    """软删除：is_active=0（API_CONTRACT §4.6.13 DELETE）。

    - 不物理删除；operation_logs 记录操作
    """
    repo = ContentRepository(db)
    item = repo.get_by_id(item_id)
    if item is None:
        raise ContentItemNotFound

    item.is_active = 0
    db.flush()

    ct = repo.get_type_by_id(item.type_id)
    admin_repo.add_operation_log(
        db,
        user_id=admin_id,
        action="delete_content",
        target_type="content_item",
        target_id=item.id,
        detail=f"[{ct.code if ct else '?'}] {item.title}",
    )
    db.commit()
