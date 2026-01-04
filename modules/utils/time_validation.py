from __future__ import annotations

import logging

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from modules.models.collection_types import Collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)

UTC = timezone.utc


def parse_utc_timestamp(value: Union[str, datetime]) -> datetime:
    """
    Parse an ISO-8601 UTC timestamp and return a timezone-aware UTC datetime
    truncated to seconds.

    Accepted:
      - '2026-01-04T14:22:33Z'
      - '2026-01-04T14:22:33.179345200Z'
      - '2026-01-04T14:22:33+00:00'
      - aware datetime in UTC

    Rejected:
      - naive datetime
      - legacy 'YYYY-MM-DD HH:MM:SS'
    """
    if hasattr(value, 'tzinfo'):
        if value.tzinfo is None:
            raise ValueError("Naive datetime is not allowed")
        return value.astimezone(UTC).replace(microsecond=0)

    if not isinstance(value, str):
        raise TypeError(f"Unsupported timestamp type: {type(value)!r}")

    s = value.strip()

    # Enforce ISO-8601 with timezone
    if "T" not in s or ("Z" not in s and "+" not in s and "-" not in s[10:]):
        raise ValueError(f"Invalid ISO-8601 UTC timestamp: {value}")

    # Normalize Z → +00:00
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    # Drop fractional seconds (we only care up to seconds)
    if "." in s:
        before_dot, after_dot = s.split(".", 1)

        tz_part = ""
        if "+" in after_dot:
            tz_part = "+" + after_dot.split("+", 1)[1]
        elif "-" in after_dot and ":" in after_dot[after_dot.rfind("-"):]:
            tz_part = after_dot[after_dot.rfind("-"):]

        s = before_dot + tz_part

    dt = datetime.fromisoformat(s)

    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone information")

    return dt.astimezone(UTC).replace(microsecond=0)


def get_lootpool_week() -> tuple[int, int]:
    return get_lootpool_week_for_timestamp(datetime.now(UTC))


def get_lootpool_week_for_timestamp(
        timestamp: Union[str, int, float, datetime],
        reset_day: int = 4,
        reset_hour: int = 18
) -> tuple[int, int]:
    """Get the current Wynn week number and year. Lootpool resets every Friday at 6 PM UTC."""
    now = parse_utc_timestamp(timestamp)

    days_since_reset = (now.weekday() - reset_day) % 7
    last_reset = now - timedelta(days=days_since_reset)

    # If it's reset day but before reset hour, use the previous week
    if last_reset.weekday() == reset_day and now.hour < reset_hour:
        last_reset -= timedelta(days=7)

    last_reset = last_reset.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    next_reset = last_reset + timedelta(days=7)

    if now >= next_reset:
        wynn_week = next_reset.isocalendar().week
        wynn_year = next_reset.year
    else:
        wynn_week = last_reset.isocalendar().week
        wynn_year = last_reset.year

    return wynn_year, wynn_week


def get_raidpool_week() -> tuple[int, int]:
    return get_lootpool_week_for_timestamp(datetime.now(UTC), reset_hour=17)


def get_current_gambit_day(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    reset_hour = 17  # 17:00 (5 PM) UTC
    now = parse_utc_timestamp(now or datetime.now(UTC))

    reset_today = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)

    if now >= reset_today:  # past today's reset => next reset tomorrow
        previous_reset = reset_today
        next_reset = reset_today + timedelta(days=1)
    else:  # before today's reset
        next_reset = reset_today
        previous_reset = reset_today - timedelta(days=1)

    return previous_reset, next_reset


def get_week_range(
        reset_day: int,
        reset_hour: int,
        now: Optional[Union[str, int, float, datetime]] = None
) -> tuple[datetime, datetime]:
    now_dt = parse_utc_timestamp(now or datetime.now(UTC))

    days_since_reset_day = (now_dt.weekday() - reset_day + 7) % 7
    last_reset_date = now_dt.date() - timedelta(days=days_since_reset_day)

    last_reset = datetime(
        last_reset_date.year, last_reset_date.month, last_reset_date.day,
        reset_hour, 0, 0, 0,
        tzinfo=UTC
    )

    # If today is reset day but current time is before reset time, subtract a week
    if days_since_reset_day == 0 and now_dt < last_reset:
        last_reset -= timedelta(days=7)

    next_reset = last_reset + timedelta(days=7)
    return last_reset, next_reset


def is_time_valid(pool_type: Collection, time_value: Union[str, int, float, datetime]) -> bool:
    """Check if the provided timestamp belongs to the current Wynncraft period (UTC-aware)."""
    time_dt = parse_utc_timestamp(time_value)

    if pool_type == Collection.RAID:
        reset_day = 4  # Friday
        reset_hour = 17  # 17:00 (5 PM) UTC
        week_start, week_end = get_week_range(reset_day, reset_hour)
        return week_start <= time_dt < week_end

    if pool_type == Collection.LOOT:
        reset_day = 4  # Friday
        reset_hour = 18  # 18:00 (6 PM) UTC
        week_start, week_end = get_week_range(reset_day, reset_hour)
        return week_start <= time_dt < week_end

    if pool_type == Collection.GAMBIT:
        previous_reset, next_reset = get_current_gambit_day()
        return previous_reset <= time_dt < next_reset

    return False
