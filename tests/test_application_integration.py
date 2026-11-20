"""A real GUI-to-service workflow using a temporary SQLite database."""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtWidgets import QApplication

from app.database.connection import Database
from app.services.application_services import LogService
from app.ui.main_window import MainWindow
from app.ui.screens.dashboard.data_provider import get_empty_dashboard_data
from app.ui.styles.theme import apply_dark_theme

LINES = (
    "2026-10-02T08:00:10 sshd[2211]: Failed password for admin from 203.0.113.7 port 52144",
    "2026-10-02T08:02:30 sshd[2212]: Failed password for admin from 203.0.113.7 port 52145",
    "2026-10-02T08:04:00 sshd[2213]: Failed password for admin from 203.0.113.7 port 52146",
    "2026-10-02T08:07:45 sshd[2214]: Failed password for admin from 203.0.113.7 port 52147",
    "2026-10-02T08:09:55 sshd[2215]: Failed password for admin from 203.0.113.7 port 52148",
    "2026-10-02T08:12:00 sshd[2216]: Accepted password for admin from 203.0.113.7 port 52149",
)


@pytest.fixture
def application():
    app = QApplication.instance() or QApplication([])
    apply_dark_theme(app)
    return app


def _wait(app, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return predicate()


def test_ui_import_detection_and_review_use_persistent_services(application, tmp_path):
    source = tmp_path / "auth_sample.log"
    source.write_text("\n".join(LINES), encoding="utf-8")
    service = LogService(Database(tmp_path / "logshield.db"))
    window = MainWindow(
        dashboard_data=get_empty_dashboard_data(),
        import_service=service,
        event_service=service,
        detection_service=service,
        dashboard_service=service,
    )
    window._handle_import_request(str(source))
    assert _wait(application, lambda: window._import_worker is None)
    assert service.has_eligible_events()
    assert window.dashboard.data["total_events"] == 6
    window.detection_rules.set_event_availability(True)
    assert window.detection_rules.rule_settings.request_detection()
    assert _wait(application, lambda: len(service.get_run_history()) == 1)
    application.processEvents()
    run = service.get_run_history()[0]
    incidents = service.get_run_results(run["run_id"])
    assert len(incidents) == 1 and incidents[0]["severity"] == "HIGH"
    summary = window.dashboard.data["latest_incidents"][0]
    assert summary["id"] == incidents[0]["id"]
    window._handle_incident_open_request(dict(summary))
    assert window.incidents_reports.selected_incident["id"] == incidents[0]["id"]
    window.close()
