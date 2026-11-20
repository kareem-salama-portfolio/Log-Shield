"""Shared authentication-log event models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class Event:
    """A normalized authentication-log record."""

    id: int | None = None
    timestamp: datetime
    source_ip: str
    username: str
    outcome: str
    file_id: int | None = None
    line_no: int


@dataclass(kw_only=True)
class MalformedRecord:
    """A supported-format log line that could not be normalized."""

    line_no: int
    line_raw: str
    reason: str

