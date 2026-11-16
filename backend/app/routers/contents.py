"""内容板块前台端点（批次五 R1–R5 / API_CONTRACT §4.2.10–11）

- 3 个端点全部游客只读，无需认证
- 统一响应体 {code, message, data}
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.content import (
    ContentItemOut,
    ContentListResponse,
    ContentTypeOut,
)
from app.services import contents

router = APIRouter()


@router.get("/content-types", response_model=dict)
def list_content_types(db: Session = Depends(get_db)) -> dict:
    """板块分类列表（API_CONTRACT §4.2.10）。"""
    result: list[ContentTypeOut] = contents.list_content_types(db)
    return ok([item.model_dump() for item in result])


@router.get("/contents", response_model=dict)
def list_contents(
    type: str | None = Query(
        None, description="板块 code（teaware/origin/culture/brand/knowledge）"
    ),
    keyword: str | None = Query(None, description="关键词（title/summary 模糊匹配，≤100 字符）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=50, description="每页条数"),
    db: Session = Depends(get_db),
) -> dict:
    """前台内容列表（API_CONTRACT §4.2.11 GET /contents）。"""
    result: ContentListResponse = contents.list_contents(
        db, type_code=type, keyword=keyword, page=page, page_size=page_size
    )
    return ok(result.model_dump())


@router.get("/contents/{item_id}", response_model=dict)
def get_content(
    item_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """内容详情（API_CONTRACT §4.2.11 GET /contents/{id}）。"""
    result: ContentItemOut = contents.get_content(db, item_id)
    return ok(result.model_dump())
