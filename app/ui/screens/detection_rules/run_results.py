"""Selected run summary and incident preview table."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidgetItem, QWidget

from app.models.detection import DetectionIncident, DetectionRunSummary
from app.ui.styles.tokens import Typography
from app.ui.widgets.components import PanelCard, SeverityBadge, StatusBadge
from app.ui.widgets.styled_table import StyledTable


class RunResultsPanel(PanelCard):
    """Render incidents belonging only to the currently selected run."""

    incident_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Selected Run Results",
            "Incident results stored for the selected detection run.",
            parent=parent,
        )
        self.selected_run: DetectionRunSummary | None = None
        self.incidents: list[DetectionIncident] = []

        self.summary_label = QLabel("No detection run selected")
        self.summary_label.setObjectName("resultsSummary")
        self.summary_label.setAccessibleName("Selected detection run summary")
        self.content_layout.addWidget(self.summary_label)

        self.incidents_table = StyledTable(
            ("SOURCE IP", "START TIME", "END TIME", "FAILURES", "SEVERITY")
        )
        self.incidents_table.setAccessibleName("Incidents in selected detection run")
        self.incidents_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.incidents_table.setMinimumHeight(150)
        self.incidents_table.setWordWrap(True)
        header = self.incidents_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in enumerate((145, 116, 116, 76, 80)):
            self.incidents_table.setColumnWidth(column, width)
        header.setStretchLastSection(True)
        self.incidents_table.itemSelectionChanged.connect(self._handle_selection)
        self.content_layout.addWidget(self.incidents_table)

        self.state_label = QLabel("Select a detection run to view its stored incidents.")
        self.state_label.setObjectName("explorerEmptyState")
        self.state_label.setWordWrap(True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setMinimumHeight(100)
        self.content_layout.addWidget(self.state_label)
        self._show_state("no_selection", self.state_label.text())

    def clear_selection(self) -> None:
        self.selected_run = None
        self.incidents = []
        self.summary_label.setText("No detection run selected")
        self.summary_label.setProperty("tone", "neutral")
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(0)
        self._show_state("no_selection", "Select a detection run to view its stored incidents.")

    def set_loading(self, run: DetectionRunSummary) -> None:
        self.selected_run = run
        self.incidents = []
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(0)
        self.summary_label.setText(f"Run #{run['run_id']} · Loading stored results…")
        self._show_state("loading", f"Loading incidents for run #{run['run_id']}…")

    def set_error(self, run_id: int, message: str) -> None:
        if self.selected_run is None or self.selected_run["run_id"] != run_id:
            return
        self.incidents = []
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(0)
        self.summary_label.setText(f"Run #{run_id} · Results unavailable")
        self._show_state("error", message)

    def set_results(self, run_id: int, incidents: list[DetectionIncident]) -> bool:
        """Render matching run results and ignore stale or mismatched responses."""
        if self.selected_run is None or self.selected_run["run_id"] != run_id:
            return False
        matching = [incident for incident in incidents if incident["run_id"] == run_id]
        if incidents and not matching:
            self.set_error(run_id, "The detection service returned results for a different run.")
            return False

        self.incidents = matching
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(len(matching))
        for row, incident in enumerate(matching):
            start = _format_datetime(incident["start_ts"], multiline=True)
            end = _format_datetime(incident["end_ts"], multiline=True)
            values = (
                incident["source_ip"],
                start,
                end,
                f"{incident['failure_count']:,}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(
                    incident["start_ts"] if column == 1 else incident["end_ts"] if column == 2 else value
                )
                item.setData(Qt.ItemDataRole.UserRole, incident["id"])
                if column == 0:
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_SM))
                if column == 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif column in (1, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.incidents_table.setItem(row, column, item)

            severity = incident["severity"].upper()
            if severity in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
                badge = SeverityBadge(severity, severity)
            else:
                badge = StatusBadge(severity, "neutral")
            badge.setToolTip(f"Severity returned by the detection service: {severity}")
            self.incidents_table.setCellWidget(row, 4, badge)
            self.incidents_table.setRowHeight(row, 46)

        summary = self.selected_run
        self.summary_label.setText(
            f"{summary['total_incidents']:,} incidents detected "
            f"({summary['high_incidents']:,} HIGH) · Run #{run_id}"
        )
        if summary["total_incidents"] == 0 and not matching:
            self._show_state("zero", "This run completed with zero incidents.")
        elif matching:
            self._show_state("ready", "")
        else:
            self._show_state(
                "error",
                "The service reported incidents for this run but returned no matching incident records.",
            )
        return True

    def _show_state(self, state: str, message: str) -> None:
        self.state_label.setText(message)
        self.state_label.setObjectName(
            "explorerErrorState" if state == "error" else "explorerEmptyState"
        )
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.state_label.setVisible(state != "ready")
        self.incidents_table.setVisible(state == "ready")

    def _handle_selection(self) -> None:
        row = self.incidents_table.currentRow()
        if 0 <= row < len(self.incidents):
            self.incident_selected.emit(self.incidents[row])


def _format_datetime(value: str, *, multiline: bool = False) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d\n%H:%M" if multiline else "%Y-%m-%d %H:%M")
