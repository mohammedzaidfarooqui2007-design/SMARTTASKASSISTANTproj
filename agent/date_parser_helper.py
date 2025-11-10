import dateparser
from datetime import datetime
from dateparser.search import search_dates


def extract_time(text: str):
    """
    Extract and return a datetime object from text using dateparser.
    Automatically interprets future dates and Indian timezone.
    Supports phrases like:
      - "tomorrow at 5pm"
      - "next monday 9am"
      - "in 2 hours"
      - "5th November 3:30pm"
    """
    if not text or not isinstance(text, str):
        return None

    # Try direct parsing first
    parsed_time = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "Asia/Kolkata",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if parsed_time:
        return parsed_time

    # Try searching for date/time expressions inside the text
    try:
        results = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "TIMEZONE": "Asia/Kolkata",
                "RETURN_AS_TIMEZONE_AWARE": False,
            },
        )
        if results:
            # search_dates returns list of tuples [(phrase, datetime)]
            return results[0][1]
    except Exception:
        pass

    return None


def format_time(dt):
    """
    Convert a datetime object into '%Y-%m-%d %H:%M' formatted string.
    """
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return None