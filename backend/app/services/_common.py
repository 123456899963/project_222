"""业务层公共工具（仅纯函数，不含数据库访问与业务规则）。"""


def split_csv(raw: str | None) -> list[str]:
    """逗号分隔多值解析，去空白与空项。"""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]
