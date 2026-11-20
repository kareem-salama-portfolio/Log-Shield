"""Empty and synthetic adapters for Log Import & Event Explorer development.

The demo query operates against only this module's fixed sample records and
returns a page. The screen receives that page; it never loads or filters the
provider's entire fixture collection itself.
"""

from copy import deepcopy

from app.models.log_import import (
    EventFilters,
    EventPage,
    EventRecord,
    ImportHistoryRecord,
    IPDetails,
    MalformedRecord,
)


_DEMO_IMPORT_HISTORY: tuple[ImportHistoryRecord, ...] = (
    {
        "import_id": 2,
        "file_name": "secure-archive.txt",
        "imported_at": "2026-10-02T09:18:00",
        "total_records": 481,
        "accepted_records": 481,
        "malformed_records": 0,
        "status": "COMPLETED",
    },
    {
        "import_id": 1,
        "file_name": "auth-sample.log",
        "imported_at": "2026-10-02T08:35:00",
        "total_records": 876,
        "accepted_records": 872,
        "malformed_records": 4,
        "status": "PARTIAL",
    },
)

_DEMO_EVENTS: tuple[EventRecord, ...] = (
    {"id": 101, "timestamp": "2026-10-02T08:00:10", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 1, "line_no": 25},
    {"id": 102, "timestamp": "2026-10-02T08:00:44", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 1, "line_no": 27},
    {"id": 103, "timestamp": "2026-10-02T08:02:01", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 1, "line_no": 39},
    {"id": 104, "timestamp": "2026-10-02T08:03:18", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "SUCCESS", "file_id": 1, "line_no": 48},
    {"id": 105, "timestamp": "2026-10-02T08:05:33", "source_ip": "203.0.113.21", "username": "root", "outcome": "FAILED", "file_id": 1, "line_no": 62},
    {"id": 106, "timestamp": "2026-10-02T08:06:07", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "SUCCESS", "file_id": 1, "line_no": 64},
    {"id": 107, "timestamp": "2026-10-02T08:09:52", "source_ip": "203.0.113.7", "username": "deploy", "outcome": "FAILED", "file_id": 2, "line_no": 13},
    {"id": 108, "timestamp": "2026-10-02T08:12:29", "source_ip": "198.51.100.42", "username": "operator", "outcome": "SUCCESS", "file_id": 2, "line_no": 51},
    {"id": 109, "timestamp": "2026-10-02T08:14:55", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "SUCCESS", "file_id": 2, "line_no": 88},
    {"id": 110, "timestamp": "2026-10-02T08:16:11", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 2, "line_no": 96},
)

_DEMO_IP_DETAILS: dict[str, IPDetails] = {
    "203.0.113.7": {
        "source_ip": "203.0.113.7",
        "total_events": 18,
        "failed_logins": 16,
        "successful_logins": 2,
        "first_seen": "2026-10-02 08:00:10",
        "last_seen": "2026-10-02 08:26:42",
        "activity": [
            {"timestamp": "2026-10-02T08:00:00", "event_count": 2},
            {"timestamp": "2026-10-02T08:05:00", "event_count": 5},
            {"timestamp": "2026-10-02T08:10:00", "event_count": 3},
            {"timestamp": "2026-10-02T08:15:00", "event_count": 4},
            {"timestamp": "2026-10-02T08:20:00", "event_count": 4},
        ],
    },
    "198.51.100.42": {
        "source_ip": "198.51.100.42",
        "total_events": 9,
        "failed_logins": 5,
        "successful_logins": 4,
        "first_seen": "2026-10-02 08:03:18",
        "last_seen": "2026-10-02 08:19:51",
        "activity": [
            {"timestamp": "2026-10-02T08:03:00", "event_count": 1},
            {"timestamp": "2026-10-02T08:08:00", "event_count": 3},
            {"timestamp": "2026-10-02T08:13:00", "event_count": 2},
            {"timestamp": "2026-10-02T08:18:00", "event_count": 3},
        ],
    },
    "192.0.2.44": {
        "source_ip": "192.0.2.44",
        "total_events": 3,
        "failed_logins": 0,
        "successful_logins": 3,
        "first_seen": "2026-10-02 08:03:18",
        "last_seen": "2026-10-02 08:14:55",
        "activity": [
            {"timestamp": "2026-10-02T08:03:00", "event_count": 1},
            {"timestamp": "2026-10-02T08:09:00", "event_count": 1},
            {"timestamp": "2026-10-02T08:14:00", "event_count": 1},
        ],
    },
}

_DEMO_MALFORMED: dict[int, tuple[MalformedRecord, ...]] = {
    1: (
        {"line_no": 102, "raw_text": "not-a-date sshd[2041]: Failed password for admin from 203.0.113.8", "reason": "Bad timestamp"},
        {"line_no": 219, "raw_text": "Oct  2 08:06:13 host sshd: Failed password for root from 999.10.2.4", "reason": "Invalid IP"},
        {"line_no": 440, "raw_text": "auth record with an unrecognized event shape", "reason": "Unknown pattern"},
        {"line_no": 603, "raw_text": "Oct  2 08:16:17 host sshd: Failed password for", "reason": "Unknown pattern"},
    ),
}


def get_empty_import_history() -> list[ImportHistoryRecord]:
    return []


def get_empty_event_page(page: int = 1, page_size: int = 200) -> EventPage:
    return {"items": [], "page": page, "page_size": page_size, "total_count": 0}


def get_demo_import_history() -> list[ImportHistoryRecord]:
    return deepcopy(list(_DEMO_IMPORT_HISTORY))


def get_demo_event_page(
    filters: EventFilters,
    *,
    page: int = 1,
    page_size: int = 200,
) -> EventPage:
    """Return a filtered fixture page for visual development, not real analysis."""
    matches = [event for event in _DEMO_EVENTS if _matches(event, filters)]
    safe_page_size = max(1, page_size)
    safe_page = max(1, page)
    start = (safe_page - 1) * safe_page_size
    return {
        "items": deepcopy(list(matches[start : start + safe_page_size])),
        "page": safe_page,
        "page_size": safe_page_size,
        "total_count": len(matches),
    }


def get_demo_ip_details(source_ip: str) -> IPDetails | None:
    details = _DEMO_IP_DETAILS.get(source_ip)
    return deepcopy(details) if details is not None else None


def get_demo_malformed_records(import_id: int) -> list[MalformedRecord]:
    return deepcopy(list(_DEMO_MALFORMED.get(import_id, ())))


def _matches(event: EventRecord, filters: EventFilters) -> bool:
    source_ip = filters["source_ip"]
    if source_ip and source_ip.casefold() not in event["source_ip"].casefold():
        return False
    username = filters["username"]
    if username and username.casefold() not in event["username"].casefold():
        return False
    outcome = filters["outcome"]
    if outcome and outcome.upper() != event["outcome"].upper():
        return False
    start_time = filters["start_time"]
    if start_time and event["timestamp"] < start_time:
        return False
    end_time = filters["end_time"]
    if end_time and event["timestamp"] > end_time:
        return False
    return True
