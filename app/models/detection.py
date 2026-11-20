"""Plain request and response shapes for detection runs and incidents."""

from typing import NotRequired, TypedDict


class DetectionRunRequest(TypedDict):
    """Parameters agreed for a run; HIGH-severity UI state is intentionally omitted."""

    failure_threshold: int
    time_window_minutes: int


class DetectionRunSummary(TypedDict):
    """Persisted run fields needed by history and the results summary."""

    run_id: int
    started_at: str
    failure_threshold: int
    time_window_minutes: int
    total_incidents: int
    high_incidents: int


class DetectionIncident(TypedDict):
    """Incident shape shared with the Incidents & Reports screen."""

    id: int
    run_id: int
    source_ip: str
    start_ts: str
    end_ts: str
    failure_count: int
    severity: str
    status: str
    note: str
    event_ids: list[int]
    status_updated_at: NotRequired[str]


class DetectionRunResult(TypedDict):
    """Confirmed result returned after a detection service completes a run."""

    run: DetectionRunSummary
    incidents: list[DetectionIncident]


class DetectionProgress(TypedDict, total=False):
    """Optional backend progress; percentage is absent when not supplied."""

    percentage: NotRequired[int]
    status: NotRequired[str]
