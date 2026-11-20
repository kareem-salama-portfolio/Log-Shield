"""Persistence and end-to-end workflow checks for application services."""

import json

import pytest

from app.database.connection import Database
from app.services.application_services import LogService
from app.utils.errors import ValidationError

SAMPLE = (
    "2026-10-02T08:00:10 sshd[2211]: Failed password for admin from 203.0.113.7 port 52144",
    "2026-10-02T08:02:30 sshd[2212]: Failed password for admin from 203.0.113.7 port 52145",
    "2026-10-02T08:04:00 sshd[2213]: Failed password for admin from 203.0.113.7 port 52146",
    "2026-10-02T08:07:45 sshd[2214]: Failed password for admin from 203.0.113.7 port 52147",
    "2026-10-02T08:09:55 sshd[2215]: Failed password for admin from 203.0.113.7 port 52148",
    "2026-10-02T08:12:00 sshd[2216]: Accepted password for admin from 203.0.113.7 port 52149",
    "not a valid authentication line",
)


@pytest.fixture
def service(tmp_path):
    return LogService(Database(tmp_path / "logshield.db"))


def test_import_persists_valid_and_malformed_and_reports_progress(service, tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("\n".join(SAMPLE) + "\n", encoding="utf-8")
    progress = []
    result = service.import_log_file(source, progress.append)
    assert (
        result["total_records"] == 7
        and result["accepted_records"] == 6
        and result["malformed_records"] == 1
    )
    assert (
        service.get_import_history(page=1, page_size=10)["items"][0]["import_id"]
        == result["import_id"]
    )
    assert (
        service.get_malformed_records(result["import_id"])[0]["reason"]
        == "UNKNOWN_PATTERN"
    )
    assert progress[-1]["percentage"] == 100


def test_same_file_is_rejected_without_duplicating_rows(service, tmp_path):
    source = tmp_path / "sample.log"
    source.write_text("\n".join(SAMPLE), encoding="utf-8")
    service.import_log_file(source)
    with pytest.raises(ValueError, match="already imported"):
        service.import_log_file(source)
    assert (
        service.get_events(
            {
                "source_ip": None,
                "username": None,
                "outcome": None,
                "start_time": None,
                "end_time": None,
            },
            page=1,
            page_size=200,
        )["total_count"]
        == 6
    )


def test_detection_saves_worked_example_review_evidence_and_exports(service, tmp_path):
    source = tmp_path / "auth.log"
    source.write_text("\n".join(SAMPLE[:6]), encoding="utf-8")
    service.import_log_file(source)
    result = service.run_detection({"failure_threshold": 5, "time_window_minutes": 10})
    assert len(result["incidents"]) == 1
    incident = result["incidents"][0]
    assert (
        incident["failure_count"] == 5
        and incident["severity"] == "HIGH"
        and len(incident["event_ids"]) == 6
    )
    assert len(service.get_linked_events(incident["event_ids"])) == 6
    saved = service.save_review(
        result["run"]["run_id"], incident["id"], "REVIEWED", "triaged"
    )
    assert saved["status"] == "REVIEWED" and saved["note"] == "triaged"
    assert saved["status_updated_at"]
    output = tmp_path / "report.json"
    service.export_report(result["run"]["run_id"], "json", output)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert (
        report["run"]["run_id"] == result["run"]["run_id"]
        and len(report["incidents"]) == 1
    )
    csv_path = tmp_path / "report.csv"
    service.export_report(result["run"]["run_id"], "csv", csv_path)
    assert "failure_threshold" in csv_path.read_text(encoding="utf-8-sig")


def test_database_constraints_and_cascade_are_enabled(service, tmp_path):
    source = tmp_path / "auth.txt"
    source.write_text(SAMPLE[0], encoding="utf-8")
    imported = service.import_log_file(source)
    with service.database.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        conn.execute("DELETE FROM log_files WHERE id=?", (imported["import_id"],))
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_zero_incident_reports_are_valid_and_explicit(service, tmp_path):
    source = tmp_path / "benign.log"
    source.write_text(
        "\n".join(  # noqa: FLY002 - keep the fixture as separate log records
            (
                "2026-10-02T08:00:00 sshd[1]: Failed password for admin from 192.0.2.1 port 22",
                "2026-10-02T08:20:00 sshd[2]: Failed password for admin from 192.0.2.1 port 22",
            )
        ),
        encoding="utf-8",
    )
    service.import_log_file(source)
    run = service.run_detection({"failure_threshold": 5, "time_window_minutes": 10})
    assert run["run"]["total_incidents"] == 0
    json_path = tmp_path / "empty.json"
    csv_path = tmp_path / "empty.csv"
    service.export_report(run["run"]["run_id"], "json", json_path)
    service.export_report(run["run"]["run_id"], "csv", csv_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["counts"]["total"] == 0
    assert "0" in csv_path.read_text(encoding="utf-8-sig")


def test_service_layer_rejects_invalid_paging_filters_and_review_values(service):
    with pytest.raises(ValidationError):
        service.get_events(
            {
                "source_ip": None,
                "username": None,
                "outcome": None,
                "start_time": "yesterday",
                "end_time": None,
            },
            page=1,
            page_size=200,
        )
    with pytest.raises(ValidationError):
        service.get_import_history(page=0, page_size=200)
    with pytest.raises(ValidationError):
        service.get_events(
            {
                "source_ip": None,
                "username": None,
                "outcome": None,
                "start_time": None,
                "end_time": None,
            },
            page=1,
            page_size=201,
        )
    with pytest.raises(ValidationError):
        service.save_review(1, 1, "REVIEWED", None)
