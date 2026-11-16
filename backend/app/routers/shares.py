"""分享路由（API_CONTRACT §4.5）"""

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user, get_optional_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.share import ShareGenerateRequest
from app.services import shares as shares_service

router = APIRouter()


@router.post("/generate")
def generate(
    payload: ShareGenerateRequest | None = Body(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成/复用分享链接（§4.5.1）：可选 body {list_id}，缺省分享默认清单"""
    list_id = payload.list_id if payload else None
    data = shares_service.generate(db, current_user.id, list_id)
    return ok(data.model_dump())


@router.post("/revoke/{token}")
def revoke(
    token: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销分享（§4.5.2）"""
    data = shares_service.revoke(db, user_id=current_user.id, token=token)
    return ok(data.model_dump())


@router.get("/{token}")
def view(
    token: str,
    viewer=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """公开查看分享清单（§4.5.3，游客/登录用户均可）"""
    data = shares_service.view(db, token=token, viewer_id=viewer.id if viewer else None)
    return ok(data.model_dump())


@router.post("/{token}/copy")
def copy_all(
    token: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一键收藏全部（§4.5.4）"""
    data = shares_service.copy_all(db, token=token, user_id=current_user.id)
    return ok(data.model_dump())
