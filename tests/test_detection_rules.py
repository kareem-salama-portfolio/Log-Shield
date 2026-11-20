"""Detection Rules & Runs screen state and selection checks."""

import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.detection import (
    DetectionIncident,
    DetectionRunResult,
    DetectionRunSummary,
)
from app.ui.main_window import MainWindow
from app.ui.screens.detection_rules.data_provider import (
    get_demo_detection_runs,
    get_demo_run_incidents,
)
from app.ui.screens.detection_rules.detection_runs import DetectionRulesScreen
from app.ui.styles.theme import apply_dark_theme


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_dark_theme(instance)
    return instance


def _run(
    run_id: int,
    *,
    total_incidents: int = 0,
    high_incidents: int = 0,
) -> DetectionRunSummary:
    return {
        "run_id": run_id,
        "started_at": f"2026-10-0{run_id}T08:00:00",
        "failure_threshold": 5,
        "time_window_minutes": 10,
        "total_incidents": total_incidents,
        "high_incidents": high_incidents,
    }


def _incident(
    incident_id: int,
    run_id: int,
    source_ip: str,
    severity: str = "MEDIUM",
) -> DetectionIncident:
    return {
        "id": incident_id,
        "run_id": run_id,
        "source_ip": source_ip,
        "start_ts": "2026-10-02T08:00:10",
        "end_ts": "2026-10-02T08:09:55",
        "failure_count": 5,
        "severity": severity,
        "status": "NEW",
        "note": "",
        "event_ids": [101, 102],
    }


class _LocalDetectionTestService:
    """Test-only service that records which thread called the run method."""

    def __init__(self) -> None:
        self.run_thread_id: int | None = None
        self.request: dict[str, int] | None = None

    def get_run_history(self) -> list[DetectionRunSummary]:
        return []

    def get_run_results(self, run_id: int) -> list[DetectionIncident]:
        return []

    def run_detection(self, request, *, progress_callback=None) -> DetectionRunResult:
        self.run_thread_id = threading.get_ident()
        self.request = dict(request)
        if progress_callback is not None:
            progress_callback({"status": "Checking imported events…"})
        return {"run": _run(9), "incidents": []}


class _LocalEventTestService:
    def has_eligible_events(self) -> bool:
        return True


def _wait_until(application: QApplication, predicate, timeout_ms: int = 3000) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        application.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    application.processEvents()
    return predicate()


