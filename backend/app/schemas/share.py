"""分享相关 Schema（API_CONTRACT §2.6 / §4.5）"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas._common import iso_z


class ShareGenerateRequest(BaseModel):
    """生成分享请求体（可选）：不传 list_id 时分享默认清单。"""

    model_config = ConfigDict(extra="forbid")

    list_id: int | None = None


class ShareGenerateData(BaseModel):
    token: str
    url: str
    created_at: datetime
    is_new: bool

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return iso_z(v)


class ShareRevokeData(BaseModel):
    token: str
    is_active: bool
    revoked_at: datetime

    @field_serializer("revoked_at")
    def serialize_revoked_at(self, v: datetime) -> str:
        return iso_z(v)


class ShareViewItem(BaseModel):
    """公开可见条目：绝不含 tasting_note。"""

    tea_id: int
    name: str
    category: str
    origin: str
    season: str | None = None
    main_image_url: str | None = None
    favorite_count: int = 0
    is_available: bool = True


class ShareViewData(BaseModel):
    token: str
    title: str
    tea_count: int
    created_at: datetime
    revoked: bool
    is_owner: bool = False
    items: list[ShareViewItem]

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return iso_z(v)


class CopyResult(BaseModel):
    added: int
    skipped: int
    total: int
