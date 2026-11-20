"""UI-facing service protocols for import, event, and detection workflows.

These protocols describe future integration boundaries; they are not
implementations. Service methods use plain Python values and do not import
PySide6. The Qt worker adapter runs detection service calls outside the GUI
thread and relays optional progress and responses through Qt signals.
Event queries and IP details come from backend responses, not visible rows.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from app.models.detection import (
    DetectionIncident,
    DetectionProgress,
    DetectionRunRequest,
    DetectionRunResult,
    DetectionRunSummary,
)
from app.models.log_import import (
    EventFilters,
    EventPage,
    ImportHistoryPage,
    ImportHistoryRecord,
    ImportProgress,
    IPDetails,
    MalformedRecord,
)


class ImportService(Protocol):
    """Import files, list import history, and retrieve parser diagnostics."""

    def import_log_file(
        self,
        file_path: Path,
        progress_callback: Callable[[ImportProgress], None] | None = None,
    ) -> ImportHistoryRecord: ...

    def get_import_history(self, *, page: int, page_size: int) -> ImportHistoryPage: ...

    def get_malformed_records(self, import_id: int) -> list[MalformedRecord]: ...


class EventService(Protocol):
    """Return filtered event pages and backend-calculated source summaries."""

    def get_events(
        self,
        filters: EventFilters,
        *,
        page: int,
        page_size: int,
    ) -> EventPage: ...

    def get_ip_details(self, source_ip: str) -> IPDetails | None: ...

    def get_linked_events(self, event_ids: list[int]) -> list[dict]: ...

    def has_eligible_events(self) -> bool:
        """Return whether imported authentication events are eligible for detection."""


class DetectionService(Protocol):
    """Expose run operations without importing Qt or defining detection semantics."""

    def run_detection(
        self,
        request: DetectionRunRequest,
        *,
        progress_callback: Callable[[DetectionProgress], None] | None = None,
    ) -> DetectionRunResult: ...

    def get_run_history(self) -> list[DetectionRunSummary]: ...

    def get_run_results(self, run_id: int) -> list[DetectionIncident]: ...

    def save_review(
        self, run_id: int, incident_id: int, status: str, note: str
    ) -> DetectionIncident: ...

    def export_report(self, run_id: int, format_name: str, destination: str) -> str: ...
