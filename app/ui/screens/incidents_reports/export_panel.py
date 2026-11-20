"""Run-level CSV/JSON export actions using the native save-file dialog."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QWidget

from app.models.detection import DetectionRunSummary
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PanelCard, PrimaryButton, SecondaryButton, StatusBadge


class ExportPanel(PanelCard):
    """Choose an export destination and emit a request without writing files."""

    export_requested = Signal(int, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Export Reports",
            "Export the selected detection run through the report service.",
            parent=parent,
        )
        self.selected_run: DetectionRunSummary | None = None
        self._exporting = False
        self._exporting_run_id: int | None = None

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.SM)
        self.csv_button = PrimaryButton("Export CSV", "download")
        self.csv_button.setAccessibleName("Export selected detection run as CSV")
        self.json_button = SecondaryButton("Export JSON", "download")
        self.json_button.setAccessibleName("Export selected detection run as JSON")
        self.csv_button.clicked.connect(lambda: self.choose_export_destination("csv"))
        self.json_button.clicked.connect(lambda: self.choose_export_destination("json"))
        row.addWidget(self.csv_button)
        row.addWidget(self.json_button)
        row.addStretch(1)

        self.state_badge = StatusBadge("NO RUN", "neutral")
        row.addWidget(self.state_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self.content_layout.addLayout(row)

        self.state_message = QLabel("Select a detection run to enable report export.")
        self.state_message.setObjectName("operationStatus")
        self.state_message.setWordWrap(True)
        self.content_layout.addWidget(self.state_message)
        self.set_selected_run(None)

    def set_selected_run(self, run: DetectionRunSummary | None) -> None:
        self.selected_run = dict(run) if run is not None else None
        self._exporting = False
        self._exporting_run_id = None
        self._update_buttons()
        if run is None:
            self._set_status("NO RUN", "Select a detection run to enable report export.", "neutral")
        elif run["total_incidents"] == 0:
            self._set_status(
                "READY",
                f"Run #{run['run_id']} contains 0 incidents. CSV and JSON export remain available.",
                "info",
            )
        else:
            self._set_status(
                "READY",
                f"Run #{run['run_id']} · {run['total_incidents']:,} incidents · "
                f"{run['high_incidents']:,} HIGH.",
                "neutral",
            )

    def choose_export_destination(self, export_format: str) -> bool:
        """Ask for a destination, then emit a service request if not cancelled."""
        normalized = export_format.lower()
        if normalized not in {"csv", "json"} or self.selected_run is None or self._exporting:
            return False
        run_id = self.selected_run["run_id"]
        default_name = f"logshield-run-{run_id}.{normalized}"
        selected, _selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export Run #{run_id} as {normalized.upper()}",
            default_name,
            f"{normalized.upper()} files (*.{normalized})",
        )
        if not selected:
            return False

        destination = Path(selected)
        expected_suffix = f".{normalized}"
        if destination.suffix.lower() != expected_suffix:
            destination = destination.with_suffix(expected_suffix) if destination.suffix else Path(f"{destination}{expected_suffix}")
        self.set_exporting(normalized)
        self.export_requested.emit(run_id, normalized, str(destination))
        return True

    def set_exporting(self, export_format: str) -> bool:
        """Show the pending state while a connected export service is working."""
        normalized = export_format.lower()
        if normalized not in {"csv", "json"} or self.selected_run is None or self._exporting:
            return False
        self._exporting = True
        self._exporting_run_id = self.selected_run["run_id"]
        self._update_buttons()
        self._set_status(
            "EXPORTING",
            f"Waiting for the export service to create the {normalized.upper()} report…",
            "info",
        )
        return True

    def set_export_success(self, path: str, run_id: int | None = None) -> bool:
        if run_id is not None and (
            self.selected_run is None
            or run_id != self._exporting_run_id
            or run_id != self.selected_run["run_id"]
        ):
            return False
        self._exporting = False
        self._exporting_run_id = None
        self._update_buttons()
        self._set_status("EXPORTED", f"Report exported to {Path(path).name}.", "success")
        return True

    def set_export_failure(self, message: str, run_id: int | None = None) -> bool:
        if run_id is not None and (
            self.selected_run is None
            or run_id != self._exporting_run_id
            or run_id != self.selected_run["run_id"]
        ):
            return False
        self._exporting = False
        self._exporting_run_id = None
        self._update_buttons()
        self._set_status("EXPORT FAILED", message, "error")
        return True

    def _update_buttons(self) -> None:
        enabled = self.selected_run is not None and not self._exporting
        self.csv_button.setEnabled(enabled)
        self.json_button.setEnabled(enabled)

    def _set_status(self, badge: str, message: str, tone: str) -> None:
        self.state_badge.setText(badge)
        self.state_badge.setProperty("tone", tone)
        self.state_message.setText(message)
        self.state_message.setProperty("tone", tone)
        for widget in (self.state_badge, self.state_message):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
