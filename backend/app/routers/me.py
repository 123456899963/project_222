"""我的模块路由（S15 / ADR-0004 / API_CONTRACT §4.7）"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.auth import AvatarPresetRequest, UserResponse
from app.services import me as me_service
from app.services import stats as stats_service

router = APIRouter()


@router.get("/stats")
def get_my_stats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户统计与等级（§4.7.1）。需登录。"""
    data = stats_service.get_stats(db, current_user.id)
    return ok(data.model_dump())


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传本地图片设为头像（§4.7.2）。需登录；JPEG/PNG/WebP ≤5MB。"""
    user = await me_service.update_by_upload(db, current_user, file)
    return ok(UserResponse.model_validate(user).model_dump(mode="json"))


@router.put("/avatar")
def set_preset_avatar(
    payload: AvatarPresetRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """选择预置头像（§4.7.3）。需登录；preset 取值白名单 tea-01～tea-08。"""
    user = me_service.update_by_preset(db, current_user, payload.preset)
    return ok(UserResponse.model_validate(user).model_dump(mode="json"))
