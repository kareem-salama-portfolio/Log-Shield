"""Incidents & Reports screen state, boundaries, and navigation checks."""

import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from app.models.detection import DetectionIncident, DetectionRunResult, DetectionRunSummary
from app.ui.main_window import MainWindow
from app.ui.screens.detection_rules.data_provider import (
    get_demo_detection_runs,
    get_demo_run_incidents,
)
from app.ui.screens.incidents_reports.data_provider import get_demo_incident_evidence
from app.ui.screens.incidents_reports.incidents_reports import IncidentsReportsScreen
from app.ui.styles.theme import apply_dark_theme


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_dark_theme(instance)
    return instance


def _prepared_screen() -> IncidentsReportsScreen:
    history = get_demo_detection_runs()
    run = next(record for record in history if record["run_id"] == 3)
    incidents = get_demo_run_incidents(3)
    screen = IncidentsReportsScreen()
    assert screen.handoff(history, run, incidents, incidents[0])
    return screen


def _wait_until(application: QApplication, predicate, timeout_ms: int = 3000) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        application.processEvents()
        if predicate():
            return True
        QTest.qWait(10)
    application.processEvents()
    return predicate()


class _LocalEventService:
    def has_eligible_events(self) -> bool:
        return True


class _LocalDetectionService:
    def __init__(self) -> None:
        self.history_thread_id: int | None = None
        self.results_thread_id: int | None = None

    def get_run_history(self) -> list[DetectionRunSummary]:
        self.history_thread_id = threading.get_ident()
        return [get_demo_detection_runs()[2]]

    def get_run_results(self, run_id: int) -> list[DetectionIncident]:
        self.results_thread_id = threading.get_ident()
        return get_demo_run_incidents(run_id)

    def run_detection(self, request, *, progress_callback=None) -> DetectionRunResult:
        raise AssertionError("This test does not start detection.")


def test_run_history_zero_and_run_scoped_incident_states(application: QApplication) -> None:
    screen = IncidentsReportsScreen()
    history = get_demo_detection_runs()
    screen.set_run_history(history)
    screen.select_run(3)
    screen.set_incidents(3, get_demo_run_incidents(3))
    screen.set_run_history([])
    assert "No detection runs available" in screen.run_summary_label.text()
    assert "No detection runs available" in screen.incidents_panel.state_label.text()
    assert screen.export_panel.selected_run is None

    screen.set_run_history(history)
    assert screen.select_run(2)
    run_zero = history[1]
    assert screen.selected_run_id == 2
    assert screen.incidents_panel.state_label.text().startswith("Loading incidents")
    assert screen.set_incidents(2, [], select_incident_id=None)
    assert "0 incidents" in screen.incidents_panel.state_label.text()
    assert screen.export_panel.csv_button.isEnabled()
    assert screen.export_panel.json_button.isEnabled()

    assert screen.select_run(3)
    assert screen.set_incidents(3, get_demo_run_incidents(3))
    assert [item["id"] for item in screen.incidents_panel.records] == [15, 16, 17]
    assert all(item["run_id"] == 3 for item in screen.incidents_panel.records)
    assert run_zero["total_incidents"] == 0
    screen.close()


def test_compact_layout_fits_viewport_and_keeps_full_values_in_tooltips(application: QApplication) -> None:
    window = MainWindow(demo_mode=True)
    window.resize(900, 700)
    window.show()
    window.sidebar.items["incidents_reports"].click()
    application.processEvents()
    screen = window.incidents_reports
    table = screen.incidents_panel.incidents_table

    assert screen.width() <= window.incidents_reports_scroll.viewport().width()
    assert table.horizontalScrollBarPolicy().name == "ScrollBarAlwaysOff"
    assert table.item(0, 1).text() == "203.0.\n113.7"
    assert table.item(0, 4).text() == "10-02\n08:00"
    assert table.item(0, 4).toolTip() == "2026-10-02T08:00:10"
    window.close()


def test_selected_incident_details_status_and_exact_linked_evidence(application: QApplication) -> None:
    window = MainWindow(demo_mode=True)
    window.sidebar.items["incidents_reports"].click()
    screen = window.incidents_reports
    assert screen.demo_badge is not None
    assert screen.demo_badge.text() == "SYNTHETIC DEMO"
    assert screen.incidents_panel.incidents_table.rowCount() == 3

    screen.incidents_panel.incidents_table.selectRow(0)
    assert screen.selected_incident["id"] == 15
    assert screen.details_panel.values["incident_id"].text() == "#15"
    assert screen.details_panel.values["source_ip"].text() == "203.0.113.7"
    assert screen.details_panel.review_badge.text() == "NEW"
    assert [event["id"] for event in screen.evidence_panel.events] == [101, 102, 103, 104, 105, 106]
    assert [event["outcome"] for event in screen.evidence_panel.events][-1] == "SUCCESS"

    screen.incidents_panel.incidents_table.selectRow(2)
    assert screen.selected_incident["id"] == 17
    assert screen.evidence_panel.state_label.text() == "This incident has no linked evidence events."

    screen.incidents_panel.incidents_table.selectRow(1)
    assert screen.details_panel.review_badge.text() == "REVIEWED"
    assert screen.incidents_panel.records[1]["severity"] == "MEDIUM"
    window.close()


