"""Read-only details for the currently selected incident."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from app.models.detection import DetectionIncident
from app.ui.styles.tokens import Spacing, Typography
from app.ui.widgets.components import PanelCard, SeverityBadge, StatusBadge


class IncidentDetailsPanel(PanelCard):
    """Show fields from the incident contract without deriving new values."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Incident Details",
            "Values returned for the selected incident.",
            parent=parent,
        )
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(Spacing.MD)
        grid.setVerticalSpacing(Spacing.SM)
        self.content_layout.addLayout(grid)

        self.values: dict[str, QLabel] = {}
        labels = (
            ("incident_id", "Incident ID"),
            ("source_ip", "Source IP"),
            ("start_ts", "Start timestamp"),
            ("end_ts", "End timestamp"),
            ("failure_count", "Failure count"),
            ("run_id", "Detection run ID"),
        )
        for index, (key, label_text) in enumerate(labels):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("detailMetricValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            if key in {"source_ip", "start_ts", "end_ts"}:
                value.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_SM))
            grid.addWidget(label, row, column)
            grid.addWidget(value, row, column + 1)
            self.values[key] = value

        self.severity_label = QLabel("Severity")
        self.severity_label.setObjectName("fieldLabel")
        self.severity_badge = SeverityBadge("UNKNOWN", "UNKNOWN")
        grid.addWidget(self.severity_label, 3, 0)
        grid.addWidget(self.severity_badge, 3, 1, Qt.AlignmentFlag.AlignLeft)

        review_label = QLabel("Review status")
        review_label.setObjectName("fieldLabel")
        self.review_badge = StatusBadge("UNKNOWN", "neutral")
        grid.addWidget(review_label, 4, 0)
        grid.addWidget(self.review_badge, 4, 1, Qt.AlignmentFlag.AlignLeft)

        note_label = QLabel("Current note")
        note_label.setObjectName("fieldLabel")
        self.note_value = QLabel("—")
        self.note_value.setObjectName("resultsSummary")
        self.note_value.setWordWrap(True)
        self.note_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(note_label, 5, 0)
        grid.addWidget(self.note_value, 5, 1, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

    def set_incident(self, incident: DetectionIncident | None) -> None:
        if incident is None:
            for value in self.values.values():
                value.setText("—")
                value.setToolTip("")
            self._set_severity("UNKNOWN")
            self._set_review_status("UNKNOWN")
            self.note_value.setText("—")
            self.note_value.setToolTip("")
            return

        self.values["incident_id"].setText(f"#{incident['id']}")
        self.values["source_ip"].setText(incident["source_ip"])
        self.values["start_ts"].setText(_format_datetime(incident["start_ts"]))
        self.values["end_ts"].setText(_format_datetime(incident["end_ts"]))
        self.values["failure_count"].setText(f"{incident['failure_count']:,}")
        self.values["run_id"].setText(f"#{incident['run_id']}")
        self.values["start_ts"].setToolTip(incident["start_ts"])
        self.values["end_ts"].setToolTip(incident["end_ts"])
        self.values["source_ip"].setToolTip(incident["source_ip"])
        self._set_severity(incident["severity"])
        self._set_review_status(incident["status"])
        note = incident["note"] or "—"
        self.note_value.setText(note)
        self.note_value.setToolTip(note)

    def _set_severity(self, severity: str) -> None:
        normalized = severity.upper()
        if normalized not in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
            normalized = "UNKNOWN"
        self.severity_badge.setText(normalized)
        self.severity_badge.setProperty("severity", normalized)
        self.severity_badge.setAccessibleName(f"{normalized} severity")
        self.severity_badge.style().unpolish(self.severity_badge)
        self.severity_badge.style().polish(self.severity_badge)

    def _set_review_status(self, status: str) -> None:
        normalized = status.upper()
        label = normalized.replace("_", " ")
        tone = {
            "NEW": "info",
            "REVIEWED": "success",
            "FALSE_POSITIVE": "warning",
        }.get(normalized, "neutral")
        self.review_badge.setText(label)
        self.review_badge.setProperty("tone", tone)
        self.review_badge.setAccessibleName(f"Review status: {label}")
        self.review_badge.style().unpolish(self.review_badge)
        self.review_badge.style().polish(self.review_badge)


def _format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d %H:%M:%S")
