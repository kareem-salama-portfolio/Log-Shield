"""Render UI review images using the active Qt desktop platform.

Run with ``python tools/capture_dashboard_previews.py``. This is a visual-QA
helper, not part of the desktop application's runtime path. It uses installed
platform fonts so images reflect the supported Windows UI.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / "data" / "matplotlib"))
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.screens.dashboard.data_provider import (
    get_demo_dashboard_data,
    get_empty_dashboard_data,
)
from app.ui.screens.log_import.data_provider import get_demo_malformed_records
from app.ui.styles.theme import apply_dark_theme


def _capture(
    application: QApplication,
    data: dict,
    filename: str,
    demo_mode: bool,
    size: tuple[int, int] = (1440, 900),
    screen_id: str = "dashboard",
) -> Path:
    window = MainWindow(dashboard_data=data, demo_mode=demo_mode)
    window.resize(*size)
    if screen_id != "dashboard":
        window.sidebar.items[screen_id].click()
    window.show()
    application.processEvents()

    output_path = PROJECT_ROOT / "screenshots" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def _capture_detection(
    application: QApplication,
    filename: str,
    state: str,
    size: tuple[int, int] = (1440, 900),
) -> Path:
    window = MainWindow(demo_mode=True)
    window.resize(*size)
    window.sidebar.items["detection_rules"].click()
    screen = window.detection_rules

    if state == "empty":
        screen.set_run_history([])
        screen.set_event_availability(False)
        screen.set_detection_service_available(
            False,
            "Detection service unavailable. Synthetic history is read-only; no run was started.",
        )
    elif state == "running":
        screen.set_detection_running()
        window.statusBar().showMessage(
            "Synthetic demonstration data · running-state layout preview"
        )
    elif state == "zero":
        screen.select_run(2)
    elif state == "history-loading":
        screen.set_run_history_loading()
    elif state == "history-error":
        screen.set_run_history_error(
            "Detection service unavailable; run history could not be loaded."
        )
    elif state == "results-error":
        screen.select_run(3)
        screen.set_selected_run_error(
            3, "Detection service could not return this run's results."
        )
    elif state == "failure":
        screen.set_detection_failed(
            "Detection service returned an error. No run was created."
        )

    window.show()
    application.processEvents()
    if state == "compact-results":
        scroll_bar = window.detection_rules_scroll.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
        application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def _capture_incidents(
    application: QApplication,
    filename: str,
    state: str,
    size: tuple[int, int] = (1440, 900),
) -> Path:
    """Capture a synthetic Incidents & Reports visual state without persistence."""
    demo_mode = state != "service-unavailable"
    window = MainWindow(demo_mode=demo_mode)
    window.resize(*size)
    window.sidebar.items["incidents_reports"].click()
    screen = window.incidents_reports
    prompt_unsaved = False

    if state == "no-runs":
        screen.set_run_history([])
    elif state == "zero":
        screen.select_run(2)
    elif state in {
        "selected-evidence",
        "no-evidence",
        "unsaved",
        "saving",
        "save-success",
        "save-failure",
        "compact-details",
    }:
        screen.incidents_panel.incidents_table.selectRow(
            2 if state == "no-evidence" else 0
        )
        if state in {"unsaved", "saving", "save-success", "save-failure"}:
            screen.editor_panel.note_editor.setPlainText(
                "Visual review note — no persistence in this preview."
            )
        if state == "unsaved":
            prompt_unsaved = True
        elif state == "saving":
            screen.save_requested.disconnect(window._handle_incident_review_save)
            screen.editor_panel.save_changes()
        elif state == "save-success":
            screen.save_requested.disconnect(window._handle_incident_review_save)
            screen.editor_panel.save_changes()
            updated = dict(screen.selected_incident)
            updated["status"] = "REVIEWED"
            updated["note"] = screen.editor_panel.current_note
            screen.set_save_success(updated)
            screen.editor_panel.state_message.setText(
                "Visual-only success state; no review data was persisted."
            )
        elif state == "save-failure":
            screen.editor_panel.save_changes()
    elif state == "exporting":
        screen.export_panel.set_exporting("csv")
    elif state == "export-success":
        screen.export_panel.set_exporting("csv")
        screen.export_panel.set_export_success("logshield-run-3.csv")
        screen.export_panel.state_message.setText(
            "Visual-only success state; no file was created."
        )
    elif state == "export-failure":
        screen.export_panel.set_export_failure(
            "Export service unavailable; no report was written."
        )
    elif state == "service-unavailable":
        window.statusBar().showMessage(
            "Service-unavailable state preview · no backend services connected"
        )

    window.show()
    application.processEvents()
    if state in {
        "compact-details",
        "selected-evidence",
        "no-evidence",
        "saving",
        "save-success",
        "save-failure",
    }:
        scrollbar = window.incidents_reports_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        if state == "selected-evidence":
            evidence_scroll = screen.evidence_panel.evidence_table.verticalScrollBar()
            evidence_scroll.setValue(evidence_scroll.maximum())
        application.processEvents()
    if prompt_unsaved:
        screen.request_navigation("detection_rules")
        application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    preview = (
        screen.unsaved_dialog.grab()
        if prompt_unsaved and screen.unsaved_dialog is not None
        else window.grab()
    )
    if not preview.save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def _capture_malformed_dialog(application: QApplication) -> Path:
    """Capture the app-owned malformed-record dialog over the explorer screen."""
    window = MainWindow(demo_mode=True)
    window.resize(1440, 900)
    window.sidebar.items["log_import"].click()
    records = get_demo_malformed_records(1)
    dialog = window.event_explorer.show_malformed_records(records, len(records))
    window.show()
    application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / "malformed-records-dialog.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not dialog.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    dialog.close()
    window.close()
    return output_path


def _capture_event_state(application: QApplication, filename: str, state: str) -> Path:
    """Capture query, import, selected-IP, or input-focus states."""
    window = MainWindow(demo_mode=True)
    window.resize(1440, 900)
    window.sidebar.items["log_import"].click()
    screen = window.event_explorer
    if state == "loading":
        screen.set_events_loading()
    elif state == "error":
        screen.set_events_error("Event service unavailable. No query was run.")
    elif state == "import-progress":
        screen.set_import_progress(58, "Parsing authentication log…")
    elif state == "import-failure":
        screen.set_import_failed(
            "Import service unavailable; the selected file was not imported."
        )
    elif state == "ip-details":
        screen.event_table.selectRow(0)

    window.show()
    application.processEvents()
    if state == "focus":
        screen.filter_panel.source_ip_input.setFocus()
        application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def _capture_event_compact_results(application: QApplication) -> Path:
    """Show the narrow event table and IP-detail panels after scrolling."""
    window = MainWindow(demo_mode=True)
    window.resize(900, 700)
    window.sidebar.items["log_import"].click()
    window.event_explorer.event_table.selectRow(0)
    window.show()
    application.processEvents()
    scrollbar = window.event_explorer_scroll.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())
    application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / "event-explorer-compact-results.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def _capture_regular_screen(
    application: QApplication, screen_id: str, filename: str
) -> Path:
    """Capture a real empty-workspace service state without demo fixtures."""
    window = MainWindow(demo_mode=False)
    window.resize(1440, 900)
    window.sidebar.items[screen_id].click()
    window.show()
    application.processEvents()
    output_path = PROJECT_ROOT / "screenshots" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output_path)):
        raise OSError(f"Could not save application screenshot: {output_path}")
    window.close()
    return output_path


def main() -> None:
    application = QApplication([])
    application.setApplicationName("LogShield screenshot review")
    # The offscreen Qt plugin does not register Windows desktop fonts by
    # itself; explicitly load Segoe UI so preview captures match the app.
    QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\segoeui.ttf")
    apply_dark_theme(application)

    outputs = (
        _capture(application, get_demo_dashboard_data(), "dashboard-demo.png", True),
        _capture(application, get_empty_dashboard_data(), "dashboard-empty.png", False),
        _capture(
            application,
            get_demo_dashboard_data(),
            "dashboard-compact.png",
            True,
            (900, 700),
        ),
        _capture(
            application,
            get_demo_dashboard_data(),
            "event-explorer-demo.png",
            True,
            screen_id="log_import",
        ),
        _capture_detection(application, "detection-rules-demo.png", "demo"),
        _capture_detection(application, "detection-rules-empty.png", "empty"),
        _capture_detection(application, "detection-rules-running.png", "running"),
        _capture_detection(application, "detection-rules-zero-incidents.png", "zero"),
        _capture_detection(
            application,
            "detection-rules-compact.png",
            "demo",
            (900, 700),
        ),
        _capture_detection(
            application,
            "detection-rules-results-compact.png",
            "compact-results",
            (900, 700),
        ),
        _capture(
            application,
            get_empty_dashboard_data(),
            "event-explorer-empty.png",
            False,
            screen_id="log_import",
        ),
        _capture(
            application,
            get_demo_dashboard_data(),
            "event-explorer-compact.png",
            True,
            (900, 700),
            screen_id="log_import",
        ),
        _capture_incidents(application, "incidents-reports-demo.png", "demo"),
        _capture_incidents(application, "incidents-reports-no-runs.png", "no-runs"),
        _capture_incidents(application, "incidents-reports-zero-incidents.png", "zero"),
        _capture_incidents(
            application, "incidents-reports-selected-evidence.png", "selected-evidence"
        ),
        _capture_incidents(
            application, "incidents-reports-no-linked-evidence.png", "no-evidence"
        ),
        _capture_incidents(
            application, "incidents-reports-unsaved-changes.png", "unsaved"
        ),
        _capture_incidents(application, "incidents-reports-saving.png", "saving"),
        _capture_incidents(
            application, "incidents-reports-save-success-preview.png", "save-success"
        ),
        _capture_incidents(
            application, "incidents-reports-save-failure.png", "save-failure"
        ),
        _capture_incidents(application, "incidents-reports-exporting.png", "exporting"),
        _capture_incidents(
            application,
            "incidents-reports-export-success-preview.png",
            "export-success",
        ),
        _capture_incidents(
            application, "incidents-reports-export-failure.png", "export-failure"
        ),
        _capture_incidents(
            application,
            "incidents-reports-service-unavailable.png",
            "service-unavailable",
        ),
        _capture_incidents(
            application,
            "incidents-reports-compact.png",
            "selected-evidence",
            (900, 700),
        ),
        _capture_incidents(
            application,
            "incidents-reports-compact-details.png",
            "compact-details",
            (900, 700),
        ),
        _capture_malformed_dialog(application),
        _capture_event_state(application, "event-explorer-loading.png", "loading"),
        _capture_event_state(application, "event-explorer-error.png", "error"),
        _capture_event_state(
            application, "event-import-progress.png", "import-progress"
        ),
        _capture_event_state(application, "event-import-failure.png", "import-failure"),
        _capture_event_state(application, "event-ip-details.png", "ip-details"),
        _capture_event_state(application, "focused-input.png", "focus"),
        _capture_event_compact_results(application),
        _capture_detection(
            application, "detection-history-loading.png", "history-loading"
        ),
        _capture_detection(application, "detection-history-error.png", "history-error"),
        _capture_detection(application, "detection-results-error.png", "results-error"),
        _capture_detection(application, "detection-failure.png", "failure"),
        _capture_regular_screen(
            application,
            "detection_rules",
            "detection-rules-service-unavailable.png",
        ),
    )
    for output in outputs:
        print(output)

    responsive_sizes = ((1440, 900), (1280, 800), (1024, 768), (900, 700))
    screen_ids = ("dashboard", "log_import", "detection_rules", "incidents_reports")
    for width, height in responsive_sizes:
        for screen_id in screen_ids:
            filename = f"redesign-{screen_id}-{width}x{height}.png"
            output = _capture(
                application,
                get_demo_dashboard_data(),
                filename,
                True,
                (width, height),
                screen_id=screen_id,
            )
            print(output)


if __name__ == "__main__":
    main()
