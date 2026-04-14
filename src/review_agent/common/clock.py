"""时间工具。"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(UTC)
