"""认证路由：注册、登录、退出、当前用户、用户名可用性

对齐 API_CONTRACT §4.1：
- 成功响应 data 为 User（id/username/role/created_at）
- 注册/登录成功 Set-Cookie: tea_session（30 天，HttpOnly，SameSite=Lax）
- 不使用 Token / Authorization 头（API_CONTRACT §1.5）
"""

import re

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_user, get_optional_user
from app.core.config import settings
from app.core.database import get_db
from app.core.response import ValidationError, ok
from app.core.security import create_session_token
from app.repositories import user_repo
from app.schemas.auth import (
    USERNAME_PATTERN,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UsernameAvailabilityResponse,
    UserResponse,
)
from app.services import auth as auth_service

router = APIRouter()

# Cookie 通用属性（API_CONTRACT §1.5 / SECURITY S-07）
_COOKIE_MAX_AGE = settings.SESSION_EXPIRE_DAYS * 86400


def _cookie_kwargs() -> dict:
    """每次下发时读取配置，便于部署切换 COOKIE_SECURE 与测试覆盖。"""
    return dict(
        key="tea_session",
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
        # HTTPS 部署启用 Secure；纯 HTTP 演示需显式设 COOKIE_SECURE=false
        secure=settings.cookie_secure,
    )


def _set_session_cookie(response: Response, user) -> None:
    token = create_session_token(user.id, user.session_version)
    response.set_cookie(value=token, **_cookie_kwargs())


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key="tea_session",
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def _user_to_dict(user) -> dict:
    """User ORM → 契约 User 字典（显式字段，永不返回 password_hash）。"""
    return UserResponse.model_validate(user).model_dump(mode="json")


@router.get("/username-availability")
def username_availability(
    username: str = Query(..., min_length=3, max_length=20),
    db: Session = Depends(get_db),
):
    """用户名可用性查询（API_CONTRACT §4.1.1）。游客可调用。"""
    trimmed = username.strip()
    # 服务端正则兜底（Query 只卡长度），复用 Schema 中的同一条规则
    if not re.match(USERNAME_PATTERN, trimmed):
        raise ValidationError
    existing = user_repo.get_by_username(db, trimmed)
    return ok(
        UsernameAvailabilityResponse(username=trimmed, available=existing is None).model_dump()
    )


@router.post("/register")
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """注册 → 自动登录 → Set-Cookie（PRD FR-4.1 / API_CONTRACT §4.1.2）。"""
    username = req.username.strip()
    user = auth_service.register(db, username, req.password)
    _set_session_cookie(response, user)
    return ok(_user_to_dict(user))


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """登录 → Set-Cookie（API_CONTRACT §4.1.3）。

    S14：按「用户名 + IP」双维度统计失败次数，达到阈值返回 42900。
    """
    username = req.username.strip()
    ip = request.client.host if request.client else "unknown"
    user = auth_service.login(db, username, req.password, ip=ip)
    _set_session_cookie(response, user)
    return ok(_user_to_dict(user))


@router.post("/logout")
def logout(
    response: Response,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """退出登录（API_CONTRACT §4.1.4）。

    有效会话时递增 session_version 吊销该用户全部旧 Cookie（SECURITY S-10）；
    未登录/无效 Cookie 仅清 Cookie，接口保持幂等。
    """
    auth_service.logout(db, current_user)
    _clear_session_cookie(response)
    return ok()


@router.put("/password")
def change_password(
    req: ChangePasswordRequest,
    response: Response,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码（API_CONTRACT §4.1.6）。

    成功后递增 session_version，旧 Cookie 全部失效，并清除当前 Cookie 要求重新登录。
    """
    auth_service.change_password(db, current_user, req.old_password, req.new_password)
    _clear_session_cookie(response)
    return ok()


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    """当前用户信息（API_CONTRACT §4.1.5）。需登录。"""
    return ok(_user_to_dict(current_user))
