"""Synthetic historical detection runs for explicit ``--demo-data`` review."""

from copy import deepcopy

from app.models.detection import DetectionIncident, DetectionRunSummary


_DEMO_RUNS: list[DetectionRunSummary] = [
    {
        "run_id": 3,
        "started_at": "2026-10-02T08:10:05",
        "failure_threshold": 5,
        "time_window_minutes": 10,
        "total_incidents": 3,
        "high_incidents": 1,
    },
    {
        "run_id": 2,
        "started_at": "2026-10-01T13:45:20",
        "failure_threshold": 6,
        "time_window_minutes": 15,
        "total_incidents": 0,
        "high_incidents": 0,
    },
    {
        "run_id": 1,
        "started_at": "2026-09-30T09:20:00",
        "failure_threshold": 5,
        "time_window_minutes": 10,
        "total_incidents": 1,
        "high_incidents": 0,
    },
]

_DEMO_INCIDENTS: list[DetectionIncident] = [
    {
        "id": 15,
        "run_id": 3,
        "source_ip": "203.0.113.7",
        "start_ts": "2026-10-02T08:00:10",
        "end_ts": "2026-10-02T08:09:55",
        "failure_count": 5,
        "severity": "HIGH",
        "status": "NEW",
        "note": "",
        "event_ids": [101, 102, 103, 104, 105, 106],
    },
    {
        "id": 16,
        "run_id": 3,
        "source_ip": "198.51.100.42",
        "start_ts": "2026-10-02T08:04:10",
        "end_ts": "2026-10-02T08:08:33",
        "failure_count": 4,
        "severity": "MEDIUM",
        "status": "REVIEWED",
        "note": "",
        "event_ids": [107, 108, 109, 110],
    },
    {
        "id": 17,
        "run_id": 3,
        "source_ip": "192.0.2.88",
        "start_ts": "2026-10-02T08:06:41",
        "end_ts": "2026-10-02T08:09:19",
        "failure_count": 3,
        "severity": "MEDIUM",
        "status": "FALSE_POSITIVE",
        "note": "",
        "event_ids": [],
    },
    {
        "id": 9,
        "run_id": 1,
        "source_ip": "192.0.2.44",
        "start_ts": "2026-09-30T09:12:15",
        "end_ts": "2026-09-30T09:19:40",
        "failure_count": 5,
        "severity": "MEDIUM",
        "status": "REVIEWED",
        "note": "",
        "event_ids": [41, 42, 43, 44, 45],
    },
]


def get_demo_detection_runs() -> list[DetectionRunSummary]:
    """Return fresh synthetic history records; no run is started here."""
    return deepcopy(_DEMO_RUNS)


def get_empty_detection_runs() -> list[DetectionRunSummary]:
    """Return the explicit no-runs fixture for tests and visual state review."""
    return []


def get_demo_run_incidents(run_id: int) -> list[DetectionIncident]:
    """Return synthetic incidents associated only with the requested run ID."""
    return deepcopy(
        [incident for incident in _DEMO_INCIDENTS if incident["run_id"] == run_id]
    )


def demo_has_eligible_events() -> bool:
    """Report the synthetic event availability shown in demo mode."""
    return True
