"""时间工具：统一产出 naive UTC 时间，对齐 MySQL DATETIME 列语义。

替代 Python 3.12 起弃用的 ``datetime.utcnow()``：DATETIME 列不带时区，
写入时统一使用 naive UTC，API 输出时由 Pydantic serializer 追加 ``Z``。
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """当前 UTC 时间（naive）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
