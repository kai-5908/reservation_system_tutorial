from datetime import datetime, timezone
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def to_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def utc_naive_to_jst(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(JST)
