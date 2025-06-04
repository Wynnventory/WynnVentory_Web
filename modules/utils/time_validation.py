from datetime import datetime, timedelta, timezone

from modules.models.collection_types import Collection


def get_lootpool_week():
    return get_lootpool_week_for_timestamp(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))

def get_lootpool_week_for_timestamp(timestamp, reset_day=4, reset_hour=18):
    """ Get the current Wynn week number and year. Lootpool resets every Friday at 6 PM UTC. """

    now = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

    days_since_reset = (now.weekday() - reset_day) % 7
    last_reset = now - timedelta(days=days_since_reset)

    if last_reset.weekday() == reset_day and now.hour < reset_hour:
        last_reset -= timedelta(days=7)

    last_reset = last_reset.replace(
        hour=reset_hour, minute=0, second=0, microsecond=0)

    next_reset = last_reset + timedelta(days=7)

    if now >= next_reset:
        wynn_week = next_reset.isocalendar().week
        wynn_year = next_reset.year
    else:
        wynn_week = last_reset.isocalendar().week
        wynn_year = last_reset.year

    return wynn_year, wynn_week

def get_raidpool_week():
    return get_lootpool_week_for_timestamp(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), reset_hour=17)

def get_current_gambit_day():
    reset_hour = 19  # 19:00 (7 PM) UTC

    now = datetime.now()
    reset_today = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if now.hour > reset_hour: # Already past reset time today = next reset tomorrow at reset hour
        next_reset = reset_today + timedelta(days=1)
        previous_reset = reset_today
    else: # still before reset today = reset today at reset hour
        next_reset = reset_today
        previous_reset = reset_today - timedelta(days=1)

    return previous_reset, next_reset

def get_week_range(reset_day, reset_hour, now=None):
    if now is None:
        now = datetime.now(timezone.utc)

    # Calculate days since the last reset day
    days_since_reset_day = (now.weekday() - reset_day + 7) % 7
    last_reset_date = now.date() - timedelta(days=days_since_reset_day)

    # Combine last reset date with reset time
    last_reset = datetime.combine(last_reset_date, datetime.min.time()).replace(hour=reset_hour)

    # If today is the reset day and current time is before the reset time, subtract a week
    if days_since_reset_day == 0 and now < last_reset:
        last_reset -= timedelta(days=7)

    # Next reset is always 7 days after last reset
    next_reset = last_reset + timedelta(days=7)

    return last_reset, next_reset


def is_time_valid(pool_type: Collection, time_str):
    """Check if the provided timestamp belongs to the current Wynncraft week.

    Args:
        pool_type (str): The type of week ("RAID" or "LOOT").
        time_str (str): The timestamp in 'YYYY-MM-DD HH:MM:SS' format.

    Returns:
        bool: True if the time belongs to the current week, False otherwise.
    """
    # Parse the time string into a datetime object
    time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

    if pool_type == Collection.RAID:
        reset_day = 4  # Friday
        reset_hour = 17  # 17:00 (5 PM) UTC
    elif pool_type == Collection.LOOT:
        reset_day = 4  # Friday
        reset_hour = 18  # 18:00 (6 PM) UTC
    elif pool_type == Collection.GAMBIT:
        previous_reset, next_reset = get_current_gambit_day()

        return previous_reset <= time < next_reset
    else:
        return False

    # Get the week range for the current week
    week_start, week_end = get_week_range(reset_day, reset_hour)

    # Check if the time falls within the current week range
    return week_start <= time < week_end