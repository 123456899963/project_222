"""我的模块服务：头像设置（ADR-0004）

两个通道共用 users.avatar_url：
- 上传：复用 upload.save_image 的魔数/大小校验，落盘 /uploads/
- 预置：仅接受白名单预设，映射到前端静态资源 /avatars/tea-0X.svg
"""

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.response import InternalError, TeaGuideError
from app.models.user import User
from app.repositories import user_repo
from app.services.upload import save_image

# 与 frontend/public/avatars/tea-0X.svg 一一对应
AVATAR_PRESETS: tuple[str, ...] = tuple(f"tea-0{i}" for i in range(1, 9))


def preset_url(preset: str) -> str:
    """校验预置头像编号并返回静态地址；非法值抛 400。"""
    if preset not in AVATAR_PRESETS:
        raise TeaGuideError(40000, "头像不在可选范围内")
    return f"/avatars/{preset}.svg"


async def update_by_upload(db: Session, user: User, file: UploadFile) -> User:
    """上传图片并设为头像；返回更新后的用户。"""
    result = await save_image(file)
    updated = user_repo.update_avatar(db, user.id, result["url"])
    if updated is None:  # 理论上不可达：user 来自已鉴权会话
        raise InternalError
    user_repo.add_avatar_log(db, user.id, f"上传头像 {result['url']}")
    db.commit()
    return updated


def update_by_preset(db: Session, user: User, preset: str) -> User:
    """选择预置头像；返回更新后的用户。"""
    url = preset_url(preset)
    updated = user_repo.update_avatar(db, user.id, url)
    if updated is None:  # 理论上不可达：user 来自已鉴权会话
        raise InternalError
    user_repo.add_avatar_log(db, user.id, f"选择预置头像 {preset}")
    db.commit()
    return updated
