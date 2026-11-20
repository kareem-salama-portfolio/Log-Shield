"""Incidents & Reports screen with explicit service boundaries."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.detection import DetectionIncident, DetectionRunSummary
from app.models.log_import import EventRecord
from app.ui.screens.incidents_reports.evidence_timeline import EvidenceTimelinePanel
from app.ui.screens.incidents_reports.export_panel import ExportPanel
from app.ui.screens.incidents_reports.incident_details import IncidentDetailsPanel
from app.ui.screens.incidents_reports.incident_editor import IncidentEditorPanel, UnsavedChangesDialog
from app.ui.screens.incidents_reports.incidents_table import IncidentsTablePanel
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PageHeader, PanelCard, StatusBadge


class IncidentsReportsScreen(QWidget):
    """Present incidents for one run and relay review/evidence/export requests."""

    run_selected = Signal(int)
    evidence_requested = Signal(int, int, object)
    save_requested = Signal(int, int, str, str)
    export_requested = Signal(int, str, str)
    navigation_allowed = Signal(str)

    _COMPACT = "compact"
    _WIDE = "wide"

    def __init__(self, demo_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardContent")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.demo_mode = demo_mode
        self.run_summaries: list[DetectionRunSummary] = []
        self.selected_run: DetectionRunSummary | None = None
        self.selected_incident: DetectionIncident | None = None
        self._active_incidents: list[DetectionIncident] = []
        self._run_history_state = "empty"
        self._pending_action: tuple[str, object] | None = None
        self._unsaved_dialog: UnsavedChangesDialog | None = None
        self._layout_mode: str | None = None

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        self.root_layout.setSpacing(Spacing.LG)
        self.demo_badge = StatusBadge("SYNTHETIC DEMO", "info") if demo_mode else None
        if self.demo_badge is not None:
            self.demo_badge.setAccessibleName("Synthetic demonstration data; these are not imported log records")
        self.root_layout.addWidget(
            PageHeader(
                "Incidents & Reports",
                "Review detection findings, inspect linked authentication evidence, and export run reports.",
                action=self.demo_badge,
            )
        )

        self.top_grid = QGridLayout()
        self.top_grid.setContentsMargins(0, 0, 0, 0)
        self.top_grid.setHorizontalSpacing(Spacing.MD)
        self.top_grid.setVerticalSpacing(Spacing.MD)
        self.run_panel = PanelCard(
            "Detection Run",
            "Incidents and exports are scoped to one selected run.",
        )
        selector_row = QHBoxLayout()
        selector_row.setContentsMargins(0, 0, 0, 0)
        selector_row.setSpacing(Spacing.SM)
        self.run_selector = QComboBox()
        self.run_selector.setAccessibleName("Detection run for incidents and reports")
        self.run_selector.addItem("Select a detection run…", None)
        selector_row.addWidget(self.run_selector, 1)
        self.run_state_badge = StatusBadge("NO RUNS", "neutral")
        selector_row.addWidget(self.run_state_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self.run_panel.content_layout.addLayout(selector_row)
        self.run_summary_label = QLabel("No detection runs available. Run detection to create a run to review.")
        self.run_summary_label.setObjectName("operationStatus")
        self.run_summary_label.setWordWrap(True)
        self.run_panel.content_layout.addWidget(self.run_summary_label)
        self.export_panel = ExportPanel()
        self.top_grid.addWidget(self.run_panel, 0, 0)
        self.top_grid.addWidget(self.export_panel, 0, 1)
        self.root_layout.addLayout(self.top_grid)

        self.incidents_panel = IncidentsTablePanel()
        self.root_layout.addWidget(self.incidents_panel)

        self.detail_grid = QGridLayout()
        self.detail_grid.setContentsMargins(0, 0, 0, 0)
        self.detail_grid.setHorizontalSpacing(Spacing.MD)
        self.detail_grid.setVerticalSpacing(Spacing.MD)
        self.details_panel = IncidentDetailsPanel()
        self.evidence_panel = EvidenceTimelinePanel()
        self.editor_panel = IncidentEditorPanel()
        self.detail_grid.addWidget(self.details_panel, 0, 0)
        self.detail_grid.addWidget(self.evidence_panel, 0, 1)
        self.detail_grid.addWidget(self.editor_panel, 0, 2)
        self.root_layout.addLayout(self.detail_grid)
        self.root_layout.addStretch(1)

        self.run_selector.currentIndexChanged.connect(self._handle_run_selector_changed)
        self.incidents_panel.incident_selected.connect(self._handle_incident_selected)
        self.editor_panel.save_requested.connect(self._handle_save_request)
        self.export_panel.export_requested.connect(self.export_requested)
        self._update_responsive_layout()

    @property
    def selected_run_id(self) -> int | None:
        return self.selected_run["run_id"] if self.selected_run is not None else None

    @property
    def unsaved_dialog(self) -> UnsavedChangesDialog | None:
        return self._unsaved_dialog

    def set_run_history_loading(self) -> None:
        self._run_history_state = "loading"
        self._set_run_state("LOADING", "Loading detection run history…", "info")

    def set_run_history(self, records: list[DetectionRunSummary]) -> None:
        previous_run_id = self.selected_run_id
        self.run_summaries = [dict(record) for record in records]
        self.run_selector.setEnabled(not self.editor_panel.is_saving)
        self.run_selector.blockSignals(True)
        self.run_selector.clear()
        self.run_selector.addItem("Select a detection run…", None)
        for run in self.run_summaries:
            self.run_selector.addItem(f"Run #{run['run_id']} · {run['started_at']}", run["run_id"])
        self.run_selector.blockSignals(False)
        self._run_history_state = "ready" if records else "empty"

        restored = next((run for run in self.run_summaries if run["run_id"] == previous_run_id), None)
        if restored is None:
            self._set_combo_run(None)
            if previous_run_id is not None:
                message = (
                    "No detection runs available. Run detection to create a run to review."
                    if not records
                    else "The previously selected run is no longer available. Select another run."
                )
                self._clear_selected_run(message)
            elif not records:
                self._clear_selected_run("No detection runs available. Run detection to create a run to review.")
        else:
            self.selected_run = restored
            self._set_combo_run(restored["run_id"])
            self.export_panel.set_selected_run(restored)

        if records:
            self._set_run_state("RUNS READY", f"{len(records)} detection run(s) available.", "success")
        else:
            self._set_run_state("NO RUNS", "No detection runs available. Complete a detection run to review incidents or export a report.", "neutral")

    def set_run_history_error(self, message: str) -> None:
        self._run_history_state = "error"
        if not self.run_summaries:
            self.run_selector.blockSignals(True)
            self.run_selector.clear()
            self.run_selector.addItem("No detection runs available", None)
            self.run_selector.setEnabled(False)
            self.run_selector.blockSignals(False)
            self._clear_selected_run(message)
        self._set_run_state("SERVICE UNAVAILABLE", message, "error")

    def select_run(self, run_id: int, *, notify: bool = True) -> bool:
        index = self.run_selector.findData(run_id)
        if index < 0:
            return False
        if notify:
            self.run_selector.setCurrentIndex(index)
        else:
            self.run_selector.blockSignals(True)
            self.run_selector.setCurrentIndex(index)
            self.run_selector.blockSignals(False)
        return True

    def set_incidents_loading(self, run_id: int) -> None:
        if self.selected_run_id != run_id:
            return
        self._active_incidents = []
        self.selected_incident = None
        self.incidents_panel.set_loading(run_id)
        self._clear_incident_panels("Loading incidents for the selected run…")

    def set_incidents(
        self,
        run_id: int,
        incidents: list[DetectionIncident],
        *,
        select_incident_id: int | None = None,
    ) -> bool:
        if self.selected_run is None or self.selected_run["run_id"] != run_id:
            return False
        expected_count = self.selected_run["total_incidents"]
        accepted = self.incidents_panel.set_incidents(run_id, incidents, expected_count)
        if not accepted:
            self._active_incidents = []
            self.selected_incident = None
            self._clear_incident_panels("Incident results are unavailable for this run.")
            return False
        self._active_incidents = [dict(incident) for incident in incidents]
        self.selected_incident = None
        self._clear_incident_panels(
            "Select an incident to inspect its details, evidence, and review status."
        )
        if select_incident_id is not None:
            row_incident = next(
                (item for item in self._active_incidents if item["id"] == select_incident_id),
                None,
            )
            if row_incident is None:
                return False
            self.incidents_panel.select_incident_id(select_incident_id, notify=False)
            self._apply_incident(row_incident)
        return True

    def set_incidents_error(self, run_id: int, message: str) -> None:
        if self.selected_run_id != run_id:
            return
        self.incidents_panel.set_error(run_id, message)
        self._active_incidents = []
        self.selected_incident = None
        self._clear_incident_panels(message)

    def set_evidence(self, run_id: int, incident_id: int, events: list[EventRecord]) -> bool:
        incident = self.selected_incident
        if incident is None or (incident["run_id"], incident["id"]) != (run_id, incident_id):
            return False
        return self.evidence_panel.set_evidence(
            run_id,
            incident_id,
            events,
            incident["event_ids"],
        )

    def set_evidence_unavailable(self, run_id: int, incident_id: int, message: str) -> None:
        self.evidence_panel.set_unavailable(run_id, incident_id, message)

    def set_save_success(self, updated_incident: DetectionIncident) -> bool:
        selected = self.selected_incident
        if selected is None or (selected["run_id"], selected["id"]) != (
            updated_incident["run_id"],
            updated_incident["id"],
        ):
            return False
        if not self.editor_panel.set_save_success(updated_incident):
            self._set_review_controls_enabled(True)
            self._pending_action = None
            return False
        self._set_review_controls_enabled(True)
        self.selected_incident = dict(updated_incident)
        self._replace_active_incident(updated_incident)
        self.details_panel.set_incident(updated_incident)
        self.incidents_panel.set_incidents(
            updated_incident["run_id"],
            self._active_incidents,
            self.selected_run["total_incidents"] if self.selected_run is not None else None,
        )
        self.incidents_panel.select_incident_id(updated_incident["id"], notify=False)
        self._perform_pending_action()
        return True

    def set_save_failure(
        self,
        message: str,
        incident_id: int | None = None,
        run_id: int | None = None,
    ) -> None:
        if (
            self.selected_incident is None
            or (incident_id is not None and self.selected_incident["id"] != incident_id)
            or (run_id is not None and self.selected_incident["run_id"] != run_id)
        ):
            return
        self.editor_panel.set_save_failure(message)
        self._set_review_controls_enabled(True)
        self._pending_action = None

    def set_export_success(self, path: str, run_id: int | None = None) -> None:
        self.export_panel.set_export_success(path, run_id)

    def set_export_failure(self, message: str, run_id: int | None = None) -> None:
        self.export_panel.set_export_failure(message, run_id)

    def request_navigation(self, target_screen_id: str) -> bool:
        """Return True when navigation is clear, otherwise prompt before leaving."""
        if self.editor_panel.is_saving:
            return False
        if not self.editor_panel.is_dirty:
            return True
        self._pending_action = ("navigate", target_screen_id)
        self._show_unsaved_dialog()
        return False

    def handoff(
        self,
        history: list[DetectionRunSummary],
        run: DetectionRunSummary,
        incidents: list[DetectionIncident],
        incident: DetectionIncident,
    ) -> bool:
        """Open a detection result in context without fetching or rewriting it."""
        records = list(history)
        if not any(record["run_id"] == run["run_id"] for record in records):
            records.insert(0, dict(run))
        self.set_run_history(records)
        if not self.select_run(run["run_id"], notify=False):
            return False
        self._apply_run(run)
        if not self.set_incidents(run["run_id"], incidents, select_incident_id=incident["id"]):
            return False
        return self.selected_incident is not None and self.selected_incident["id"] == incident["id"]

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt event name
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _handle_run_selector_changed(self, index: int) -> None:
        run_id = self.run_selector.itemData(index)
        if run_id == self.selected_run_id:
            return
        if self.editor_panel.is_saving:
            self._set_combo_run(self.selected_run_id)
            return
        if run_id is not None and not any(run["run_id"] == run_id for run in self.run_summaries):
            return
        target = int(run_id) if run_id is not None else None
        if self.editor_panel.is_dirty:
            self._set_combo_run(self.selected_run_id)
            self._pending_action = ("run", target)
            self._show_unsaved_dialog()
            return
        self._apply_run_by_id(target)

    def _handle_incident_selected(self, incident: DetectionIncident) -> None:
        if self.selected_incident is not None and incident["id"] == self.selected_incident["id"]:
            return
        if self.editor_panel.is_saving:
            if self.selected_incident is None:
                self.incidents_panel.clear_selection()
            else:
                self.incidents_panel.select_incident_id(self.selected_incident["id"], notify=False)
            return
        if self.editor_panel.is_dirty:
            if self.selected_incident is None:
                self.incidents_panel.clear_selection()
            else:
                self.incidents_panel.select_incident_id(self.selected_incident["id"], notify=False)
            self._pending_action = ("incident", dict(incident))
            self._show_unsaved_dialog()
            return
        self._apply_incident(incident)

    def _handle_save_request(self, incident_id: int, status: str, note: str) -> None:
        if self.selected_incident is None or self.selected_run is None:
            self.editor_panel.set_save_failure("Select an incident before saving review changes.")
            return
        self._set_review_controls_enabled(False)
        self.save_requested.emit(self.selected_run["run_id"], incident_id, status, note)

    def _handle_unsaved_choice(self, choice: str) -> None:
        self._unsaved_dialog = None
        if choice == "cancel":
            self._pending_action = None
            return
        if choice == "discard":
            self.editor_panel.set_incident(self.selected_incident)
            self._perform_pending_action()
            return
        if choice == "save":
            if not self.editor_panel.save_changes():
                if not self.editor_panel.is_dirty:
                    self._perform_pending_action()
                else:
                    self._pending_action = None

    def _show_unsaved_dialog(self) -> None:
        if self._unsaved_dialog is not None:
            return
        dialog = UnsavedChangesDialog(self)
        self._unsaved_dialog = dialog
        dialog.decision_made.connect(self._handle_unsaved_choice)
        dialog.finished.connect(lambda _result, current=dialog: current.deleteLater())
        dialog.open()

    def _perform_pending_action(self) -> None:
        action = self._pending_action
        self._pending_action = None
        if action is None:
            return
        kind, value = action
        if kind == "run":
            self._apply_run_by_id(value if isinstance(value, int) else None)
        elif kind == "incident" and isinstance(value, dict):
            self._apply_incident(value)
        elif kind == "navigate" and isinstance(value, str):
            self.navigation_allowed.emit(value)

    def _apply_run_by_id(self, run_id: int | None) -> None:
        run = next((item for item in self.run_summaries if item["run_id"] == run_id), None)
        if run is None:
            self._set_combo_run(None)
            self._clear_selected_run("Select a detection run to view its incidents.")
            return
        self._apply_run(run)
        self.run_selected.emit(run["run_id"])

    def _apply_run(self, run: DetectionRunSummary) -> None:
        self.selected_run = dict(run)
        self.selected_incident = None
        self._set_combo_run(run["run_id"])
        self.export_panel.set_selected_run(run)
        self._set_run_state(
            "RUN SELECTED",
            f"Run #{run['run_id']} · {run['started_at']} · threshold {run['failure_threshold']} failures / "
            f"{run['time_window_minutes']} min · {run['total_incidents']} incident(s) · "
            f"{run['high_incidents']} HIGH.",
            "success",
        )
        self.set_incidents_loading(run["run_id"])

    def _apply_incident(self, incident: DetectionIncident) -> None:
        if self.selected_run_id != incident["run_id"]:
            return
        if not any(item["id"] == incident["id"] for item in self._active_incidents):
            return
        self.selected_incident = dict(incident)
        self.details_panel.set_incident(incident)
        self.editor_panel.set_incident(incident)
        self.evidence_panel.set_loading(incident["run_id"], incident["id"])
        event_ids = list(incident["event_ids"])
        if not event_ids:
            self.evidence_panel.set_no_linked_evidence(incident["run_id"], incident["id"])
            return
        self.evidence_requested.emit(incident["run_id"], incident["id"], event_ids)

    def _clear_selected_run(self, message: str) -> None:
        self.selected_run = None
        self.selected_incident = None
        self._active_incidents = []
        self.export_panel.set_selected_run(None)
        self.incidents_panel.clear(message)
        self._clear_incident_panels(message)

    def _clear_incident_panels(self, message: str) -> None:
        self.details_panel.set_incident(None)
        self.editor_panel.set_incident(None)
        self.evidence_panel.clear(message)

    def _set_review_controls_enabled(self, enabled: bool) -> None:
        self.run_selector.setEnabled(enabled and bool(self.run_summaries))
        self.incidents_panel.incidents_table.setEnabled(enabled)

    def _set_combo_run(self, run_id: int | None) -> None:
        index = self.run_selector.findData(run_id)
        if index < 0:
            index = 0
        self.run_selector.blockSignals(True)
        self.run_selector.setCurrentIndex(index)
        self.run_selector.blockSignals(False)

    def _set_run_state(self, badge: str, message: str, tone: str) -> None:
        self.run_state_badge.setText(badge)
        self.run_state_badge.setProperty("tone", tone)
        self.run_summary_label.setText(message)
        self.run_summary_label.setProperty("tone", tone)
        for widget in (self.run_state_badge, self.run_summary_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _replace_active_incident(self, incident: DetectionIncident) -> None:
        self._active_incidents = [
            dict(incident) if item["id"] == incident["id"] else item
            for item in self._active_incidents
        ]

    def _update_responsive_layout(self) -> None:
        mode = self._COMPACT if self.width() < 1120 else self._WIDE
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        self.incidents_panel.set_compact_columns(mode == self._COMPACT)
        self.top_grid.removeWidget(self.run_panel)
        self.top_grid.removeWidget(self.export_panel)
        self.detail_grid.removeWidget(self.details_panel)
        self.detail_grid.removeWidget(self.evidence_panel)
        self.detail_grid.removeWidget(self.editor_panel)
        if mode == self._COMPACT:
            self.top_grid.addWidget(self.run_panel, 0, 0)
            self.top_grid.addWidget(self.export_panel, 1, 0)
            for row, panel in enumerate((self.details_panel, self.evidence_panel, self.editor_panel)):
                self.detail_grid.addWidget(panel, row, 0)
            self.top_grid.setColumnStretch(0, 1)
            self.top_grid.setColumnStretch(1, 0)
            for column in (1, 2):
                self.detail_grid.setColumnStretch(column, 0)
            self.detail_grid.setColumnStretch(0, 1)
        else:
            self.top_grid.addWidget(self.run_panel, 0, 0)
            self.top_grid.addWidget(self.export_panel, 0, 1)
            self.detail_grid.addWidget(self.details_panel, 0, 0)
            self.detail_grid.addWidget(self.editor_panel, 0, 1)
            self.detail_grid.addWidget(self.evidence_panel, 1, 0, 1, 2)
            self.top_grid.setColumnStretch(0, 3)
            self.top_grid.setColumnStretch(1, 2)
            self.detail_grid.setColumnStretch(0, 1)
            self.detail_grid.setColumnStretch(1, 1)
