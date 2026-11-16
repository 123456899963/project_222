"""内容板块 Schema（批次五 R1–R5 / API_CONTRACT §4.2.10–11 + §4.6.12）

- 5 板块统一两表承载；各板块特有字段放在 meta JSON
- meta 字段根据板块类型做差异化校验（teaware/origin/culture/brand/knowledge）
- 管理员写操作 extra='forbid' 防止伪造 is_active / type_id 等
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.schemas._common import iso_z

# 5 板块 code 常量
CONTENT_TYPES = ("teaware", "origin", "culture", "brand", "knowledge")
ContentTypeCode = Literal["teaware", "origin", "culture", "brand", "knowledge"]

TITLE_MAX = 200
SUMMARY_MAX = 500
BODY_MAX = 20000
IMAGE_URL_MAX = 500
META_MAX_KEYS = 20  # meta JSON 最多字段数，防止塞入垃圾


# === Meta 校验辅助 ===


def _validate_meta(meta: dict | None, code: ContentTypeCode) -> dict | None:
    """按板块 code 校验 meta JSON 结构。

    - teaware: material(选填 str), volume(选填 str), category(选填 str)
    - origin: province(选填 str), region(选填 str)
    - culture: era(选填 str), tags(选填 list[str])
    - brand: founded(选填 int), brand_origin(选填 str), website(选填 str)
    - knowledge: subtype(选填 'standard'|'brewing'), difficulty(选填 'beginner'|'intermediate'|'advanced')
    """
    if meta is None:
        return None
    if not isinstance(meta, dict):
        raise ValueError("meta 必须是对象")
    if len(meta) > META_MAX_KEYS:
        raise ValueError(f"meta 最多 {META_MAX_KEYS} 个字段")

    allowed = {
        "teaware": {"material", "volume", "category"},
        "origin": {"province", "region"},
        "culture": {"era", "tags"},
        "brand": {"founded", "brand_origin", "website"},
        "knowledge": {"subtype", "difficulty"},
    }[code]

    # 禁止未定义的 key
    extra = set(meta.keys()) - allowed
    if extra:
        raise ValueError(f"meta 中存在未定义字段: {extra}")

    # culture.tags 必须是字符串数组
    if code == "culture" and "tags" in meta:
        tags = meta["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ValueError("meta.tags 必须是字符串数组")

    # knowledge.subtype / difficulty 枚举校验
    if code == "knowledge":
        if "subtype" in meta and meta["subtype"] not in ("standard", "brewing"):
            raise ValueError("meta.subtype 必须是 'standard' 或 'brewing'")
        if "difficulty" in meta and meta["difficulty"] not in (
            "beginner",
            "intermediate",
            "advanced",
        ):
            raise ValueError("meta.difficulty 必须是 'beginner'/'intermediate'/'advanced' 之一")

    # brand.website URL 校验（非空才校验）
    if code == "brand" and "website" in meta and meta["website"]:
        w = meta["website"]
        if not isinstance(w, str) or not (w.startswith("http://") or w.startswith("https://")):
            raise ValueError("meta.website 必须以 http(s):// 开头")

    return meta


# === 前台输出 ===


class ContentTypeOut(BaseModel):
    """板块分类（API_CONTRACT §4.2.10）。"""

    id: int
    code: str
    name: str
    icon: str | None = None
    description: str | None = None
    sort_order: int


class ContentItemOut(BaseModel):
    """内容条目（前台列表/详情共用）。"""

    id: int
    type_id: int
    type_code: str = ""  # 运行时由 _to_out 补充，非 ORM 列
    title: str
    summary: str | None = None
    body: str | None = None
    cover_image: str | None = None
    meta: dict[str, Any] | None = None
    sort_order: int
    is_active: bool | None = None  # 后台返回（前台详情不含）
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, v: datetime) -> str:
        return iso_z(v)


class ContentListResponse(BaseModel):
    """分页响应（API_CONTRACT §1.6）。"""

    items: list[ContentItemOut]
    total: int
    page: int
    page_size: int


# === 管理员输入 ===


class ContentCreateRequest(BaseModel):
    """管理员创建条目（API_CONTRACT §4.6.12）。"""

    model_config = ConfigDict(extra="forbid")

    type_code: ContentTypeCode
    title: str = Field(..., max_length=TITLE_MAX)
    summary: str | None = Field(None, max_length=SUMMARY_MAX)
    body: str | None = Field(None, max_length=BODY_MAX)
    cover_image: str | None = Field(None, max_length=IMAGE_URL_MAX)
    meta: dict[str, Any] | None = None
    sort_order: int = Field(default=0, ge=-9999, le=9999)

    @field_validator("title", "summary", "body", mode="before")
    @classmethod
    def _normalize_text(cls, v: Any) -> Any:
        if v is None:
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title 不能为空")
        return v

    @field_validator("cover_image")
    @classmethod
    def _validate_image_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("/uploads/")):
            raise ValueError("cover_image 必须为 http(s):// 或 /uploads/ 路径")
        return v

    @model_validator(mode="after")
    def _validate_meta_for_type(self) -> "ContentCreateRequest":
        """按板块校验 meta —— Pydantic 自动在构造时执行，ValueError → ValidationError → 422 → 400。"""
        self.meta = _validate_meta(self.meta, self.type_code)
        return self


class ContentUpdateRequest(BaseModel):
    """管理员更新条目（全量替换；API_CONTRACT §4.6.13）。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, max_length=TITLE_MAX)
    summary: str | None = Field(None, max_length=SUMMARY_MAX)
    body: str | None = Field(None, max_length=BODY_MAX)
    cover_image: str | None = Field(None, max_length=IMAGE_URL_MAX)
    meta: dict[str, Any] | None = None
    sort_order: int | None = Field(None, ge=-9999, le=9999)
    is_active: bool | None = None

    @field_validator("title", "summary", "body", mode="before")
    @classmethod
    def _normalize_text(cls, v: Any) -> Any:
        if v is None:
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("cover_image")
    @classmethod
    def _validate_image_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("/uploads/")):
            raise ValueError("cover_image 必须为 http(s):// 或 /uploads/ 路径")
        return v


class AdminContentListItem(BaseModel):
    """后台列表（含下架；API_CONTRACT §4.6.12）。"""

    id: int
    type_code: str
    title: str
    summary: str | None = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, v: datetime) -> str:
        return iso_z(v)


class AdminContentListResponse(BaseModel):
    """后台分页响应。"""

    items: list[AdminContentListItem]
    total: int
    page: int
    page_size: int
