"""茶品相关 Schema（响应 DTO，对齐 API_CONTRACT §2.2 / §2.3 / §2.3.1）

红线：schemas 不 import Model（ARCHITECTURE §3）；ORM → DTO 的转换
通过 from_attributes + model_validator 扁平化 tips_* 派生字段完成。
时间字段统一输出 ISO8601 UTC 带 Z（API_CONTRACT §1.7）。
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
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

CATEGORY_VALUES = ("green", "white", "yellow", "red", "oolong", "dark", "reprocessed")
SEASON_VALUES = ("明前", "雨前", "春茶", "夏茶", "秋茶", "冬茶")
FERMENTATION_VALUES = ("不发酵", "微发酵", "半发酵", "全发酵", "后发酵")
SORT_VALUES = ("newest", "favorite")

CategoryValue = Literal["green", "white", "yellow", "red", "oolong", "dark", "reprocessed"]
SeasonValue = Literal["明前", "雨前", "春茶", "夏茶", "秋茶", "冬茶"]
FermentationValue = Literal["不发酵", "微发酵", "半发酵", "全发酵", "后发酵"]


class TeaListItem(BaseModel):
    """公开列表卡片（API_CONTRACT §2.2）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    origin: str
    season: str | None = None
    main_image_url: str | None = None
    favorite_count: int = 0


class TeaListResponse(BaseModel):
    """分页结构（API_CONTRACT §1.6 / §4.2.1）"""

    items: list[TeaListItem]
    total: int
    page: int
    page_size: int


class TeaArticleItem(BaseModel):
    """已通过审核的用户科普投稿（S11 / S12），随茶品详情返回。"""

    id: int
    title: str | None = None
    content: str
    contributor: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        return iso_z(v)


class BrewingStep(BaseModel):
    """冲泡教程单步（ADR-0005）：标题 + 动作说明 + 可选小提示。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=30)
    detail: str = Field(min_length=1, max_length=200)
    tip: str | None = Field(default=None, max_length=100)

    @field_validator("title", "detail", "tip", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value


class BrewingGuide(BaseModel):
    """茶品冲泡教程（ADR-0005）：3–8 步，整篇读写。"""

    intro: str | None = Field(default=None, max_length=200)
    steps: list[BrewingStep] = Field(min_length=3, max_length=8)
    caution: str | None = Field(default=None, max_length=500)

    @field_validator("intro", "caution", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value


class BrewingGuideUpdateRequest(BrewingGuide):
    """管理员整篇保存教程（ADR-0005）：步数与字段长度在 Schema 层校验。"""

    model_config = ConfigDict(extra="forbid")


class TeaDetail(BaseModel):
    """茶品详情（API_CONTRACT §2.3）：含扁平化 tips_* 派生字段"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    origin: str
    season: str | None = None
    fermentation: str | None = None
    price_range: str | None = None
    # 价格区间数值（S2 五档筛选）：单位元/斤
    price_min: int | None = None
    price_max: int | None = None
    representative_variety: str | None = None

    shape_desc: str
    soup_desc: str
    aroma_desc: str
    taste_desc: str

    water_temp: float | None = None
    tea_amount: float | None = None
    brew_time: float | None = None

    main_image_url: str | None = None
    # 视频介绍（ADR-0003 S5）：video_url 为 NULL 时前端整块隐藏
    video_url: str | None = None
    video_duration: int | None = None
    # 图片集（ADR-0003 S4）：最多 9 张，按 sort_order 升序；空列表表示无图片集
    image_set: list[str] = Field(default_factory=list)
    is_active: bool = True
    favorite_count: int = 0

    tips_history: str | None = None
    tips_suitable: str | None = None
    tips_misconception: str | None = None
    tips_official_note: str | None = None

    # 分步冲泡教程（ADR-0005）：null 表示未维护，前端退回三格速查卡
    brewing_guide: BrewingGuide | None = None

    # 用户科普投稿（S11 / S12）：仅含审核通过项，空列表时前端隐藏
    contributed_articles: list[TeaArticleItem] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def flatten_tips(cls, data: Any) -> Any:
        """ORM Tea 对象 → 扁平 DTO 输入：把 tea.tips.* 映射为 tips_*。"""
        # 仅处理带 SQLAlchemy 表结构的 ORM 对象；dict 直接放行
        if hasattr(data, "__table__"):
            columns = {c.name: getattr(data, c.name) for c in data.__table__.columns}
            tips = getattr(data, "tips", None)
            columns["tips_history"] = tips.history if tips else None
            columns["tips_suitable"] = tips.suitable if tips else None
            columns["tips_misconception"] = tips.misconception if tips else None
            columns["tips_official_note"] = tips.official_note if tips else None
            guide = getattr(data, "brewing_guide", None)
            columns["brewing_guide"] = (
                {"intro": guide.intro, "steps": guide.steps, "caution": guide.caution}
                if guide
                else None
            )
            media = getattr(data, "media_images", None) or []
            columns["image_set"] = [m.image_url for m in media]
            return columns
        return data

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, v: datetime) -> str:
        return iso_z(v)


