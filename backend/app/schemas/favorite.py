"""收藏相关 Schema（API_CONTRACT §4.3 / §4.4 FavoriteState）"""

from pydantic import BaseModel, ConfigDict


class FavoriteState(BaseModel):
    """收藏状态 + 所在清单 + 茶品缓存收藏数（§4.3.1 ~ §4.3.3）"""

    model_config = ConfigDict(from_attributes=True)

    tea_id: int
    is_favorited: bool
    favorite_count: int
    list_ids: list[int] = []


class FavoriteAddRequest(BaseModel):
    """收藏请求体（可选）：不传 list_id 时归入默认清单。"""

    model_config = ConfigDict(extra="forbid")

    list_id: int | None = None
