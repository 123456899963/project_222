"""用户统计与等级 Schema（S15 / API_CONTRACT §4.7.1）"""

from pydantic import BaseModel, ConfigDict


class LevelInfo(BaseModel):
    """等级信息：四档（茶客/茶友/茶人/茶师），按收藏数实时计算。"""

    name: str
    index: int  # 1-4
    next_name: str | None = None
    next_threshold: int | None = None
    remaining: int = 0


class UserStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    favorite_count: int
    note_count: int
    share_count: int
    level: LevelInfo
