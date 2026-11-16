"""收藏路由（API_CONTRACT §4.3 / §4.4）—— 仅声明与参数注入，业务在 services"""

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.favorite import FavoriteAddRequest
from app.services import favorites as favorites_service

router = APIRouter()


@router.post("/{tea_id}")
def add_favorite(
    tea_id: int,
    payload: FavoriteAddRequest | None = Body(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏茶品（§4.3.1）：可选 body {list_id}，缺省归入默认清单"""
    list_id = payload.list_id if payload else None
    data = favorites_service.add_favorite(
        db, user_id=current_user.id, tea_id=tea_id, list_id=list_id
    )
    return ok(data.model_dump())


@router.delete("/{tea_id}")
def remove_favorite(
    tea_id: int,
    list_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消收藏（§4.3.2）：可选 ?list_id，缺省移除所有清单中的该茶"""
    data = favorites_service.remove_favorite(
        db, user_id=current_user.id, tea_id=tea_id, list_id=list_id
    )
    return ok(data.model_dump())


@router.get("/{tea_id}/status")
def favorite_status(
    tea_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询收藏状态（§4.3.3）"""
    data = favorites_service.get_status(db, user_id=current_user.id, tea_id=tea_id)
    return ok(data.model_dump())
