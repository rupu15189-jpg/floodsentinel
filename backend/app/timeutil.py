"""时区处理：库里统一存 UTC 的 naive datetime，接口统一输出 +08:00。

这是全项目唯一允许做时间转换的地方，别在别处写 datetime.now() 直接用。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))


def now_utc() -> datetime:
    """当前 UTC 时间（naive），用于写库。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_db(dt: datetime) -> datetime:
    """外部传入的时间 → 入库格式（UTC naive）。"""
    if dt.tzinfo is None:
        # 无时区按东八区理解，避免前端传 '2026-07-20T14:05:00' 被当成 UTC
        dt = dt.replace(tzinfo=CST)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_api(dt: datetime | None) -> str | None:
    """入库时间 → 接口输出（+08:00 ISO8601）。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CST).isoformat(timespec="seconds")


def parse_api(s: str) -> datetime:
    """接口输入字符串 → datetime。"""
    return datetime.fromisoformat(s)
