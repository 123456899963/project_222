"""认证相关 Schema（请求/响应 DTO）

对齐 API_CONTRACT §4.1 与 SECURITY S-19/S-20：
- 用户名 3-20 字符，仅中文/英文/数字
- 密码 6-64 字符
- 响应 User 仅含 id/username/role/created_at，永不返回 password_hash
- 所有请求 DTO extra='forbid'，防止批量赋值
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 用户名正则：3-20 字符，中文/英文/数字（API_CONTRACT §4.1.1）
USERNAME_PATTERN = r"^[A-Za-z0-9\u4e00-\u9fa5]{3,20}$"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=USERNAME_PATTERN,
        description="用户名 3-20 字符，中文/英文/数字",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=64,
        description="密码 6-64 字符",
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=64)


class ChangePasswordRequest(BaseModel):
    """修改密码（API_CONTRACT §4.1.6）；新旧密码规则与注册一致。"""

    model_config = ConfigDict(extra="forbid")

    old_password: str = Field(..., min_length=1, max_length=64, description="当前密码")
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=64,
        description="新密码 6-64 字符，规则与注册一致",
    )


class UserResponse(BaseModel):
    """当前用户信息（API_CONTRACT §2.1 User）。不含 password_hash。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Literal["user", "admin"]
    avatar_url: str | None = None
    created_at: datetime


class UsernameAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    available: bool


class AvatarPresetRequest(BaseModel):
    """选择预置头像（ADR-0004）；取值范围由 Service 白名单二次校验。"""

    model_config = ConfigDict(extra="forbid")

    preset: str = Field(..., min_length=1, max_length=32)
