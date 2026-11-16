"""内容板块 Repository（批次五 R1–R5）

- 前台查询自动过滤 is_active=0；后台查询带状态筛选
- 只 flush 不 commit，事务由 Service 层控制
- 不在 Repository 做业务判断
"""

from typing import Sequence

from sqlalchemy import asc, desc, func, or_, select

from app.core.database import SessionLocal
from app.models.content import ContentItem, ContentType
from app.repositories._common import escape_like


class ContentRepository:
    def __init__(self, db: SessionLocal):
        self.db = db

    # ===== ContentType =====

    def list_types(self) -> Sequence[ContentType]:
        return (
            self.db.execute(select(ContentType).order_by(asc(ContentType.sort_order)))
            .scalars()
            .all()
        )

    def get_type_by_code(self, code: str) -> ContentType | None:
        return self.db.execute(
            select(ContentType).where(ContentType.code == code)
        ).scalar_one_or_none()

    def get_type_by_id(self, type_id: int) -> ContentType | None:
        return self.db.execute(
            select(ContentType).where(ContentType.id == type_id)
        ).scalar_one_or_none()

    # ===== ContentItem 前台 =====

    def list_public_items(
        self,
        type_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[Sequence[ContentItem], int]:
        """前台列表：只返回 is_active=1；按 sort_order ASC 兜底 created_at DESC。"""
        stmt = select(ContentItem).where(ContentItem.is_active == 1)
        if type_id is not None:
            stmt = stmt.where(ContentItem.type_id == type_id)
        if keyword:
            # 转义 % / _ / \，避免用户输入被解释为通配符（与茶品搜索同一工具）
            pattern = f"%{escape_like(keyword)}%"
            stmt = stmt.where(
                or_(
                    ContentItem.title.like(pattern, escape="\\"),
                    ContentItem.summary.like(pattern, escape="\\"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        items = (
            self.db.execute(
                stmt.order_by(asc(ContentItem.sort_order), desc(ContentItem.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )

        return items, total

    def get_public_item(self, item_id: int) -> ContentItem | None:
        return self.db.execute(
            select(ContentItem).where(ContentItem.id == item_id, ContentItem.is_active == 1)
        ).scalar_one_or_none()

    # ===== ContentItem 后台 =====

    def list_admin_items(
        self,
        type_id: int | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[Sequence[ContentItem], int]:
        """后台列表：含下架条目；可选状态筛选。"""
        stmt = select(ContentItem)
        if type_id is not None:
            stmt = stmt.where(ContentItem.type_id == type_id)
        if is_active is not None:
            stmt = stmt.where(ContentItem.is_active == int(is_active))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        items = (
            self.db.execute(
                stmt.order_by(asc(ContentItem.sort_order), desc(ContentItem.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )

        return items, total

    def get_by_id(self, item_id: int) -> ContentItem | None:
        return self.db.execute(
            select(ContentItem).where(ContentItem.id == item_id)
        ).scalar_one_or_none()

    def add(self, item: ContentItem) -> None:
        self.db.add(item)
        self.db.flush()

    def delete(self, item: ContentItem) -> None:
        self.db.delete(item)
        self.db.flush()
