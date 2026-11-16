"""用户贡献 Schema（S10–S13 / API_CONTRACT §4.8）

- 提交仅接受结构化字段，extra='forbid' 防止伪造 status / reviewer 等
- new_tea 主体校验与管理员新增保持一致，但主图不是强制项（X7 不开放图片投稿）
- article 内容 3–500 字，目标茶品必须已上架
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
from app.schemas.tea import (
    CategoryValue,
    FermentationValue,
    SeasonValue,
    _normalize_optional_text,
    _normalize_required_text,
    _one_decimal,
)

ContributionType = Literal["new_tea", "article"]
ContributionStatus = Literal["pending", "approved", "rejected"]

TYPE_VALUES = ("new_tea", "article")
STATUS_VALUES = ("pending", "approved", "rejected")
REJECT_REASON_PRESETS = (
    "信息不完整",
    "茶类矛盾",
    "重复提交",
    "疑似广告",
    "其他原因",
)
TITLE_MAX_LEN = 50
CONTENT_MIN_LEN = 3
CONTENT_MAX_LEN = 500
REASON_MAX_LEN = 200


class ContributionTeaPayload(BaseModel):
    """用户提交的新茶字段（与管理员新增结构一致，主图选填）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100)
    category: CategoryValue
    origin: str = Field(..., max_length=200)
    season: SeasonValue | None = None
    fermentation: FermentationValue | None = None
    price_range: str | None = Field(None, max_length=32)
    representative_variety: str | None = Field(None, max_length=100)

    shape_desc: str
    soup_desc: str
    aroma_desc: str
    taste_desc: str

    water_temp: float = Field(..., ge=70.0, le=100.0)
    tea_amount: float = Field(..., gt=0, le=999.9)
    brew_time: float = Field(..., gt=0, le=999.9)

    main_image_url: str | None = Field(None, max_length=500)

    tips_history: str | None = None
    tips_suitable: str | None = None
    tips_misconception: str | None = None
    tips_official_note: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: Any) -> Any:
        return _normalize_required_text(value, "name")

    @field_validator("origin", mode="before")
    @classmethod
    def _validate_origin(cls, value: Any) -> Any:
        return _normalize_required_text(value, "origin")

    @field_validator("shape_desc", "soup_desc", "aroma_desc", "taste_desc", mode="before")
    @classmethod
    def _validate_required_desc(cls, value: Any) -> Any:
        return _normalize_required_text(value, "感官描述")

    @field_validator(
        "season",
        "fermentation",
        "price_range",
        "representative_variety",
        "main_image_url",
        "tips_history",
        "tips_suitable",
        "tips_misconception",
        "tips_official_note",
        mode="before",
    )
    @classmethod
    def _validate_optional_text(cls, value: Any) -> Any:
        return _normalize_optional_text(value)

    @field_validator("water_temp", "tea_amount", "brew_time", mode="before")
    @classmethod
    def _validate_number(cls, value: Any) -> Any:
        return _one_decimal(value)

    @field_validator("main_image_url")
    @classmethod
    def _validate_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/uploads/")
        ):
            raise ValueError("main_image_url 必须为 http(s):// 或 /uploads/ 路径")
        return value


class ContributionCreateRequest(BaseModel):
    """创建提交（API_CONTRACT §4.8.1）：按 type 二选一。"""

    model_config = ConfigDict(extra="forbid")

    type: ContributionType
    tea: ContributionTeaPayload | None = None
    target_tea_id: int | None = None
    title: str | None = Field(None, max_length=TITLE_MAX_LEN)
    content: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, value: Any) -> Any:
        return _normalize_optional_text(value)

    @field_validator("content", mode="before")
    @classmethod
    def _normalize_content(cls, value: Any) -> Any:
        if value is None:
            return None
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_by_type(self) -> "ContributionCreateRequest":
        if self.type == "new_tea":
            if self.tea is None:
                raise ValueError("new_tea 提交必须提供 tea")
            if self.target_tea_id is not None or self.content is not None:
                raise ValueError("new_tea 提交不接受 target_tea_id / content")
            return self

        if self.target_tea_id is None:
            raise ValueError("article 提交必须提供 target_tea_id")
        if self.content is None or not (CONTENT_MIN_LEN <= len(self.content) <= CONTENT_MAX_LEN):
            raise ValueError(f"科普内容需为 {CONTENT_MIN_LEN}–{CONTENT_MAX_LEN} 字")
        if self.tea is not None:
            raise ValueError("article 提交不接受 tea")
        return self


class ContributionItem(BaseModel):
    """单条提交记录（用户端 / 管理端共用）。"""

    id: int
    type: ContributionType
    status: ContributionStatus
    target_tea_id: int | None = None
    target_tea_name: str | None = None
    payload: dict[str, Any]
    reject_reason: str | None = None
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    username: str | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return iso_z(v)

    @field_serializer("reviewed_at")
    def serialize_reviewed_at(self, v: datetime | None) -> str | None:
        return iso_z(v) if v is not None else None


class ContributionListResponse(BaseModel):
    """管理端分页结构（API_CONTRACT §1.6 / §4.6.12）。"""

    items: list[ContributionItem]
    total: int
    page: int
    page_size: int


class RejectRequest(BaseModel):
    """拒绝提交（API_CONTRACT §4.6.14）：预设理由或自定义，1–200 字。"""

    model_config = ConfigDict(extra="forbid")

    reason: str

    @field_validator("reason", mode="before")
    @classmethod
    def _normalize_reason(cls, value: Any) -> Any:
        return _normalize_required_text(value, "reason")

    @field_validator("reason")
    @classmethod
    def _check_reason_len(cls, value: str) -> str:
        if len(value) > REASON_MAX_LEN:
            raise ValueError(f"拒绝理由不能超过 {REASON_MAX_LEN} 字")
        return value
