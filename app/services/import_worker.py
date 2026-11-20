"""Qt worker for local log file import."""

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    progress = Signal(object)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, service, path: str) -> None:
        super().__init__()
        self.service = service
        self.path = Path(path)

    def run(self) -> None:
        try:
            result = self.service.import_log_file(
                self.path, progress_callback=self.progress.emit
            )
        except Exception as error:
            logger.exception("Log import failed for %s", self.path)
            self.failed.emit(str(error) or error.__class__.__name__)
        else:
            self.completed.emit(result)
