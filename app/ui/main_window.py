"""Top-level LogShield window and navigation between implemented screens."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QWidget,
)

from app.models.dashboard import DashboardData
from app.models.detection import DetectionRunRequest
from app.models.log_import import EventFilters
from app.services.import_worker import ImportWorker
from app.services.ui_contracts import DetectionService, EventService, ImportService
from app.ui.navigation import PRIMARY_SCREENS
from app.ui.screens.dashboard.dashboard import Dashboard
from app.ui.screens.dashboard.data_provider import (
    get_demo_dashboard_data,
    get_empty_dashboard_data,
)
from app.ui.screens.detection_rules.data_provider import (
    demo_has_eligible_events,
    get_demo_detection_runs,
    get_demo_run_incidents,
)
from app.ui.screens.detection_rules.detection_runs import DetectionRulesScreen
from app.ui.screens.detection_rules.run_worker import (
    DetectionOperation,
    DetectionServiceWorker,
)
from app.ui.screens.incidents_reports.data_provider import get_demo_incident_evidence
from app.ui.screens.incidents_reports.incidents_reports import IncidentsReportsScreen
from app.ui.screens.log_import.data_provider import (
    get_demo_event_page,
    get_demo_import_history,
    get_demo_ip_details,
    get_demo_malformed_records,
    get_empty_event_page,
    get_empty_import_history,
)
from app.ui.screens.log_import.event_explorer import EventExplorer
from app.ui.styles.tokens import Spacing
from app.ui.widgets.sidebar import Sidebar

logger = logging.getLogger(__name__)

_ORPHANED_DETECTION_WORKERS: set[DetectionServiceWorker] = set()


class MainWindow(QMainWindow):
    """Shared application shell with all implemented primary screens."""

    def __init__(
        self,
        dashboard_data: DashboardData | None = None,
        demo_mode: bool = False,
        event_service: EventService | None = None,
        detection_service: DetectionService | None = None,
        import_service: ImportService | None = None,
        dashboard_service: object | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("LogShield — Security Overview")
        self.resize(1440, 900)
        self.setMinimumSize(800, 560)
        self.demo_mode = demo_mode
        self.event_service = event_service
        self.detection_service = detection_service
        self.import_service = import_service
        self.dashboard_service = dashboard_service
        self._import_worker = None
        self._detection_worker: DetectionServiceWorker | None = None
        self._active_detection_workers: set[DetectionServiceWorker] = set()

        central = QWidget(self)
        central.setObjectName("appRoot")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(Spacing.XS, Spacing.XS, Spacing.XS, Spacing.XS)
        layout.setSpacing(Spacing.SM)

        self.sidebar = Sidebar(active_screen="dashboard", parent=central)
        initial_dashboard_data = dashboard_data
        if initial_dashboard_data is None:
            initial_dashboard_data = (
                get_demo_dashboard_data() if demo_mode else get_empty_dashboard_data()
            )
        self.dashboard = Dashboard(
            initial_dashboard_data, demo_mode=demo_mode, parent=central
        )
        self.dashboard_scroll = QScrollArea(central)
        self.dashboard_scroll.setObjectName("dashboardScroll")
        self.dashboard_scroll.setWidgetResizable(True)
        self.dashboard_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.dashboard_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.dashboard_scroll.setWidget(self.dashboard)

        self.event_explorer = EventExplorer()
        self.event_explorer_scroll = QScrollArea(central)
        self.event_explorer_scroll.setObjectName("eventExplorerScroll")
        self.event_explorer_scroll.setWidgetResizable(True)
        self.event_explorer_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.event_explorer_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.event_explorer_scroll.setWidget(self.event_explorer)

        self.detection_rules = DetectionRulesScreen()
        self.detection_rules_scroll = QScrollArea(central)
        self.detection_rules_scroll.setObjectName("detectionRulesScroll")
        self.detection_rules_scroll.setWidgetResizable(True)
        self.detection_rules_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.detection_rules_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.detection_rules_scroll.setWidget(self.detection_rules)

        self.incidents_reports = IncidentsReportsScreen(demo_mode=demo_mode)
        self.incidents_reports_scroll = QScrollArea(central)
        self.incidents_reports_scroll.setObjectName("incidentsReportsScroll")
        self.incidents_reports_scroll.setWidgetResizable(True)
        self.incidents_reports_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.incidents_reports_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.incidents_reports_scroll.setWidget(self.incidents_reports)

        self.screen_stack = QStackedWidget(central)
        self.screen_stack.addWidget(self.dashboard_scroll)
        self.screen_stack.addWidget(self.event_explorer_scroll)
        self.screen_stack.addWidget(self.detection_rules_scroll)
        self.screen_stack.addWidget(self.incidents_reports_scroll)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.screen_stack, 1)
        self.setCentralWidget(central)

        self._screen_labels = dict(PRIMARY_SCREENS)
        self.sidebar.navigation_requested.connect(self._handle_navigation_request)
        self.dashboard.navigation_requested.connect(self._handle_navigation_request)
        self.dashboard.incident_open_requested.connect(
            self._handle_incident_open_request
        )
        self.event_explorer.import_requested.connect(self._handle_import_request)
        self.event_explorer.events_requested.connect(self._handle_events_request)
        self.event_explorer.ip_details_requested.connect(
            self._handle_ip_details_request
        )
        self.event_explorer.malformed_records_requested.connect(
            self._handle_malformed_records_request
        )
        self.detection_rules.run_requested.connect(self._handle_detection_run_request)
        self.detection_rules.run_results_requested.connect(
            self._handle_run_results_request
        )
        self.detection_rules.incident_selected.connect(
            self._handle_detection_incident_open_request
        )
        self.incidents_reports.run_selected.connect(self._handle_incident_run_selected)
        self.incidents_reports.evidence_requested.connect(
            self._handle_incident_evidence_requested
        )
        self.incidents_reports.save_requested.connect(self._handle_incident_review_save)
        self.incidents_reports.export_requested.connect(self._handle_incident_export)
        self.incidents_reports.navigation_allowed.connect(self._activate_screen)

        self.statusBar().showMessage(self._status_message(demo_mode))

        if demo_mode:
            self.event_explorer.set_import_history(get_demo_import_history())
            self.event_explorer.set_events_page(get_demo_event_page(_empty_filters()))
        else:
            self.event_explorer.set_import_history(get_empty_import_history())
            self.event_explorer.set_events_page(get_empty_event_page())

        self._initialize_detection_rules()
        self._initialize_incidents_reports()

    @staticmethod
    def _status_message(demo_mode: bool) -> str:
        if demo_mode:
            return "Offline workspace  ·  Synthetic demonstration data"
        return "Offline workspace  ·  Import a log file to begin"

    def _handle_navigation_request(self, screen_id: str) -> None:
        if (
            self.screen_stack.currentWidget() is self.incidents_reports_scroll
            and screen_id != "incidents_reports"
            and screen_id in self._screen_labels
            and not self.incidents_reports.request_navigation(screen_id)
        ):
            return
        self._activate_screen(screen_id)

    def _activate_screen(self, screen_id: str) -> None:
        if screen_id == "dashboard":
            self.screen_stack.setCurrentWidget(self.dashboard_scroll)
            self.sidebar.set_active_screen("dashboard")
            self.setWindowTitle("LogShield — Security Overview")
            self.statusBar().showMessage("Security Overview is open.", 3500)
            return
        if screen_id == "log_import":
            self.screen_stack.setCurrentWidget(self.event_explorer_scroll)
            self.sidebar.set_active_screen("log_import")
            self.setWindowTitle("LogShield — Log Import & Event Explorer")
            self.statusBar().showMessage("Log Import & Event Explorer is open.", 3500)
            return
        if screen_id == "detection_rules":
            self.screen_stack.setCurrentWidget(self.detection_rules_scroll)
            self.sidebar.set_active_screen("detection_rules")
            self.setWindowTitle("LogShield — Detection Rules & Runs")
            self.statusBar().showMessage("Detection Rules & Runs is open.", 3500)
            return
        if screen_id == "incidents_reports":
            self.screen_stack.setCurrentWidget(self.incidents_reports_scroll)
            self.sidebar.set_active_screen("incidents_reports")
            self.setWindowTitle("LogShield — Incidents & Reports")
            self.statusBar().showMessage("Incidents & Reports is open.", 3500)
            return
        label = self._screen_labels.get(screen_id)
        if label is None:
            self.statusBar().showMessage(
                "This navigation destination is unavailable.", 4500
            )
            return
        self.statusBar().showMessage(
            f"{label} will be available in a future task.", 4500
        )

    def _handle_import_request(self, file_path: str) -> None:
        if self.import_service is None:
            self.statusBar().showMessage("Import service is unavailable.", 6000)
            return
        if self._import_worker is not None and self._import_worker.isRunning():
            return
        self.event_explorer.import_panel.set_importing(Path(file_path).name)
        worker = ImportWorker(self.import_service, file_path)
        self._import_worker = worker
        worker.progress.connect(self._handle_import_progress)
        worker.completed.connect(self._handle_import_completed)
        worker.failed.connect(self._handle_import_failed)
        worker.finished.connect(lambda: setattr(self, "_import_worker", None))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _handle_import_progress(self, progress: object) -> None:
        if isinstance(progress, dict):
            self.event_explorer.set_import_progress(
                int(progress.get("percentage", 0)),
                str(progress.get("status", "Import in progress…")),
            )

    def _handle_import_completed(self, record: object) -> None:
        self.event_explorer.set_import_result(record)
        self.event_explorer.set_import_history(
            self.import_service.get_import_history(page=1, page_size=50)["items"]
        )
        self._refresh_database_views()
        self.statusBar().showMessage("Log file imported successfully.", 5000)

    def _handle_import_failed(self, message: str) -> None:
        self.event_explorer.set_import_failed(message)
        self.statusBar().showMessage(f"Import failed: {message}", 7000)

    def _refresh_database_views(self) -> None:
        if self.event_service is None:
            return
        self.event_explorer.set_events_page(
            self.event_service.get_events(_empty_filters(), page=1, page_size=200)
        )
        if self.detection_service is not None:
            self.detection_rules.set_event_availability(
                self.event_service.has_eligible_events()
            )
        self._refresh_dashboard()

    def _refresh_dashboard(self) -> None:
        dashboard_service = self.dashboard_service
        if dashboard_service is not None:
            self.dashboard.update_data(dashboard_service.dashboard())

    def _handle_events_request(
        self, filters: EventFilters, page: int, page_size: int
    ) -> None:
        if self.demo_mode:
            self.event_explorer.set_events_page(
                get_demo_event_page(filters, page=page, page_size=page_size)
            )
            return
        if self.event_service is not None:
            self.event_explorer.set_events_page(
                self.event_service.get_events(filters, page=page, page_size=page_size)
            )
        else:
            self.event_explorer.set_events_error("Event service is not connected.")

    def _handle_ip_details_request(self, source_ip: str) -> None:
        if self.demo_mode:
            self.event_explorer.set_ip_details(get_demo_ip_details(source_ip))
            return
        if self.event_service is not None:
            self.event_explorer.set_ip_details(
                self.event_service.get_ip_details(source_ip)
            )
        else:
            self.event_explorer.set_ip_details_unavailable(source_ip)

    def _handle_malformed_records_request(self, import_id: int) -> None:
        if self.demo_mode:
            records = get_demo_malformed_records(import_id)
            history = {
                record["import_id"]: record for record in get_demo_import_history()
            }
            total_count = history.get(import_id, {}).get(
                "malformed_records", len(records)
            )
            self.event_explorer.show_malformed_records(records, total_count)
            return
        self.statusBar().showMessage(
            "Malformed-record details are unavailable until an Import Service is connected.",
            5500,
        )

    def _handle_incident_open_request(self, incident: object) -> None:
        """Open a dashboard summary in the reports screen without inventing IDs."""
        self._activate_screen("incidents_reports")
        if isinstance(incident, dict) and {"id", "run_id", "event_ids"}.issubset(
            incident
        ):
            self._handle_detection_incident_open_request(incident)
            return
        self.statusBar().showMessage(
            "Select a detection run to review this dashboard summary; it does not include a run or incident ID.",
            6000,
        )

    def _initialize_detection_rules(self) -> None:
        if self.demo_mode:
            self.detection_rules.set_event_availability(demo_has_eligible_events())
            self.detection_rules.set_run_history(get_demo_detection_runs())
            self.detection_rules.set_detection_service_available(
                False,
                "Detection service unavailable. Synthetic history is read-only; no run was started.",
            )
            self.detection_rules.select_run(3)
            return

        if self.event_service is None:
            self.detection_rules.set_event_availability(
                None,
                "Event service is not connected. Import authentication logs before running detection.",
            )
        else:
            try:
                self.detection_rules.set_event_availability(
                    self.event_service.has_eligible_events()
                )
            except Exception as error:
                logger.exception("Could not check detection readiness")
                self.detection_rules.set_event_availability(
                    None,
                    f"Eligible events could not be checked: {_exception_message(error)}",
                )

        if self.detection_service is None:
            self.detection_rules.set_detection_service_available(
                False,
                "Detection service is not connected. No run can be started.",
            )
            self.detection_rules.set_run_history_error(
                "Detection service is not connected. Run history is unavailable."
            )
        else:
            self.detection_rules.set_detection_service_available(True)
            self.detection_rules.set_run_history_loading()
            self._start_detection_service_request("history")

    def _initialize_incidents_reports(self) -> None:
        if self.demo_mode:
            self.incidents_reports.set_run_history(get_demo_detection_runs())
            self.incidents_reports.select_run(3)
            return
        if self.detection_service is None:
            self.incidents_reports.set_run_history_error(
                "Detection service is not connected. Run history is unavailable."
            )
        else:
            self.incidents_reports.set_run_history_loading()

    def _handle_detection_run_request(self, request: DetectionRunRequest) -> None:
        if self.demo_mode:
            self.detection_rules.set_detection_failed(
                "Synthetic demonstration history is read-only. No detection run was started."
            )
            return
        if self.detection_service is None:
            self.detection_rules.set_detection_failed(
                "Detection service is not connected. No detection run was started."
            )
            return
        if self._detection_worker is not None and self._detection_worker.isRunning():
            return

        worker = self._start_detection_service_request("run", request=request)
        self._detection_worker = worker
        self.statusBar().showMessage("Detection run is in progress.")

    def _start_detection_service_request(
        self,
        operation: DetectionOperation,
        *,
        request: DetectionRunRequest | None = None,
        run_id: int = 0,
    ) -> DetectionServiceWorker:
        if self.detection_service is None:
            raise RuntimeError("Detection service is not connected.")
        worker = DetectionServiceWorker(
            self.detection_service,
            operation,
            request=request,
            run_id=run_id,
        )
        self._active_detection_workers.add(worker)
        worker.request_completed.connect(self._handle_detection_service_response)
        worker.request_failed.connect(self._handle_detection_service_error)
        if operation == "run":
            worker.progress_received.connect(
                self.detection_rules.set_detection_progress
            )
        worker.finished.connect(
            lambda active_worker=worker: self._handle_detection_worker_finished(
                active_worker
            )
        )
        worker.finished.connect(worker.deleteLater)
        worker.start()
        return worker

    def _handle_detection_service_response(
        self,
        operation: str,
        run_id: int,
        result: object,
    ) -> None:
        if operation == "history":
            self.detection_rules.set_run_history(result)
            self.incidents_reports.set_run_history(result)
        elif operation == "results":
            self.detection_rules.set_selected_run_results(run_id, result)
            self.incidents_reports.set_incidents(run_id, result)
        elif operation == "run":
            run_result = result
            self.detection_rules.set_detection_completed(run_result, worker_active=True)
            self.incidents_reports.set_run_history(
                self.detection_rules.runs_panel.records
            )
            self._refresh_dashboard()
            self.statusBar().showMessage(
                f"Run #{run_result['run']['run_id']} completed and stored.", 5000
            )

    def _handle_detection_service_error(
        self,
        operation: str,
        run_id: int,
        message: str,
    ) -> None:
        if operation == "history":
            self.detection_rules.set_run_history_error(
                f"Run history could not be loaded: {message}"
            )
            self.incidents_reports.set_run_history_error(
                f"Run history could not be loaded: {message}"
            )
        elif operation == "results":
            self.detection_rules.set_selected_run_error(
                run_id,
                f"Run #{run_id} results could not be loaded: {message}",
            )
            self.incidents_reports.set_incidents_error(
                run_id,
                f"Run #{run_id} results could not be loaded: {message}",
            )
        elif operation == "run":
            self.detection_rules.set_detection_failed(message, worker_active=True)
            self.statusBar().showMessage(f"Detection run failed: {message}", 6000)

    def _handle_detection_worker_finished(self, worker: DetectionServiceWorker) -> None:
        self._active_detection_workers.discard(worker)
        if self._detection_worker is worker:
            self._detection_worker = None
            self.detection_rules.set_detection_worker_finished()

    def _handle_run_results_request(self, run_id: int) -> None:
        if self.demo_mode:
            self.detection_rules.set_selected_run_results(
                run_id,
                get_demo_run_incidents(run_id),
            )
            return
        if self.detection_service is None:
            self.detection_rules.set_selected_run_error(
                run_id,
                "Detection service is not connected. Stored run results are unavailable.",
            )
            return
        self._start_detection_service_request("results", run_id=run_id)

    def _handle_detection_incident_open_request(self, incident: object) -> None:
        if not isinstance(incident, dict) or not {"id", "run_id"}.issubset(incident):
            self.statusBar().showMessage(
                "The selected item does not include an incident ID and run ID.", 5000
            )
            return
        run_id = incident["run_id"]
        run = next(
            (
                record
                for record in self.detection_rules.runs_panel.records
                if record["run_id"] == run_id
            ),
            None,
        )
        if run is None:
            self.statusBar().showMessage(
                f"Run #{run_id} is not available in the current run history.", 5000
            )
            return
        incidents = (
            self.detection_rules.run_results.incidents
            if self.detection_rules.run_results.selected_run is not None
            and self.detection_rules.run_results.selected_run["run_id"] == run_id
            else []
        )
        selected = next(
            (item for item in incidents if item["id"] == incident["id"]), None
        )
        if selected is None:
            self.statusBar().showMessage(
                f"Incident #{incident['id']} is not present in the loaded results for run #{run_id}.",
                5500,
            )
            return
        if not self.incidents_reports.handoff(
            self.detection_rules.runs_panel.records,
            run,
            incidents,
            selected,
        ):
            self.statusBar().showMessage(
                "The selected incident could not be opened for this run.", 5000
            )
            return
        self._activate_screen("incidents_reports")
        self.statusBar().showMessage(
            f"Incidents & Reports opened incident #{selected['id']} from detection run #{run_id}.",
            4500,
        )

    def _handle_incident_run_selected(self, run_id: int) -> None:
        if self.demo_mode:
            self.incidents_reports.set_incidents(run_id, get_demo_run_incidents(run_id))
            return
        if self.detection_service is None:
            self.incidents_reports.set_incidents_error(
                run_id,
                "Detection service is not connected. Stored run incidents are unavailable.",
            )
            return
        self._start_detection_service_request("results", run_id=run_id)

    def _handle_incident_evidence_requested(
        self,
        run_id: int,
        incident_id: int,
        event_ids: object,
    ) -> None:
        incident = self.incidents_reports.selected_incident
        if incident is None or (incident["run_id"], incident["id"]) != (
            run_id,
            incident_id,
        ):
            return
        if (
            not isinstance(event_ids, (list, tuple))
            or list(event_ids) != incident["event_ids"]
        ):
            self.incidents_reports.set_evidence_unavailable(
                run_id,
                incident_id,
                "The evidence request did not match this incident's linked event IDs.",
            )
            return
        if self.demo_mode:
            self.incidents_reports.set_evidence(
                run_id,
                incident_id,
                get_demo_incident_evidence(incident),
            )
            return
        if self.event_service is not None:
            self.incidents_reports.set_evidence(
                run_id,
                incident_id,
                self.event_service.get_linked_events(list(event_ids)),
            )
        else:
            self.incidents_reports.set_evidence_unavailable(
                run_id, incident_id, "Event service is unavailable."
            )

    def _handle_incident_review_save(
        self,
        run_id: int,
        incident_id: int,
        status: str,
        note: str,
    ) -> None:
        if self.demo_mode:
            self.incidents_reports.set_save_failure(
                "Synthetic demonstration data is read-only. No review changes were saved.",
                incident_id,
                run_id,
            )
            return
        if self.detection_service is None:
            self.incidents_reports.set_save_failure(
                "Incident review persistence is unavailable. No review changes were saved.",
                incident_id,
                run_id,
            )
            return
        try:
            updated = self.detection_service.save_review(
                run_id, incident_id, status, note
            )
            self.incidents_reports.set_save_success(updated)
            self._refresh_dashboard()
        except Exception as error:
            logger.exception(
                "Incident review save failed for run %s, incident %s",
                run_id,
                incident_id,
            )
            self.incidents_reports.set_save_failure(str(error), incident_id, run_id)

    def _handle_incident_export(
        self, run_id: int, export_format: str, path: str
    ) -> None:
        if self.demo_mode:
            self.incidents_reports.set_export_failure(
                "Synthetic demonstration history is read-only. No report was written.",
                run_id,
            )
            return
        if self.detection_service is None:
            self.incidents_reports.set_export_failure(
                "Export service unavailable; no file was written.", run_id
            )
            return
        try:
            exported_path = self.detection_service.export_report(
                run_id, export_format, path
            )
            self.incidents_reports.set_export_success(exported_path, run_id)
        except Exception as error:
            logger.exception("Report export failed for run %s", run_id)
            self.incidents_reports.set_export_failure(str(error), run_id)

    def closeEvent(self, event) -> None:
        for worker in tuple(self._active_detection_workers):
            if worker.isRunning():
                worker.request_completed.disconnect(
                    self._handle_detection_service_response
                )
                worker.request_failed.disconnect(self._handle_detection_service_error)
                _ORPHANED_DETECTION_WORKERS.add(worker)
                worker.finished.connect(
                    lambda active_worker=worker: _ORPHANED_DETECTION_WORKERS.discard(
                        active_worker
                    )
                )
        self._active_detection_workers.clear()
        self._detection_worker = None
        super().closeEvent(event)


def _empty_filters() -> EventFilters:
    return {
        "source_ip": None,
        "username": None,
        "outcome": None,
        "start_time": None,
        "end_time": None,
    }


def _exception_message(error: Exception) -> str:
    return str(error).strip() or error.__class__.__name__
