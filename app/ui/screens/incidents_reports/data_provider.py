"""Synthetic evidence fixtures for explicitly enabled demo mode."""

from copy import deepcopy

from app.models.detection import DetectionIncident
from app.models.log_import import EventRecord


_DEMO_EVIDENCE: dict[int, list[EventRecord]] = {
    15: [
        {"id": 101, "timestamp": "2026-10-02T08:00:10", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 3, "line_no": 25},
        {"id": 102, "timestamp": "2026-10-02T08:01:03", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 3, "line_no": 27},
        {"id": 103, "timestamp": "2026-10-02T08:02:41", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 3, "line_no": 32},
        {"id": 104, "timestamp": "2026-10-02T08:04:18", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 3, "line_no": 39},
        {"id": 105, "timestamp": "2026-10-02T08:06:52", "source_ip": "203.0.113.7", "username": "admin", "outcome": "FAILED", "file_id": 3, "line_no": 44},
        {"id": 106, "timestamp": "2026-10-02T08:09:55", "source_ip": "203.0.113.7", "username": "admin", "outcome": "SUCCESS", "file_id": 3, "line_no": 51},
    ],
    16: [
        {"id": 107, "timestamp": "2026-10-02T08:04:10", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 3, "line_no": 61},
        {"id": 108, "timestamp": "2026-10-02T08:05:22", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 3, "line_no": 63},
        {"id": 109, "timestamp": "2026-10-02T08:07:03", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 3, "line_no": 68},
        {"id": 110, "timestamp": "2026-10-02T08:08:33", "source_ip": "198.51.100.42", "username": "svc-backup", "outcome": "FAILED", "file_id": 3, "line_no": 72},
    ],
    9: [
        {"id": 41, "timestamp": "2026-09-30T09:12:15", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "FAILED", "file_id": 1, "line_no": 14},
        {"id": 42, "timestamp": "2026-09-30T09:14:02", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "FAILED", "file_id": 1, "line_no": 18},
        {"id": 43, "timestamp": "2026-09-30T09:16:31", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "FAILED", "file_id": 1, "line_no": 21},
        {"id": 44, "timestamp": "2026-09-30T09:18:05", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "FAILED", "file_id": 1, "line_no": 26},
        {"id": 45, "timestamp": "2026-09-30T09:19:40", "source_ip": "192.0.2.44", "username": "analyst", "outcome": "SUCCESS", "file_id": 1, "line_no": 28},
    ],
}


def get_demo_incident_evidence(incident: DetectionIncident) -> list[EventRecord]:
    """Return only fixture events associated with this incident's event IDs."""
    linked_ids = set(incident["event_ids"])
    return deepcopy(
        [
            event
            for event in _DEMO_EVIDENCE.get(incident["id"], [])
            if event["id"] in linked_ids
        ]
    )
