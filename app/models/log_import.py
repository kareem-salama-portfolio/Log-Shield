"""Plain request and response shapes for log import and event exploration."""

from typing import NotRequired, TypedDict


class ImportHistoryRecord(TypedDict):
    """Summary of one import, including its key for detail lookups."""

    import_id: int
    file_name: str
    imported_at: str
    total_records: int
    accepted_records: int
    malformed_records: int
    status: str


class ImportHistoryPage(TypedDict):
    items: list[ImportHistoryRecord]
    page: int
    page_size: int
    total_count: int | None


class EventFilters(TypedDict):
    source_ip: str | None
    username: str | None
    outcome: str | None
    start_time: str | None
    end_time: str | None


class EventRecord(TypedDict):
    id: int
    timestamp: str
    source_ip: str
    username: str
    outcome: str
    file_id: int
    line_no: int


class EventPage(TypedDict):
    items: list[EventRecord]
    page: int
    page_size: int
    total_count: int | None


class IPActivityPoint(TypedDict):
    timestamp: str
    event_count: int


class IPDetails(TypedDict):
    source_ip: str
    total_events: int
    failed_logins: int
    successful_logins: int
    first_seen: str
    last_seen: str
    activity: list[IPActivityPoint]


class MalformedRecord(TypedDict):
    line_no: int
    raw_text: str
    reason: str


class ImportProgress(TypedDict, total=False):
    percentage: int
    status: str
    file_name: NotRequired[str]
