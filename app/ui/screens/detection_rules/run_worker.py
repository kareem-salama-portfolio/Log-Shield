"""Qt worker adapter for detection service requests."""

import logging
from typing import Literal

from PySide6.QtCore import QThread, Signal

from app.models.detection import (
    DetectionProgress,
    DetectionRunRequest,
    DetectionRunResult,
)
from app.services.ui_contracts import DetectionService


logger = logging.getLogger(__name__)

DetectionOperation = Literal["history", "results", "run"]


class DetectionServiceWorker(QThread):
    """Run history, result, or detection calls away from the GUI thread."""

    progress_received = Signal(object)
    request_completed = Signal(str, int, object)
    request_failed = Signal(str, int, str)

    def __init__(
        self,
        service: DetectionService,
        operation: DetectionOperation,
        *,
        request: DetectionRunRequest | None = None,
        run_id: int = 0,
    ) -> None:
        super().__init__()
        self._service = service
        self._operation = operation
        self._request = dict(request) if request is not None else None
        self._run_id = run_id

    def run(self) -> None:
        try:
            if self._operation == "history":
                result = self._service.get_run_history()
            elif self._operation == "results":
                result = self._service.get_run_results(self._run_id)
            elif self._operation == "run" and self._request is not None:
                result: DetectionRunResult = self._service.run_detection(
                    self._request,
                    progress_callback=self._forward_progress,
                )
            else:
                raise ValueError("Detection worker request is incomplete.")
        except (
            Exception
        ) as error:  # Service failures return to the UI as a clear state.
            logger.exception("Detection service operation %s failed", self._operation)
            message = str(error).strip() or error.__class__.__name__
            self.request_failed.emit(self._operation, self._run_id, message)
        else:
            self.request_completed.emit(self._operation, self._run_id, result)

    def _forward_progress(self, progress: DetectionProgress) -> None:
        self.progress_received.emit(dict(progress))
