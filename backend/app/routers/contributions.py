"""用户贡献路由（S10–S13 / API_CONTRACT §4.8）

仅登录用户可用；所有校验与事务在 Service 层。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.contribution import ContributionCreateRequest
from app.services import contributions as contribution_service

router = APIRouter()


@router.post("")
def submit_contribution(
    payload: ContributionCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交新茶 / 科普投稿（§4.8.1）：落库为待审核。"""
    data = contribution_service.submit(db, user_id=current_user.id, req=payload)
    return ok(data.model_dump())


@router.get("/mine")
def list_my_contributions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的提交记录（§4.8.2）：含状态与拒绝理由。"""
    data = contribution_service.list_mine(db, current_user.id)
    return ok([item.model_dump() for item in data])


@router.delete("/{contribution_id}")
def delete_my_contribution(
    contribution_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除待审核提交（§4.8.3）：仅本人且仅 pending。"""
    contribution_service.delete_mine(db, user_id=current_user.id, contribution_id=contribution_id)
    return ok(None, "提交已删除")
