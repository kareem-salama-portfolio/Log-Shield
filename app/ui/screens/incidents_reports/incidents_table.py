"""Incident list for the currently selected detection run."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidgetItem, QWidget

from app.models.detection import DetectionIncident
from app.ui.styles.tokens import Typography
from app.ui.widgets.components import PanelCard, SeverityBadge, StatusBadge
from app.ui.widgets.styled_table import StyledTable


class IncidentsTablePanel(PanelCard):
    """Display incidents returned for one run without mixing other run IDs."""

    incident_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Incidents",
            "Incidents belonging to the selected detection run.",
            parent=parent,
        )
        self.records: list[DetectionIncident] = []
        self.selected_incident_id: int | None = None
        self.run_id: int | None = None
        self.expected_count: int | None = None
        self._compact = False

        self.incidents_table = StyledTable(
            ("ID", "SOURCE IP", "SEVERITY", "FAILURES", "START", "END", "STATUS")
        )
        self.incidents_table.setAccessibleName("Incidents for the selected detection run")
        self.incidents_table.setWordWrap(True)
        self.incidents_table.setMinimumHeight(180)
        self.incidents_table.setMaximumHeight(360)
        self.incidents_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.incidents_table.setProperty("compactDensity", True)
        self.incidents_table.horizontalHeader().setProperty("compactDensity", True)
        self.incidents_table.setCursor(Qt.CursorShape.PointingHandCursor)
        header = self.incidents_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(48)
        for column, width in ((0, 58), (2, 76), (3, 62), (6, 104)):
            self.incidents_table.setColumnWidth(column, width)
        for column in (1, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)
        self.incidents_table.itemSelectionChanged.connect(self._handle_selection)

        self.state_label = QLabel("Select a detection run to view its incidents.")
        self.state_label.setObjectName("explorerEmptyState")
        self.state_label.setWordWrap(True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setMinimumHeight(115)
        self.content_layout.addWidget(self.incidents_table)
        self.content_layout.addWidget(self.state_label)
        self._show_state("empty", self.state_label.text())

    def set_compact_columns(self, compact: bool) -> None:
        if self._compact == compact:
            return
        self._compact = compact
        widths = (48, 70, 68, 128) if compact else (58, 78, 70, 132)
        for column, width in zip((0, 2, 3, 6), widths):
            self.incidents_table.setColumnWidth(column, width)
        if self.run_id is not None:
            self.set_incidents(self.run_id, self.records, self.expected_count)

    def set_loading(self, run_id: int) -> None:
        self.run_id = run_id
        self.expected_count = None
        self.records = []
        self.selected_incident_id = None
        self.incidents_table.blockSignals(True)
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(0)
        self.incidents_table.blockSignals(False)
        self._show_state("loading", f"Loading incidents for run #{run_id}…")

    def set_error(self, run_id: int, message: str) -> None:
        if self.run_id != run_id:
            return
        self.records = []
        self.selected_incident_id = None
        self.incidents_table.setRowCount(0)
        self._show_state("error", message)

    def clear(self, message: str = "Select a detection run to view its incidents.") -> None:
        self.run_id = None
        self.expected_count = None
        self.records = []
        self.selected_incident_id = None
        self.incidents_table.blockSignals(True)
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(0)
        self.incidents_table.blockSignals(False)
        self._show_state("empty", message)

    def set_incidents(
        self,
        run_id: int,
        incidents: list[DetectionIncident],
        expected_count: int | None,
    ) -> bool:
        """Render only records for the requested run and reject mixed responses."""
        if self.run_id != run_id:
            return False
        mismatched = [item for item in incidents if item["run_id"] != run_id]
        if mismatched:
            self.records = []
            self.selected_incident_id = None
            self.incidents_table.setRowCount(0)
            self._show_state(
                "error",
                "The detection service returned incidents for a different run. No incidents were displayed.",
            )
            return False

        previous_id = self.selected_incident_id
        self.expected_count = expected_count
        self.records = list(incidents)
        self.incidents_table.blockSignals(True)
        self.incidents_table.clearContents()
        self.incidents_table.setRowCount(len(self.records))
        for row, incident in enumerate(self.records):
            values = (
                f"#{incident['id']}",
                _format_ip(incident["source_ip"], compact=self._compact),
                "",
                f"{incident['failure_count']:,}",
                _format_datetime(incident["start_ts"], compact=self._compact),
                _format_datetime(incident["end_ts"], compact=self._compact),
                "",
            )
            for column, value in enumerate(values):
                if column in (2, 6):
                    continue
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, incident["id"])
                item.setToolTip(
                    incident["start_ts"] if column == 4 else incident["end_ts"] if column == 5 else value
                )
                if column == 1:
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_XS - 2))
                elif column in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if column in (4, 5):
                        item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_XS - 2))
                self.incidents_table.setItem(row, column, item)
            severity = incident["severity"].upper()
            if severity in {"MEDIUM", "HIGH"}:
                severity_badge = SeverityBadge(severity, severity)
            else:
                severity_badge = StatusBadge(severity, "neutral")
            severity_badge.setToolTip(f"Severity returned for incident #{incident['id']}: {severity}")
            self.incidents_table.setCellWidget(row, 2, severity_badge)

            status = incident["status"].upper()
            status_label = status.replace("_", " ")
            tone = {
                "NEW": "info",
                "REVIEWED": "success",
                "FALSE_POSITIVE": "warning",
            }.get(status, "neutral")
            status_badge = StatusBadge(status_label, tone)
            status_badge.setWordWrap(True)
            status_badge.setToolTip(f"Review status: {status_label}")
            self.incidents_table.setCellWidget(row, 6, status_badge)
            self.incidents_table.setRowHeight(row, 46)

        self.selected_incident_id = None
        if previous_id is not None:
            self._select_incident_id(previous_id, notify=False)
        self.incidents_table.blockSignals(False)
        if self.records:
            self._show_state("ready", "")
        elif expected_count == 0:
            self._show_state("zero", "This detection run contains 0 incidents. CSV and JSON export remain available.")
        elif expected_count is not None:
            self._show_state(
                "error",
                f"The run summary reports {expected_count} incidents, but no incident records were returned.",
            )
        else:
            self._show_state("empty", "No incidents were returned for the selected run.")
        return True

    def select_incident_id(self, incident_id: int, *, notify: bool = True) -> bool:
        return self._select_incident_id(incident_id, notify=notify)

    def clear_selection(self) -> None:
        self.incidents_table.blockSignals(True)
        self.incidents_table.clearSelection()
        self.incidents_table.setCurrentCell(-1, -1)
        self.incidents_table.blockSignals(False)
        self.selected_incident_id = None

    def _select_incident_id(self, incident_id: int, *, notify: bool) -> bool:
        row = next(
            (index for index, record in enumerate(self.records) if record["id"] == incident_id),
            None,
        )
        if row is None:
            return False
        if not notify:
            self.incidents_table.blockSignals(True)
            self.incidents_table.selectRow(row)
            self.incidents_table.blockSignals(False)
            self.selected_incident_id = incident_id
            return True
        already_selected = (
            self.selected_incident_id == incident_id
            and self.incidents_table.currentRow() == row
        )
        self.incidents_table.selectRow(row)
        if already_selected:
            self.incident_selected.emit(self.records[row])
        return True

    def _handle_selection(self) -> None:
        row = self.incidents_table.currentRow()
        if 0 <= row < len(self.records):
            record = self.records[row]
            if record["id"] != self.selected_incident_id:
                self.selected_incident_id = record["id"]
                self.incident_selected.emit(record)

    def _show_state(self, state: str, message: str) -> None:
        self.state_label.setText(message)
        self.state_label.setObjectName("explorerErrorState" if state == "error" else "explorerEmptyState")
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.state_label.setVisible(state != "ready")
        self.incidents_table.setVisible(state == "ready")


def _format_datetime(value: str, *, compact: bool = False) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value
    if compact:
        return parsed.strftime("%m-%d\n%H:%M")
    return parsed.strftime("%Y-%m-%d\n%H:%M")


def _format_ip(value: str, *, compact: bool) -> str:
    """Wrap the full IP into two lines in narrow tables; tooltip stays complete."""
    if not compact:
        return value
    parts = value.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.\n{parts[2]}.{parts[3]}"
    return value
