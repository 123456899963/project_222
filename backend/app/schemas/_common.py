"""Schema 层公共序列化工具（不 import Model）。"""

from datetime import datetime


def iso_z(value: datetime) -> str:
    """naive UTC DATETIME → 'YYYY-MM-DDTHH:mm:ssZ'（API_CONTRACT §1.7）。"""
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
