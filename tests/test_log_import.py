"""Behavior checks for import validation and the event explorer UI states."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import QApplication, QFileDialog

from app.models.log_import import EventFilters, EventPage
from app.ui.main_window import MainWindow
from app.ui.screens.log_import.data_provider import (
    get_demo_event_page,
    get_demo_import_history,
    get_demo_malformed_records,
)
from app.ui.screens.log_import.event_explorer import EventExplorer, PAGE_SIZE
from app.ui.screens.log_import.malformed_dialog import MalformedRecordsDialog
from app.ui.styles.theme import apply_dark_theme
from app.utils.file_validation import (
    MAX_LOG_FILE_SIZE_BYTES,
    LogFileValidationError,
    validate_log_file,
)


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_dark_theme(instance)
    return instance


def test_log_import_screen_creation_and_empty_states(application: QApplication) -> None:
    screen = EventExplorer()

    assert screen.filter_panel is not None
    assert screen.history_panel.empty_label.text() == "No previous imports"
    assert screen.history_panel.history_table.rowCount() == 0
    assert "No events imported yet" in screen.event_state_label.text()
    assert screen.event_table.rowCount() == 0
    assert screen.ip_details_panel.empty_label.text() == "Select an event to view source IP context."

    screen.close()


def test_extension_and_size_validation(tmp_path: Path) -> None:
    unsupported = tmp_path / "events.csv"
    unsupported.write_text("auth event", encoding="utf-8")
    with pytest.raises(LogFileValidationError, match=".log or .txt"):
        validate_log_file(unsupported)

    oversized = tmp_path / "large.log"
    with oversized.open("wb") as file_handle:
        file_handle.truncate(MAX_LOG_FILE_SIZE_BYTES + 1)
    with pytest.raises(LogFileValidationError, match="20 MB"):
        validate_log_file(oversized)

    valid = tmp_path / "auth.TXT"
    valid.write_text("", encoding="utf-8")
    assert validate_log_file(valid) == valid.resolve()

    exact_limit = tmp_path / "at-limit.log"
    with exact_limit.open("wb") as file_handle:
        file_handle.truncate(MAX_LOG_FILE_SIZE_BYTES)
    assert validate_log_file(exact_limit) == exact_limit.resolve()


def test_invalid_selected_files_show_failure_and_valid_files_remain_pending(
    tmp_path: Path,
    application: QApplication,
) -> None:
    screen = EventExplorer()
    requested: list[str] = []
    screen.import_requested.connect(requested.append)

    assert not screen.select_log_file(tmp_path / "auth.csv")
    assert screen.import_panel.state == "error"
    assert "Choose a log file" in screen.import_panel.status_label.text()

    valid = tmp_path / "auth.log"
    valid.write_text("this text has not been parsed", encoding="utf-8")
    assert screen.select_log_file(valid)
    assert requested == [str(valid.resolve())]
    assert screen.import_panel.state == "pending"
    assert "not imported" in screen.import_panel.status_label.text()
    assert screen.history_panel.history_table.rowCount() == 0
    screen.close()


def test_native_file_picker_is_restricted_and_emits_a_valid_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application: QApplication,
) -> None:
    selected = tmp_path / "picked.txt"
    selected.write_text("", encoding="utf-8")
    calls: list[tuple[object, ...]] = []

    def fake_picker(*args: object) -> tuple[str, str]:
        calls.append(args)
        return str(selected), "Authentication logs (*.log *.txt)"

    monkeypatch.setattr(QFileDialog, "getOpenFileName", fake_picker)
    screen = EventExplorer()
    screen.open_file_picker()

    assert calls and calls[0][3] == "Authentication logs (*.log *.txt)"
    assert screen.import_panel.selected_path == selected.resolve()
    assert screen.import_panel.state == "pending"
    screen.close()


def test_invalid_date_time_range_is_rejected_and_combined_filters_are_emitted(
    application: QApplication,
) -> None:
    screen = EventExplorer()
    filters_panel = screen.filter_panel
    submitted: list[EventFilters] = []
    filters_panel.filters_submitted.connect(submitted.append)

    filters_panel.start_enabled.setChecked(True)
    filters_panel.end_enabled.setChecked(True)
    filters_panel.start_datetime.setDateTime(
        QDateTime.fromString("2026-10-02T09:00:00", Qt.DateFormat.ISODate)
    )
    filters_panel.end_datetime.setDateTime(
        QDateTime.fromString("2026-10-02T08:00:00", Qt.DateFormat.ISODate)
    )
    assert not filters_panel.apply_filters()
    assert "earlier than or equal" in filters_panel.validation_message.text()
    assert submitted == []

    filters_panel.source_ip_input.setText("203.0.113.7")
    filters_panel.username_input.setText("admin")
    filters_panel.outcome_selector.setCurrentText("FAILED")
    filters_panel.end_datetime.setDateTime(
        QDateTime.fromString("2026-10-02T10:00:00", Qt.DateFormat.ISODate)
    )
    assert filters_panel.apply_filters()
    assert submitted[-1]["source_ip"] == "203.0.113.7"
    assert submitted[-1]["username"] == "admin"
    assert submitted[-1]["outcome"] == "FAILED"
    assert submitted[-1]["start_time"] is not None
    assert submitted[-1]["end_time"] is not None
    screen.close()


def test_filter_clear_resets_controls_and_requests_unfiltered_page(application: QApplication) -> None:
    screen = EventExplorer()
    requests: list[tuple[EventFilters, int, int]] = []
    screen.events_requested.connect(lambda filters, page, size: requests.append((filters, page, size)))
    screen.filter_panel.source_ip_input.setText("192.0.2.44")
    screen.filter_panel.outcome_selector.setCurrentText("SUCCESS")
    screen.filter_panel.start_enabled.setChecked(True)

    screen.filter_panel.clear_filters()

    assert screen.filter_panel.source_ip_input.text() == ""
    assert screen.filter_panel.outcome_selector.currentIndex() == 0
    assert not screen.filter_panel.start_enabled.isChecked()
    assert requests[-1][0] == {
        "source_ip": None,
        "username": None,
        "outcome": None,
        "start_time": None,
        "end_time": None,
    }
    assert requests[-1][1:] == (1, PAGE_SIZE)
    screen.close()


def test_demo_provider_combines_filters_with_and_and_returns_a_page() -> None:
    filters: EventFilters = {
        "source_ip": "192.0.2.44",
        "username": "analyst",
        "outcome": "SUCCESS",
        "start_time": None,
        "end_time": None,
    }
    page = get_demo_event_page(filters, page=1, page_size=PAGE_SIZE)

    assert page["total_count"] == 3
    assert len(page["items"]) == 3
    assert all(event["source_ip"] == "192.0.2.44" for event in page["items"])
    assert all(event["username"] == "analyst" and event["outcome"] == "SUCCESS" for event in page["items"])
    assert page["page_size"] == PAGE_SIZE


def test_event_row_selection_requests_backend_ip_details_and_benign_ip_is_supported(
    application: QApplication,
) -> None:
    window = MainWindow(demo_mode=True)
    window.sidebar.items["log_import"].click()
    screen = window.event_explorer
    assert screen.event_table.rowCount() > 0

    success_only_row = next(
        row
        for row, event in enumerate(screen._visible_events)
        if event["source_ip"] == "192.0.2.44"
    )
    screen.event_table.selectRow(success_only_row)
    application.processEvents()

    assert screen.ip_details_panel.address_label.text() == "192.0.2.44"
    assert screen.ip_details_panel.metric_values["failed_logins"].text() == "0"
    assert screen.ip_details_panel.metric_values["successful_logins"].text() == "3"
    window.close()


def test_event_page_size_and_pagination_controls(application: QApplication) -> None:
    screen = EventExplorer()
    filters: EventFilters = {
        "source_ip": None,
        "username": None,
        "outcome": None,
        "start_time": None,
        "end_time": None,
    }
    demo_page = get_demo_event_page(filters)
    page_one_items = (demo_page["items"] * 20)[:PAGE_SIZE]
    page_one: EventPage = {
        **demo_page,
        "items": page_one_items,
        "page": 1,
        "page_size": PAGE_SIZE,
        "total_count": 405,
    }
    requests: list[tuple[EventFilters, int, int]] = []
    screen.events_requested.connect(lambda current_filters, page, size: requests.append((current_filters, page, size)))

    screen.set_events_page(page_one)
    assert screen.page_size == 200
    assert screen.event_table.rowCount() == 200
    assert not screen.previous_button.isEnabled()
    assert screen.next_button.isEnabled()
    assert screen.result_summary_label.text() == "1–200 of 405 events"

    screen.request_next_page()
    assert requests[-1][1:] == (2, 200)
    screen.set_events_page(
        {**demo_page, "items": demo_page["items"][:5], "page": 3, "page_size": 200, "total_count": 405}
    )
    assert screen.previous_button.isEnabled()
    assert not screen.next_button.isEnabled()
    assert screen.page_label.text() == "Page 3 of 3"
    assert len(screen._visible_events) <= PAGE_SIZE
    screen.close()


def test_empty_event_query_and_ip_details_states(application: QApplication) -> None:
    screen = EventExplorer()

    assert screen.event_table.isHidden()
    assert "No events imported yet" in screen.event_state_label.text()
    assert not screen.ip_details_panel.empty_label.isHidden()
    screen.set_events_error("Event Service unavailable")
    assert screen.event_state_label.text() == "Event Service unavailable"
    assert screen.result_summary_label.text() == "Results unavailable"
    screen.close()


def test_history_malformed_request_and_dialog_empty_and_populated_states(
    application: QApplication,
) -> None:
    screen = EventExplorer()
    screen.set_import_history(get_demo_import_history())
    requests: list[int] = []
    screen.history_panel.malformed_records_requested.connect(requests.append)
    screen.history_panel._handle_cell_clicked(1, 4)
    assert requests == [1]

    empty_dialog = MalformedRecordsDialog([], 0)
    assert "no malformed" in empty_dialog.empty_label.text().lower()
    assert empty_dialog.records_table.rowCount() == 0

    records = get_demo_malformed_records(1)
    records[0]["raw_text"] = "raw authentication line " + ("field " * 180)
    populated_dialog = MalformedRecordsDialog(records, 4)
    assert populated_dialog.total_count_label.text() == "4 malformed records"
    assert populated_dialog.records_table.rowCount() == 4
    assert populated_dialog.records_table.item(0, 2).text() == "Bad timestamp"
    assert populated_dialog.records_table.wordWrap()
    assert populated_dialog.records_table.item(0, 1).text().endswith("field " * 180)
    populated_dialog.close()
    empty_dialog.close()
    screen.close()


def test_import_progress_and_confirmed_result_states(application: QApplication) -> None:
    screen = EventExplorer()
    screen.import_panel.set_importing("auth.log")
    screen.set_import_progress(43, "Reading records…")
    assert screen.import_panel.progress_bar.value() == 43

    record = get_demo_import_history()[1]
    screen.set_import_result(record)
    assert screen.import_panel.state == "warning"
    assert screen.import_panel.malformed_button.isEnabled()
    assert len(screen.history_panel.records) == 1
    screen.close()