def test_screen_creation_shows_idle_empty_and_no_selection_states(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()

    assert screen.rule_settings.failure_threshold.value() == 5
    assert screen.rule_settings.time_window.value() == 10
    assert screen.rule_settings.high_severity_toggle.isCheckable()
    assert screen.runs_panel.history_state == "empty"
    assert "No detection runs yet" in screen.runs_panel.state_label.text()
    assert (
        screen.run_results.state_label.text()
        == "Select a detection run to view its stored incidents."
    )

    screen.close()


def test_threshold_and_time_window_ranges_and_defaults(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    settings = screen.rule_settings

    assert (
        settings.failure_threshold.minimum(),
        settings.failure_threshold.maximum(),
    ) == (3, 20)
    assert settings.failure_threshold.value() == 5
    settings.failure_threshold.setValue(-1)
    assert settings.failure_threshold.value() == 3
    settings.failure_threshold.setValue(100)
    assert settings.failure_threshold.value() == 20

    assert (settings.time_window.minimum(), settings.time_window.maximum()) == (1, 60)
    assert settings.time_window.value() == 10
    settings.time_window.setValue(0)
    assert settings.time_window.value() == 1
    settings.time_window.setValue(100)
    assert settings.time_window.value() == 60
    screen.close()


def test_high_severity_toggle_is_local_and_not_in_run_request(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_event_availability(True)
    screen.set_detection_service_available(True)
    screen.rule_settings.high_severity_toggle.setChecked(True)
    requests: list[object] = []
    screen.run_requested.connect(requests.append)

    assert screen.rule_settings.request_detection()
    assert requests == [{"failure_threshold": 5, "time_window_minutes": 10}]
    assert "high" not in requests[0]
    screen.close()


def test_high_only_toggle_filters_display_without_changing_run_results(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    run = _run(3, total_incidents=2, high_incidents=1)
    incidents = [
        _incident(1, 3, "203.0.113.7", "HIGH"),
        _incident(2, 3, "198.51.100.23", "MEDIUM"),
    ]
    screen.set_run_history([run])
    assert screen.select_run(3)
    assert screen.set_selected_run_results(3, incidents)
    assert len(screen.run_results.incidents) == 2

    screen.rule_settings.high_severity_toggle.setChecked(True)

    assert len(screen.run_results.incidents) == 1
    assert screen.run_results.incidents[0]["severity"] == "HIGH"
    assert screen.run_results.incidents_table.rowCount() == 1
    assert "2 incidents detected (1 HIGH)" in screen.run_results.summary_label.text()
    screen.close()


def test_run_button_is_disabled_when_no_events_are_available(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_detection_service_available(True)
    screen.set_event_availability(False)

    assert not screen.rule_settings.run_button.isEnabled()
    assert (
        screen.rule_settings.operation_message.text()
        == "Import authentication logs before running detection."
    )
    screen.close()


def test_run_button_is_disabled_when_service_is_unavailable(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_event_availability(True)
    screen.set_detection_service_available(False, "Detection service unavailable.")

    assert not screen.rule_settings.run_button.isEnabled()
    assert (
        screen.rule_settings.operation_message.text()
        == "Detection service unavailable."
    )
    screen.close()


def test_running_state_disables_button_and_prevents_duplicate_requests(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_event_availability(True)
    screen.set_detection_service_available(True)
    requests: list[object] = []
    screen.run_requested.connect(requests.append)

    assert screen.rule_settings.request_detection()
    assert screen.rule_settings.operation_badge.text() == "RUNNING"
    assert not screen.rule_settings.run_button.isEnabled()
    assert not screen.rule_settings.request_detection()
    assert len(requests) == 1

    screen.rule_settings.set_progress({"percentage": 43, "status": "Checking events…"})
    assert screen.rule_settings.progress_bar.value() == 43
    assert screen.rule_settings.operation_message.text() == "Checking events…"
    screen.close()


def test_completed_run_is_added_and_uses_backend_summary(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_event_availability(True)
    screen.set_detection_service_available(True)
    run = _run(4, total_incidents=2, high_incidents=1)
    result: DetectionRunResult = {
        "run": run,
        "incidents": [
            _incident(20, 4, "203.0.113.9", "HIGH"),
            _incident(21, 4, "198.51.100.23", "MEDIUM"),
        ],
    }
    screen.set_detection_running()
    screen.set_detection_completed(result)

    assert screen.rule_settings.operation_badge.text() == "COMPLETED"
    assert screen.rule_settings.run_button.isEnabled()
    assert screen.runs_panel.records[0] == run
    assert screen.selected_run_id == 4
    assert (
        screen.run_results.summary_label.text()
        == "2 incidents detected (1 HIGH) · Run #4"
    )
    assert screen.run_results.incidents_table.rowCount() == 2
    screen.close()


def test_zero_incident_completed_run_is_distinct_from_no_selection(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    run = _run(5)
    screen.set_detection_completed({"run": run, "incidents": []})

    assert screen.selected_run_id == 5
    assert (
        screen.run_results.summary_label.text()
        == "0 incidents detected (0 HIGH) · Run #5"
    )
    assert (
        screen.run_results.state_label.text()
        == "This run completed with zero incidents."
    )
    assert not screen.run_results.state_label.isHidden()
    screen.close()


def test_failed_run_keeps_history_intact(application: QApplication) -> None:
    screen = DetectionRulesScreen()
    runs = get_demo_detection_runs()
    screen.set_run_history(runs)
    screen.set_detection_running()

    screen.set_detection_failed("Detection service failed.")

    assert screen.rule_settings.operation_badge.text() == "FAILED"
    assert screen.rule_settings.operation_message.text() == "Detection service failed."
    assert screen.runs_panel.records == runs
    screen.close()


def test_selecting_old_run_requests_its_own_stored_results(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_run_history(get_demo_detection_runs())
    requested: list[int] = []
    screen.run_results_requested.connect(requested.append)

    assert screen.select_run(3)
    assert screen.set_selected_run_results(3, get_demo_run_incidents(3))
    assert screen.run_results.incidents[0]["run_id"] == 3
    assert screen.select_run(1)
    assert requested == [3, 1]
    assert screen.run_results.state_label.text() == "Loading incidents for run #1…"

    assert screen.set_selected_run_results(1, get_demo_run_incidents(1))
    assert screen.run_results.incidents
    assert all(item["run_id"] == 1 for item in screen.run_results.incidents)
    assert all(
        item["source_ip"] != "203.0.113.7" for item in screen.run_results.incidents
    )
    screen.close()


def test_old_or_mixed_run_results_cannot_replace_selected_run(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_run_history([_run(1, total_incidents=1)])
    screen.select_run(1)

    assert not screen.set_selected_run_results(2, [_incident(2, 2, "203.0.113.8")])
    assert not screen.set_selected_run_results(1, [_incident(2, 2, "203.0.113.8")])
    assert (
        screen.run_results.state_label.text()
        == "The detection service returned results for a different run."
    )
    screen.close()


def test_run_history_loading_and_error_keep_existing_history(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    runs = get_demo_detection_runs()
    screen.set_run_history(runs)

    screen.set_run_history_loading()
    assert screen.runs_panel.history_state == "loading"
    assert screen.runs_panel.runs_table.rowCount() == len(runs)

    screen.set_run_history_error("Run history refresh failed.")
    assert screen.runs_panel.history_state == "error"
    assert screen.runs_panel.runs_table.rowCount() == len(runs)
    assert "still available" in screen.runs_panel.state_label.text()
    screen.close()


def test_selected_run_results_loading_error_and_incident_selection(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    run = _run(8, total_incidents=1)
    incident = _incident(88, 8, "192.0.2.88")
    screen.set_run_history([run])
    screen.select_run(8)
    assert screen.run_results.state_label.text() == "Loading incidents for run #8…"

    incident_requests: list[DetectionIncident] = []
    screen.incident_selected.connect(incident_requests.append)
    assert screen.set_selected_run_results(8, [incident])
    screen.run_results.incidents_table.selectRow(0)
    assert incident_requests == [incident]

    screen.select_run(8)
    screen.set_selected_run_error(8, "Run results unavailable.")
    assert screen.run_results.state_label.text() == "Run results unavailable."
    screen.close()


def test_history_empty_state_is_distinct_from_service_unavailable(
    application: QApplication,
) -> None:
    screen = DetectionRulesScreen()
    screen.set_run_history([])
    assert screen.runs_panel.state_label.text().startswith("No detection runs yet")

    screen.set_run_history_error("Detection service is not connected.")
    assert screen.runs_panel.state_label.text() == "Detection service is not connected."
    assert screen.runs_panel.history_state == "error"
    screen.close()


def test_main_window_integrates_detection_navigation_and_incident_handoff(
    application: QApplication,
) -> None:
    window = MainWindow(demo_mode=True)
    window.sidebar.items["detection_rules"].click()

    assert window.screen_stack.currentWidget() is window.detection_rules_scroll
    assert window.sidebar.items["detection_rules"].property("active") == "true"
    assert window.detection_rules.selected_run_id == 3

    window.sidebar.items["log_import"].click()
    assert window.screen_stack.currentWidget() is window.event_explorer_scroll
    window.sidebar.items["dashboard"].click()
    assert window.screen_stack.currentWidget() is window.dashboard_scroll
    assert window.sidebar.items["dashboard"].property("active") == "true"

    window.detection_rules.incident_selected.emit(
        _incident(15, 3, "203.0.113.7", "HIGH")
    )
    assert "Incidents & Reports" in window.statusBar().currentMessage()
    window.close()


def test_regular_launch_shows_service_unavailable_without_fabricated_runs(
    application: QApplication,
) -> None:
    window = MainWindow()

    assert window.detection_rules.runs_panel.history_state == "error"
    assert window.detection_rules.runs_panel.state_label.text() == (
        "Detection service is not connected. Run history is unavailable."
    )
    assert window.detection_rules.runs_panel.records == []
    assert not window.detection_rules.rule_settings.run_button.isEnabled()
    assert window.detection_rules.rule_settings.operation_message.text().startswith(
        "Event service is not connected"
    )
    window.close()


def test_injected_service_runs_off_gui_thread_and_returns_confirmed_result(
    application: QApplication,
) -> None:
    service = _LocalDetectionTestService()
    window = MainWindow(
        event_service=_LocalEventTestService(),
        detection_service=service,
    )
    screen = window.detection_rules
    assert _wait_until(application, lambda: screen.runs_panel.history_state == "empty")
    assert screen.rule_settings.run_button.isEnabled()

    screen.rule_settings.run_button.click()

    assert _wait_until(
        application, lambda: screen.rule_settings.operation_badge.text() == "COMPLETED"
    )
    assert _wait_until(application, lambda: screen.rule_settings.run_button.isEnabled())
    assert service.request == {"failure_threshold": 5, "time_window_minutes": 10}
    assert service.run_thread_id is not None
    assert service.run_thread_id != threading.get_ident()
    assert screen.selected_run_id == 9
    assert (
        screen.run_results.state_label.text()
        == "This run completed with zero incidents."
    )
    QTest.qWait(10)
    application.processEvents()
    window.close()
