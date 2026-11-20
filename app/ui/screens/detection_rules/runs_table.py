"""Detection run history table and its empty/loading/error states."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidgetItem, QWidget

from app.models.detection import DetectionRunSummary
from app.ui.widgets.components import PanelCard
from app.ui.widgets.styled_table import StyledTable


RUN_HEADERS = ("RUN ID", "DATE / TIME", "FAIL THRESH.", "WINDOW", "INCIDENTS", "HIGH INC.")
RUN_HEADER_TOOLTIPS = (
    "Run ID",
    "Date and time the detection run started",
    "Failure threshold in failed attempts",
    "Time window in minutes",
    "Total incidents returned for this run",
    "HIGH incidents returned for this run",
)


class RunsTablePanel(PanelCard):
    """Render service-provided run summaries without altering their results."""

    run_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Detection Run History",
            "Select a run to review its stored incidents.",
            parent=parent,
        )
        self.records: list[DetectionRunSummary] = []
        self.selected_run_id: int | None = None
        self.history_state = "empty"
        self.state_message: str | None = None

        self.runs_table = StyledTable(RUN_HEADERS)
        self.runs_table.setAccessibleName("Detection run history")
        header = self.runs_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(48)
        for column, (width, tooltip) in enumerate(
            zip((58, 125, 92, 87, 92, 82), RUN_HEADER_TOOLTIPS)
        ):
            self.runs_table.setColumnWidth(column, width)
            header_item = self.runs_table.horizontalHeaderItem(column)
            if header_item is not None:
                header_item.setToolTip(tooltip)
        header.setStretchLastSection(True)
        self.runs_table.setMaximumHeight(230)
        self.runs_table.itemSelectionChanged.connect(self._handle_selection)

        self.state_label = QLabel()
        self.state_label.setObjectName("explorerEmptyState")
        self.state_label.setWordWrap(True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setMinimumHeight(78)
        self.content_layout.addWidget(self.runs_table)
        self.content_layout.addWidget(self.state_label)
        self._render_state()

    def set_runs(self, records: list[DetectionRunSummary]) -> None:
        """Replace history with one service response while keeping valid selection."""
        previous_id = self.selected_run_id
        self.records = list(records)
        self.runs_table.blockSignals(True)
        self.runs_table.clearContents()
        self.runs_table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = (
                f"#{record['run_id']}",
                _format_datetime(record["started_at"]),
                str(record["failure_threshold"]),
                f"{record['time_window_minutes']} min",
                f"{record['total_incidents']:,}",
                f"{record['high_incidents']:,}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(RUN_HEADER_TOOLTIPS[column] + f": {value}")
                item.setData(Qt.ItemDataRole.UserRole, record["run_id"])
                if column >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.runs_table.setItem(row, column, item)
        self.selected_run_id = None
        if previous_id is not None:
            self._select_run_id(previous_id, notify=False)
        self.runs_table.blockSignals(False)
        self.history_state = "ready" if self.records else "empty"
        self.state_message = None
        self._render_state()

    def set_loading(self) -> None:
        self.history_state = "loading"
        self.state_message = "Loading detection runs…"
        self._render_state()

    def set_error(self, message: str) -> None:
        self.history_state = "error"
        self.state_message = message
        self._render_state()

    def upsert_run(self, record: DetectionRunSummary) -> None:
        """Add a confirmed completed run without discarding older history."""
        remaining = [item for item in self.records if item["run_id"] != record["run_id"]]
        self.set_runs([record, *remaining])

    def select_run_id(self, run_id: int, *, notify: bool = True) -> bool:
        """Select a visible historical run and notify the owning screen."""
        return self._select_run_id(run_id, notify=notify)

    def _select_run_id(self, run_id: int, *, notify: bool) -> bool:
        row = next(
            (index for index, record in enumerate(self.records) if record["run_id"] == run_id),
            None,
        )
        if row is None:
            return False
        if notify:
            already_selected = self.selected_run_id == run_id and self.runs_table.currentRow() == row
            self.runs_table.selectRow(row)
            if already_selected:
                self.run_selected.emit(self.records[row])
        else:
            self.runs_table.blockSignals(True)
            self.runs_table.selectRow(row)
            self.runs_table.blockSignals(False)
            self.selected_run_id = run_id
        return True

    def clear_selection(self) -> None:
        self.runs_table.blockSignals(True)
        self.runs_table.clearSelection()
        self.runs_table.setCurrentCell(-1, -1)
        self.runs_table.blockSignals(False)
        self.selected_run_id = None

    def _handle_selection(self) -> None:
        row = self.runs_table.currentRow()
        if 0 <= row < len(self.records):
            record = self.records[row]
            if record["run_id"] != self.selected_run_id:
                self.selected_run_id = record["run_id"]
                self.run_selected.emit(record)
        else:
            self.selected_run_id = None

    def _render_state(self) -> None:
        has_records = bool(self.records)
        self.runs_table.setVisible(has_records)
        self.state_label.setVisible(self.history_state != "ready" or not has_records)
        if self.history_state == "loading":
            message = self.state_message or "Loading detection runs…"
            self.state_label.setObjectName("explorerEmptyState")
        elif self.history_state == "error":
            if has_records:
                message = (
                    f"{self.state_message or 'Run history is unavailable.'} "
                    "Previously loaded run history is still available above."
                )
            else:
                message = self.state_message or "Run history is unavailable."
            self.state_label.setObjectName("explorerErrorState")
        elif not has_records:
            message = "No detection runs yet. Configure your rules and run detection to get started."
            self.state_label.setObjectName("explorerEmptyState")
        else:
            message = ""
            self.state_label.setObjectName("explorerEmptyState")
        self.state_label.setText(message)
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)


def _format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d %H:%M")
