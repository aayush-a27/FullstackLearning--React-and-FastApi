"""General utility/helper functions for the backend."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime) -> str:
    """Format a datetime to ISO 8601 string."""
    return dt.isoformat()
