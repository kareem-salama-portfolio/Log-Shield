"""Detection Rules & Runs screen and service-facing UI signals."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from app.models.detection import (
    DetectionIncident,
    DetectionProgress,
    DetectionRunResult,
    DetectionRunSummary,
)
from app.ui.screens.detection_rules.rule_settings import RuleSettingsPanel
from app.ui.screens.detection_rules.run_results import RunResultsPanel
from app.ui.screens.detection_rules.runs_table import RunsTablePanel
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PageHeader


class DetectionRulesScreen(QWidget):
    """Configure a run and display only service-provided run results."""

    run_requested = Signal(object)
    run_results_requested = Signal(int)
    incident_selected = Signal(object)

    _COMPACT = "compact"
    _WIDE = "wide"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardContent")
        self._layout_mode: str | None = None
        self._selected_run: DetectionRunSummary | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        root.setSpacing(Spacing.LG)
        root.addWidget(
            PageHeader(
                "Detection Rules & Runs",
                "Configure detection parameters, run security analysis, and review previous results.",
            )
        )

        self.top_grid = QGridLayout()
        self.top_grid.setContentsMargins(0, 0, 0, 0)
        self.top_grid.setHorizontalSpacing(Spacing.MD)
        self.top_grid.setVerticalSpacing(Spacing.MD)
        self.rule_settings = RuleSettingsPanel()
        self.runs_panel = RunsTablePanel()
        self.top_grid.addWidget(self.rule_settings, 0, 0)
        self.top_grid.addWidget(self.runs_panel, 0, 1)
        root.addLayout(self.top_grid)

        self.run_results = RunResultsPanel()
        root.addWidget(self.run_results)
        root.addStretch(1)

        self.rule_settings.run_requested.connect(self.run_requested)
        self.rule_settings.high_only_changed.connect(self.run_results.set_high_only)
        self.runs_panel.run_selected.connect(self._handle_run_selected)
        self.run_results.incident_selected.connect(self.incident_selected)
        self.set_run_history([])
        self.rule_settings.set_event_availability(None)
        self.rule_settings.set_detection_service_available(False)
        self._update_responsive_layout()

    @property
    def selected_run_id(self) -> int | None:
        return self._selected_run["run_id"] if self._selected_run is not None else None

    def set_event_availability(
        self, available: bool | None, error_message: str | None = None
    ) -> None:
        self.rule_settings.set_event_availability(available, error_message)

    def set_detection_service_available(
        self,
        available: bool,
        error_message: str | None = None,
    ) -> None:
        self.rule_settings.set_detection_service_available(available, error_message)

    def set_run_history_loading(self) -> None:
        self.runs_panel.set_loading()

    def set_run_history(self, records: list[DetectionRunSummary]) -> None:
        self.runs_panel.set_runs(records)
        if self.selected_run_id is not None:
            selected = next(
                (
                    record
                    for record in records
                    if record["run_id"] == self.selected_run_id
                ),
                None,
            )
            if selected is None:
                self._selected_run = None
                self.runs_panel.clear_selection()
                self.run_results.clear_selection()
            else:
                self._selected_run = selected

    def set_run_history_error(self, message: str) -> None:
        self.runs_panel.set_error(message)

    def select_run(self, run_id: int) -> bool:
        return self.runs_panel.select_run_id(run_id)

    def set_selected_run_results(
        self,
        run_id: int,
        incidents: list[DetectionIncident],
    ) -> bool:
        return self.run_results.set_results(run_id, incidents)

    def set_selected_run_error(self, run_id: int, message: str) -> None:
        self.run_results.set_error(run_id, message)

    def set_detection_running(self, status: str = "Detection is running…") -> None:
        self.rule_settings.set_running(status)

    def set_detection_progress(self, progress: DetectionProgress) -> None:
        self.rule_settings.set_progress(progress)

    def set_detection_completed(
        self,
        result: DetectionRunResult,
        *,
        worker_active: bool = False,
    ) -> None:
        run = result["run"]
        self.runs_panel.upsert_run(run)
        self.runs_panel.select_run_id(run["run_id"], notify=False)
        self._selected_run = run
        self.run_results.set_loading(run)
        self.run_results.set_results(run["run_id"], result["incidents"])
        self.rule_settings.set_run_completed(run["run_id"], worker_active=worker_active)

    def set_detection_failed(
        self, message: str, *, worker_active: bool = False
    ) -> None:
        self.rule_settings.set_run_failed(message, worker_active=worker_active)

    def set_detection_worker_finished(self) -> None:
        self.rule_settings.set_worker_finished()

    def _handle_run_selected(self, run: DetectionRunSummary) -> None:
        self._selected_run = run
        self.run_results.set_loading(run)
        self.run_results_requested.emit(run["run_id"])

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _update_responsive_layout(self) -> None:
        mode = self._COMPACT if self.width() < 1000 else self._WIDE
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        self.run_results.incidents_table.setMaximumHeight(
            310 if mode == self._COMPACT else 380
        )

        self.top_grid.removeWidget(self.rule_settings)
        self.top_grid.removeWidget(self.runs_panel)
        if mode == self._COMPACT:
            self.top_grid.addWidget(self.rule_settings, 0, 0)
            self.top_grid.addWidget(self.runs_panel, 1, 0)
            self.top_grid.setColumnStretch(0, 1)
            self.top_grid.setColumnStretch(1, 0)
        else:
            self.top_grid.addWidget(self.rule_settings, 0, 0)
            self.top_grid.addWidget(self.runs_panel, 0, 1)
            self.top_grid.setColumnStretch(0, 2)
            self.top_grid.setColumnStretch(1, 3)
