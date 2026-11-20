"""Render only event evidence returned for a selected incident."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidgetItem, QWidget

from app.models.log_import import EventRecord
from app.ui.styles.tokens import Typography
from app.ui.widgets.components import PanelCard, StatusBadge
from app.ui.widgets.styled_table import StyledTable


class EvidenceTimelinePanel(PanelCard):
    """Display service-provided evidence without inferring event membership."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Linked Evidence",
            "Authentication events associated with this incident by the backend.",
            parent=parent,
        )
        self.run_id: int | None = None
        self.incident_id: int | None = None
        self.events: list[EventRecord] = []
        self.evidence_table = StyledTable(("TIME", "SRC IP", "USER", "OUTCOME", "LINE"))
        self.evidence_table.setAccessibleName("Authentication events linked to the selected incident")
        self.evidence_table.setWordWrap(True)
        self.evidence_table.setMinimumHeight(160)
        self.evidence_table.setMaximumHeight(380)
        self.evidence_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.evidence_table.setProperty("compactDensity", True)
        self.evidence_table.horizontalHeader().setProperty("compactDensity", True)
        header = self.evidence_table.horizontalHeader()
        header.setMinimumSectionSize(42)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.evidence_table.setColumnWidth(3, 86)
        self.evidence_table.setColumnWidth(4, 48)

        self.state_label = QLabel("Select an incident to view its linked evidence.")
        self.state_label.setObjectName("explorerEmptyState")
        self.state_label.setWordWrap(True)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setMinimumHeight(100)
        self.content_layout.addWidget(self.evidence_table)
        self.content_layout.addWidget(self.state_label)
        self._show_state("empty", self.state_label.text())

    def set_loading(self, run_id: int, incident_id: int) -> None:
        self.run_id = run_id
        self.incident_id = incident_id
        self.events = []
        self.evidence_table.clearContents()
        self.evidence_table.setRowCount(0)
        self._show_state("loading", "Loading linked evidence…")

    def set_evidence(
        self,
        run_id: int,
        incident_id: int,
        events: list[EventRecord],
        linked_event_ids: list[int],
    ) -> bool:
        """Render an exact, backend-returned subset; reject stale or unrelated data."""
        if (self.run_id, self.incident_id) != (run_id, incident_id):
            return False
        allowed_ids = set(linked_event_ids)
        if any(event["id"] not in allowed_ids for event in events):
            self.set_error(run_id, incident_id, "The evidence service returned an event not linked to this incident.")
            return False

        self.events = list(events)
        self.evidence_table.setRowCount(len(self.events))
        for row, event in enumerate(self.events):
            values = (
                _format_timestamp(event.get("timestamp", "")),
                event.get("source_ip", "—"),
                event.get("username", "—"),
                "",
                str(event.get("line_no", "—")),
            )
            for column, value in enumerate(values):
                if column == 3:
                    continue
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, event["id"])
                item.setToolTip(str(event.get("timestamp", value)) if column == 0 else value)
                if column in (0, 1, 4):
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_XS - 2))
                if column in (0, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.evidence_table.setItem(row, column, item)
            outcome = str(event.get("outcome", "UNKNOWN")).upper()
            tone = "error" if outcome == "FAILED" else "success" if outcome == "SUCCESS" else "neutral"
            badge = StatusBadge(outcome, tone)
            badge.setToolTip(f"Authentication outcome: {outcome}")
            self.evidence_table.setCellWidget(row, 3, badge)
            self.evidence_table.setRowHeight(row, 39)

        self._show_state("ready" if self.events else "empty", "" if self.events else "No linked evidence events were returned.")
        return True

    def set_no_linked_evidence(self, run_id: int, incident_id: int) -> None:
        if (self.run_id, self.incident_id) != (run_id, incident_id):
            return
        self.events = []
        self.evidence_table.setRowCount(0)
        self._show_state("empty", "This incident has no linked evidence events.")

    def set_unavailable(self, run_id: int, incident_id: int, message: str) -> None:
        self.set_error(run_id, incident_id, message)

    def set_error(self, run_id: int, incident_id: int, message: str) -> None:
        if (self.run_id, self.incident_id) != (run_id, incident_id):
            return
        self.events = []
        self.evidence_table.setRowCount(0)
        self._show_state("error", message)

    def clear(self, message: str = "Select an incident to view its linked evidence.") -> None:
        self.run_id = None
        self.incident_id = None
        self.events = []
        self.evidence_table.setRowCount(0)
        self._show_state("empty", message)

    def _show_state(self, state: str, message: str) -> None:
        self.state_label.setText(message)
        self.state_label.setObjectName("explorerErrorState" if state == "error" else "explorerEmptyState")
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.state_label.setVisible(state != "ready")
        self.evidence_table.setVisible(state == "ready")


def _format_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value or "—"
    return parsed.strftime("%Y-%m-%d\n%H:%M")
