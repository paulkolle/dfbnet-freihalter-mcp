from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def to_dfbnet_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def date_range_payload(start_date: str | date, end_date: str | date, tz_name: str = "Europe/Berlin", reason: str = "PREVENTED", comment: str | None = None) -> dict:
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    tz = ZoneInfo(tz_name)
    start_local = datetime.combine(start_date, time(0, 0, 0), tzinfo=tz)
    # DFBNet UI uses 23:59:00 for manually created NORMAL full-day exemptions.
    until_local = datetime.combine(end_date, time(23, 59, 0), tzinfo=tz)
    return {
        "from": to_dfbnet_utc(start_local),
        "until": to_dfbnet_utc(until_local),
        "reason": reason,
        "comment": comment,
    }


def full_day_payload(day: str | date, tz_name: str = "Europe/Berlin", reason: str = "PREVENTED", comment: str | None = None) -> dict:
    return date_range_payload(day, day, tz_name=tz_name, reason=reason, comment=comment)


def local_day_match(entry: dict, day: str | date, tz_name: str = "Europe/Berlin") -> bool:
    if isinstance(day, str):
        day = parse_date(day)
    tz = ZoneInfo(tz_name)
    try:
        start = datetime.fromisoformat(str(entry["from"]).replace("Z", "+00:00")).astimezone(tz)
        until = datetime.fromisoformat(str(entry["until"]).replace("Z", "+00:00")).astimezone(tz)
    except Exception:
        return False
    return start.date() == day and until.date() == day and start.hour == 0 and start.minute == 0 and until.hour == 23 and until.minute in (59,)
