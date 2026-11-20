"""Incident model produced by the detection engine."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(kw_only=True)
class Incident:
    """A brute-force detection incident and its supporting event IDs."""

    id: int | None = None
    run_id: int | None = None
    source_ip: str
    start_ts: datetime
    end_ts: datetime
    failure_count: int
    severity: str = "MEDIUM"
    status: str = "NEW"
    note: str = ""
    event_ids: list[int] = field(default_factory=list)

