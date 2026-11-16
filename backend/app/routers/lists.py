"""清单与品鉴笔记路由（API_CONTRACT §4.4，S9 多清单）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.list import ListCreateRequest, NoteUpdateRequest, TitleUpdateRequest
from app.services import lists as lists_service

router = APIRouter()


@router.get("")
def list_my_lists(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取我的全部清单摘要（§4.4.1）"""
    data = lists_service.list_summaries(db, current_user.id)
    return ok([item.model_dump() for item in data])


@router.post("")
def create_list(
    payload: ListCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新建清单（§4.4.2，最多 10 个）"""
    data = lists_service.create_list(db, current_user.id, payload.title)
    return ok(data.model_dump())


@router.get("/{list_id}")
def get_list_detail(
    list_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取清单详情（§4.4.3）"""
    data = lists_service.get_list_detail(db, current_user.id, list_id)
    return ok(data.model_dump())


@router.put("/{list_id}")
def update_title(
    list_id: int,
    payload: TitleUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新清单标题（§4.4.4）"""
    data = lists_service.update_title(db, current_user.id, list_id, payload.title)
    return ok(data.model_dump())


@router.delete("/{list_id}")
def delete_list(
    list_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除清单（§4.4.5）：条目迁入默认清单，默认清单不可删除"""
    lists_service.delete_list(db, current_user.id, list_id)
    return ok(None, "清单已删除")


@router.put("/{list_id}/notes/{tea_id}")
def save_note(
    list_id: int,
    tea_id: int,
    payload: NoteUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存/清空品鉴笔记（§4.4.6）"""
    data = lists_service.save_note(
        db, user_id=current_user.id, list_id=list_id, tea_id=tea_id, content=payload.content
    )
    return ok(data.model_dump())