def test_evidence_rejects_unlinked_events_and_demo_provider_obeys_event_ids(application: QApplication) -> None:
    screen = _prepared_screen()
    incident = screen.selected_incident
    demo_events = get_demo_incident_evidence(incident)
    assert [event["id"] for event in demo_events] == incident["event_ids"]
    assert screen.set_evidence(3, 15, demo_events)
    assert screen.evidence_panel.events == demo_events

    unrelated = dict(demo_events[0])
    unrelated["id"] = 999
    assert not screen.set_evidence(3, 15, [unrelated])
    assert "not linked" in screen.evidence_panel.state_label.text()
    screen.set_evidence_unavailable(3, 15, "Exact event lookup is unavailable.")
    assert screen.evidence_panel.state_label.text() == "Exact event lookup is unavailable."
    screen.close()


def test_status_note_limit_counter_and_save_failure_preserve_edits(application: QApplication) -> None:
    screen = _prepared_screen()
    editor = screen.editor_panel
    editor.status_selector.setCurrentIndex(editor.status_selector.findData("REVIEWED"))
    editor.note_editor.setPlainText("x" * 501)

    assert editor.current_status == "REVIEWED"
    assert editor.current_note == "x" * 500
    assert editor.character_counter.text() == "500 / 500"
    assert editor.save_button.isEnabled()
    assert editor.save_changes()
    assert not screen.run_selector.isEnabled()
    assert not screen.incidents_panel.incidents_table.isEnabled()
    screen.set_save_failure("Review service failed; edits remain local.", 15)
    assert screen.run_selector.isEnabled()
    assert screen.incidents_panel.incidents_table.isEnabled()
    assert editor.current_note == "x" * 500
    assert editor.current_status == "REVIEWED"
    assert editor.state_badge.text() == "SAVE FAILED"
    assert editor.save_button.isEnabled()
    screen.close()


def test_save_success_updates_confirmed_incident_and_allows_pending_navigation(application: QApplication) -> None:
    screen = _prepared_screen()
    screen.editor_panel.note_editor.setPlainText("Reviewed by analyst")
    allowed: list[str] = []
    screen.navigation_allowed.connect(allowed.append)

    assert not screen.request_navigation("dashboard")
    assert screen.unsaved_dialog is not None
    screen.unsaved_dialog.save_button.click()
    assert screen.editor_panel.state_badge.text() == "SAVING"
    assert not screen.incidents_panel.incidents_table.isEnabled()

    updated = dict(screen.selected_incident)
    updated["status"] = "REVIEWED"
    updated["note"] = "Reviewed by analyst"
    assert screen.set_save_success(updated)
    assert screen.details_panel.review_badge.text() == "REVIEWED"
    assert screen.details_panel.note_value.text() == "Reviewed by analyst"
    assert allowed == ["dashboard"]
    assert not screen.editor_panel.is_dirty
    screen.close()


def test_unsaved_incident_selection_cancel_and_discard(application: QApplication) -> None:
    screen = _prepared_screen()
    screen.editor_panel.note_editor.setPlainText("Keep this until confirmed")
    screen.incidents_panel.incidents_table.selectRow(1)
    assert screen.selected_incident["id"] == 15
    assert screen.unsaved_dialog is not None
    screen.unsaved_dialog.cancel_button.click()
    assert screen.selected_incident["id"] == 15
    assert screen.editor_panel.current_note == "Keep this until confirmed"

    screen.incidents_panel.incidents_table.selectRow(1)
    assert screen.unsaved_dialog is not None
    screen.unsaved_dialog.discard_button.click()
    assert screen.selected_incident["id"] == 16
    assert not screen.editor_panel.is_dirty
    screen.close()