class CategoryCount(BaseModel):
    """七大茶类计数（API_CONTRACT §2.3.1）"""

    category: Literal["green", "white", "yellow", "red", "oolong", "dark", "reprocessed"]
    count: int


class OriginCount(BaseModel):
    """产地（省级）计数（API_CONTRACT §2.3.1）"""

    origin: str
    count: int


def _normalize_optional_text(value: Any) -> Any:
    """选填文本：trim 后空串归一化为 None（API_CONTRACT §4.6.3）。"""
    if value is None or not isinstance(value, str):
        return value
    return value.strip() or None


def _normalize_required_text(value: Any, field: str) -> Any:
    """必填文本：trim 后必须非空。"""
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} 不能为空")
    return normalized


def _one_decimal(value: Any) -> Any:
    """数值最多 1 位小数，且不超过目标精度。"""
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("数值格式非法") from exc
    if decimal_value.as_tuple().exponent < -1:
        raise ValueError("数值最多保留 1 位小数")
    return float(decimal_value)


class TeaBaseRequest(BaseModel):
    """管理员茶品主体字段（新增/编辑共用，extra=forbid 防批量赋值 S-20）。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100)
    category: CategoryValue
    origin: str = Field(..., max_length=200)
    season: SeasonValue | None = None
    fermentation: FermentationValue | None = None
    price_range: str | None = Field(None, max_length=32)
    # 价格区间数值（S2）：单位元/斤，null 表示未维护，不参与价格筛选
    price_min: int | None = Field(None, ge=0, le=100000)
    price_max: int | None = Field(None, ge=0, le=100000)
    representative_variety: str | None = Field(None, max_length=100)

    shape_desc: str
    soup_desc: str
    aroma_desc: str
    taste_desc: str

    water_temp: float = Field(..., ge=70.0, le=100.0)
    tea_amount: float = Field(..., gt=0, le=999.9)
    brew_time: float = Field(..., gt=0, le=999.9)

    main_image_url: str = Field(..., max_length=500)

    # 视频介绍（ADR-0003 S5）：仅允许本站 /uploads/ 路径，禁止第三方外链
    video_url: str | None = Field(None, max_length=500)
    video_duration: int | None = Field(None, ge=1, le=180)

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
        "video_url",
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
    def _validate_image_url(cls, value: str) -> str:
        if not (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("/uploads/")
        ):
            raise ValueError("main_image_url 必须为 http(s):// 或 /uploads/ 路径")
        return value

    @field_validator("video_url")
    @classmethod
    def _validate_video_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("/uploads/"):
            raise ValueError("video_url 必须为本站 /uploads/ 路径")
        return value

    @model_validator(mode="after")
    def _validate_price_order(self) -> "TeaBaseRequest":
        """价格区间：两端都填时下限不得大于上限（S2）。"""
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min 不能大于 price_max")
        return self


class TeaCreateRequest(TeaBaseRequest):
    """管理员新增茶品（API_CONTRACT §4.6.3）。"""

    tips_history: str | None = None
    tips_suitable: str | None = None
    tips_misconception: str | None = None
    tips_official_note: str | None = None

    @field_validator(
        "tips_history", "tips_suitable", "tips_misconception", "tips_official_note", mode="before"
    )
    @classmethod
    def _validate_tips(cls, value: Any) -> Any:
        return _normalize_optional_text(value)


class TeaUpdateRequest(TeaBaseRequest):
    """管理员编辑茶品（API_CONTRACT §4.6.4）：PUT 全量替换，不接受 tips_*。"""


class TeaMediaItem(BaseModel):
    """茶品图片集条目（ADR-0003 S4 / API_CONTRACT §4.2.7）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    sort_order: int


class TeaMediaCreateRequest(BaseModel):
    """管理员追加图片（ADR-0003 S4）：仅接受本站 /uploads/ 路径。"""

    model_config = ConfigDict(extra="forbid")

    image_url: str = Field(..., max_length=500)
    sort_order: int | None = Field(None, ge=0)

    @field_validator("image_url")
    @classmethod
    def _validate_image_url(cls, value: str) -> str:
        if not value.startswith("/uploads/"):
            raise ValueError("image_url 必须为本站 /uploads/ 路径")
        return value


class LatestTipItem(BaseModel):
    """首页最新小贴士（S7）：按 tea_tips.updated_at 倒序取前 N 条。"""

    tea_id: int
    tea_name: str
    category: str
    summary: str
    updated_at: datetime

    @field_serializer("updated_at")
    def serialize_datetime(self, v: datetime) -> str:
        return iso_z(v)
