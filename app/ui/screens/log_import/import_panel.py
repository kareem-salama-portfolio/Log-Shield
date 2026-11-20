"""Local log-file selection state and empty import-history view."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.log_import import ImportHistoryRecord
from app.ui.styles.tokens import Spacing, Typography
from app.ui.widgets.components import PanelCard, PrimaryButton, SecondaryButton, StatusBadge
from app.ui.widgets.styled_table import StyledTable
from app.utils.file_validation import MAX_LOG_FILE_SIZE_BYTES


class ImportPanel(PanelCard):
    """Compact import controls; it never opens, parses, or imports file data."""

    file_picker_requested = Signal()
    malformed_records_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Import Authentication Logs",
            "Select a local log file for the import service.",
            parent=parent,
        )
        self.selected_path: Path | None = None
        self.import_id: int | None = None
        self.state = "idle"

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(Spacing.MD)
        self.import_button = PrimaryButton("Import Log File", "file-plus")
        self.import_button.clicked.connect(self.file_picker_requested.emit)
        action_row.addWidget(self.import_button, 0)

        format_copy = QVBoxLayout()
        format_copy.setContentsMargins(0, 0, 0, 0)
        format_copy.setSpacing(Spacing.XXS)
        self.supported_formats_label = QLabel("SUPPORTED FORMATS   .log  ·  .txt")
        self.supported_formats_label.setObjectName("fieldHint")
        self.max_size_label = QLabel("MAXIMUM FILE SIZE   20 MB")
        self.max_size_label.setObjectName("fieldHint")
        self.max_size_label.setAccessibleName(
            f"Maximum file size {MAX_LOG_FILE_SIZE_BYTES // (1024 * 1024)} megabytes"
        )
        format_copy.addWidget(self.supported_formats_label)
        format_copy.addWidget(self.max_size_label)
        action_row.addLayout(format_copy, 1)
        action_row.addStretch(1)
        self.content_layout.addLayout(action_row)

        self.selected_file_label = QLabel("No file selected")
        self.selected_file_label.setObjectName("fieldHint")
        self.selected_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_layout.addWidget(self.selected_file_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("importProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.progress_bar.setAccessibleName("Import progress")
        self.content_layout.addWidget(self.progress_bar)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(Spacing.MD)
        self.status_badge = StatusBadge("READY", "neutral")
        status_row.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.status_label = QLabel("Waiting for a log file.")
        self.status_label.setObjectName("operationStatus")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_label, 1)
        self.content_layout.addLayout(status_row)

        counts_row = QHBoxLayout()
        counts_row.setContentsMargins(0, 0, 0, 0)
        counts_row.setSpacing(Spacing.MD)
        self.accepted_count_label = QLabel("Accepted records: 0")
        self.accepted_count_label.setObjectName("fieldHint")
        counts_row.addWidget(self.accepted_count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        counts_row.addStretch(1)
        self.malformed_button = SecondaryButton("Malformed records: 0")
        self.malformed_button.setMinimumHeight(30)
        self.malformed_button.setEnabled(False)
        self.malformed_button.clicked.connect(self._request_malformed_records)
        counts_row.addWidget(self.malformed_button, 0, Qt.AlignmentFlag.AlignRight)
        self.content_layout.addLayout(counts_row)

    def set_selected_file(self, path: Path) -> None:
        """Display selection before the import integration is checked."""
        self.selected_path = path
        self.import_id = None
        self.selected_file_label.setText(path.name)
        self.selected_file_label.setToolTip(str(path))
        self._set_state(
            "pending",
            "SERVICE PENDING",
            "The file passed local checks, but no import service is connected. It was not imported.",
            "warning",
        )
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.accepted_count_label.setText("Accepted records: —")
        self._set_malformed_count(None, 0)

    def set_validation_error(self, message: str) -> None:
        """Show a local extension, access, or file-size validation failure."""
        self.selected_path = None
        self.selected_file_label.setText("No valid file selected")
        self._set_state("error", "FILE NOT ACCEPTED", message, "error")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

    def set_importing(self, file_name: str) -> None:
        """Prepare the display for a future worker-driven import operation."""
        self.state = "importing"
        self.selected_file_label.setText(file_name)
        self.status_badge.setText("IMPORTING")
        self.status_badge.setProperty("tone", "info")
        self.status_label.setText("Import in progress…")
        self.status_label.setProperty("tone", "info")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.import_button.setEnabled(False)
        self._refresh_status_styles()

    def update_progress(self, percentage: int, status: str = "Import in progress…") -> None:
        """Accept a worker progress update on the GUI thread."""
        if self.state != "importing":
            self.set_importing(self.selected_file_label.text())
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(100, int(percentage))))
        self.status_label.setText(status)

    def set_import_result(self, record: ImportHistoryRecord) -> None:
        """Render a result supplied only after a real import service confirms it."""
        self.import_id = record["import_id"]
        self.selected_file_label.setText(record["file_name"])
        self.accepted_count_label.setText(f"Accepted records: {record['accepted_records']:,}")
        self._set_malformed_count(self.import_id, record["malformed_records"])
        self.progress_bar.setRange(0, 100)
        self.import_button.setEnabled(True)

        status = record["status"].strip().upper()
        if status in {"FAILED", "ERROR"}:
            self.progress_bar.setValue(0)
            self._set_state("error", "IMPORT FAILED", "The import service reported a failure.", "error")
        elif status in {"PARTIAL", "WARNING", "COMPLETED_WITH_WARNINGS"}:
            self.progress_bar.setValue(100)
            self._set_state(
                "warning",
                "IMPORTED WITH WARNINGS",
                "The import service completed with warnings. Review malformed records if available.",
                "warning",
            )
        elif status in {"COMPLETED", "COMPLETE", "SUCCESS", "IMPORTED"}:
            self.progress_bar.setValue(100)
            self._set_state("completed", "IMPORT COMPLETE", "Import completed.", "success")
        else:
            self.progress_bar.setValue(0)
            self._set_state(
                "unknown",
                "IMPORT STATUS",
                f"The import service returned status: {record['status']}.",
                "neutral",
            )

    def set_import_failed(self, message: str) -> None:
        """Display an explicit import-service failure."""
        self._set_state("error", "IMPORT FAILED", message, "error")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.import_button.setEnabled(True)

    def _set_malformed_count(self, import_id: int | None, count: int) -> None:
        self.import_id = import_id
        self.malformed_button.setText(f"Malformed records: {count:,}")
        self.malformed_button.setEnabled(count > 0 and import_id is not None)
        if self.malformed_button.isEnabled():
            self.malformed_button.setToolTip("Open malformed records for this import.")
        else:
            self.malformed_button.setToolTip("No malformed-record details are available.")

    def _request_malformed_records(self) -> None:
        if self.import_id is not None and self.malformed_button.isEnabled():
            self.malformed_records_requested.emit(self.import_id)

    def _set_state(self, state: str, badge: str, message: str, tone: str) -> None:
        self.state = state
        self.status_badge.setText(badge)
        self.status_badge.setProperty("tone", tone)
        self.status_label.setText(message)
        self.status_label.setProperty("tone", tone)
        self._refresh_status_styles()

    def _refresh_status_styles(self) -> None:
        for widget in (self.status_badge, self.status_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


class ImportHistoryPanel(PanelCard):
    """Paginated-history presentation with a clean first-run empty state."""

    malformed_records_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Import History", "Previous file imports on this device.", parent=parent)
        self.history_table = StyledTable(
            ("FILE NAME", "IMPORT DATE", "TOTAL", "ACCEPTED", "MALFORMED", "STATUS")
        )
        self.history_table.setAccessibleName("Log import history")
        self.history_table.setMaximumHeight(190)
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        history_header.setMinimumSectionSize(48)
        for column, width in enumerate((120, 118, 52, 70, 88, 84)):
            self.history_table.setColumnWidth(column, width)
        history_header.setStretchLastSection(True)
        self.history_table.cellClicked.connect(self._handle_cell_clicked)
        self.empty_label = QLabel("No previous imports")
        self.empty_label.setObjectName("explorerEmptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(58)
        self.content_layout.addWidget(self.history_table)
        self.content_layout.addWidget(self.empty_label)
        self.set_records([])

    def set_records(self, records: list[ImportHistoryRecord]) -> None:
        self.records = list(records)
        self.history_table.setRowCount(len(records))
        self.history_table.setVisible(bool(records))
        self.empty_label.setVisible(not records)
        for row, record in enumerate(records):
            values = (
                record["file_name"],
                _format_datetime(record["imported_at"]),
                f"{record['total_records']:,}",
                f"{record['accepted_records']:,}",
                f"{record['malformed_records']:,}",
                _format_history_status(record["status"]),
            )
            for column, value in enumerate(values):
                if column == 5:
                    tone = _import_status_tone(record["status"])
                    badge = StatusBadge(value, tone)
                    badge.setToolTip(record["status"].replace("_", " ").upper())
                    badge.setAccessibleName(
                        f"Import status: {record['status'].replace('_', ' ').upper()}"
                    )
                    self.history_table.setCellWidget(row, column, badge)
                    continue
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setData(Qt.ItemDataRole.UserRole, record["import_id"])
                if column in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif column == 0:
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_SM))
                self.history_table.setItem(row, column, item)
        self.history_table.resizeRowsToContents()

    def _handle_cell_clicked(self, row: int, column: int) -> None:
        if column == 4 and 0 <= row < len(self.records) and self.records[row]["malformed_records"] > 0:
            import_id = self.records[row]["import_id"]
            self.malformed_records_requested.emit(import_id)


def _format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d %H:%M")


def _format_history_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized in {"COMPLETE", "COMPLETED", "SUCCESS", "IMPORTED"}:
        return "COMPLETE"
    if normalized in {"PARTIAL", "WARNING", "COMPLETED_WITH_WARNINGS"}:
        return "PARTIAL"
    if normalized in {"FAILED", "ERROR"}:
        return "FAILED"
    if normalized in {"IN_PROGRESS", "RUNNING"}:
        return "RUNNING"
    display = normalized.replace("_", " ")
    return display if len(display) <= 10 else f"{display[:9]}…"


def _import_status_tone(status: str) -> str:
    normalized = status.upper()
    if normalized in {"FAILED", "ERROR"}:
        return "error"
    if normalized in {"PARTIAL", "WARNING", "COMPLETED_WITH_WARNINGS"}:
        return "warning"
    if normalized in {"COMPLETE", "COMPLETED", "SUCCESS", "IMPORTED"}:
        return "success"
    return "neutral"