def test_csv_json_export_requests_and_cancellation(application: QApplication, monkeypatch, tmp_path) -> None:
    screen = IncidentsReportsScreen()
    history = get_demo_detection_runs()
    screen.set_run_history(history)
    screen.select_run(2)
    screen.set_incidents(2, [])
    requests: list[tuple[int, str, str]] = []
    screen.export_requested.connect(lambda run_id, fmt, path: requests.append((run_id, fmt, path)))

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: ("", ""))
    assert not screen.export_panel.choose_export_destination("csv")
    assert requests == []
    assert not screen.export_panel._exporting

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args: (str(tmp_path / "zero-run"), "CSV files (*.csv)"),
    )
    assert screen.export_panel.choose_export_destination("csv")
    assert requests[-1][0:2] == (2, "csv")
    assert requests[-1][2].endswith("zero-run.csv")
    screen.set_export_failure("Export service unavailable; no file was written.")

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args: (str(tmp_path / "run.json"), "JSON files (*.json)"),
    )
    assert screen.export_panel.choose_export_destination("json")
    assert requests[-1][0:2] == (2, "json")
    screen.set_export_success(str(tmp_path / "confirmed.json"))
    assert screen.export_panel.state_badge.text() == "EXPORTED"
    screen.export_panel.set_selected_run(history[0])
    assert not screen.export_panel.set_export_success(str(tmp_path / "stale.json"), run_id=2)
    assert screen.export_panel.state_badge.text() == "READY"
    screen.close()


def test_unavailable_export_service_does_not_create_a_report(application: QApplication, monkeypatch, tmp_path) -> None:
    window = MainWindow(demo_mode=True)
    screen = window.incidents_reports
    path = tmp_path / "not-created.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args: (str(path), "CSV files (*.csv)"))

    screen.export_panel.csv_button.click()

    assert screen.export_panel.state_badge.text() == "EXPORT FAILED"
    assert "No report was written" in screen.export_panel.state_message.text()
    assert not path.exists()
    window.close()


def test_save_failure_keeps_user_on_incidents_screen(application: QApplication) -> None:
    window = MainWindow(demo_mode=True)
    window.sidebar.items["incidents_reports"].click()
    screen = window.incidents_reports
    screen.incidents_panel.incidents_table.selectRow(0)
    screen.editor_panel.note_editor.setPlainText("Unsaved note")
    window.sidebar.items["detection_rules"].click()
    screen.unsaved_dialog.save_button.click()

    assert window.screen_stack.currentWidget() is window.incidents_reports_scroll
    assert screen.editor_panel.state_badge.text() == "SAVE FAILED"
    assert screen.editor_panel.current_note == "Unsaved note"
    window.close()


def test_main_window_exposes_missing_services_without_fabrication(application: QApplication) -> None:
    window = MainWindow()
    screen = window.incidents_reports
    assert not screen.run_selector.isEnabled()
    assert "Detection service is not connected" in screen.run_summary_label.text()
    assert screen.incidents_panel.records == []
    assert "NO RUN" in screen.export_panel.state_badge.text()
    window.close()


def test_navigation_guard_and_detection_rules_handoff(application: QApplication) -> None:
    window = MainWindow(demo_mode=True)
    window.sidebar.items["incidents_reports"].click()
    screen = window.incidents_reports
    screen.incidents_panel.incidents_table.selectRow(0)
    screen.editor_panel.note_editor.setPlainText("Pending review note")
    window.sidebar.items["detection_rules"].click()
    assert window.screen_stack.currentWidget() is window.incidents_reports_scroll
    assert screen.unsaved_dialog is not None
    screen.unsaved_dialog.cancel_button.click()
    assert window.screen_stack.currentWidget() is window.incidents_reports_scroll

    screen.editor_panel.note_editor.clear()
    window.sidebar.items["detection_rules"].click()
    assert window.screen_stack.currentWidget() is window.detection_rules_scroll
    window.detection_rules.run_results.incidents_table.selectRow(0)
    assert window.screen_stack.currentWidget() is window.incidents_reports_scroll
    assert screen.selected_run_id == 3
    assert screen.selected_incident["id"] == 15
    assert screen.evidence_panel.events
    window.close()


def test_run_history_and_results_are_loaded_on_detection_worker(application: QApplication) -> None:
    service = _LocalDetectionService()
    window = MainWindow(event_service=_LocalEventService(), detection_service=service)
    screen = window.incidents_reports
    assert _wait_until(application, lambda: screen.run_summaries and service.history_thread_id is not None)
    assert service.history_thread_id != threading.get_ident()
    assert screen.select_run(1)
    assert _wait_until(application, lambda: screen.incidents_panel.records and service.results_thread_id is not None)
    assert service.results_thread_id != threading.get_ident()
    assert all(item["run_id"] == 1 for item in screen.incidents_panel.records)
    window.close()
