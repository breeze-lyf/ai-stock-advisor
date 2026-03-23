from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """
    Return the current UTC time as a naive datetime.

    The database schema currently stores UTC timestamps in naive DateTime
    columns, so we preserve that behavior while avoiding datetime.utcnow().
    """
    return datetime.now(UTC).replace(tzinfo=None)
