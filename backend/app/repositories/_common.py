"""仓储层公共工具（仅纯函数，不涉及查询与业务判断）。"""


def escape_like(value: str) -> str:
    """转义 LIKE 通配符，避免用户输入 % / _ 被解释为模式。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
