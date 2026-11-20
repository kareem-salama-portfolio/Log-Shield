"""Application services for import, event queries, detection and reports."""

import csv
import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from ipaddress import ip_address
from pathlib import Path

from app.algorithms.detection_engine import DetectionEngine
from app.algorithms.log_parser import LogParser
from app.database.repositories import DetectionRepository, LogRepository
from app.utils.errors import ValidationError
from app.utils.file_validation import validate_log_file


class LogService:
    def __init__(self, database):
        self.database = database
        self.logs = LogRepository(database)
        self.detections = DetectionRepository(database)
        self.parser = LogParser()

    def import_log_file(
        self, file_path: Path, progress_callback: Callable | None = None
    ):
        path = validate_log_file(file_path)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        sha = digest.hexdigest()
        with self.database.connect() as c:
            prior = c.execute(
                "SELECT imported_at FROM log_files WHERE sha256=?", (sha,)
            ).fetchone()
        if prior:
            raise ValueError(f"This file was already imported on {prior[0]}.")
        events = []
        bad = []
        total = 0
        size = max(path.stat().st_size, 1)
        with path.open("rb") as stream:
            number = 0
            while True:
                raw = stream.readline()
                if not raw:
                    break
                number += 1
                total += 1
                line = raw.decode("utf-8", errors="replace")
                result = self.parser.parse_line(line, number)
                if hasattr(result, "outcome"):
                    events.append(result)
                else:
                    bad.append(result)
                if progress_callback and (number % 100 == 0):
                    progress_callback(
                        {
                            "percentage": min(99, int(stream.tell() / size * 100)),
                            "status": f"Parsed {number} lines",
                        }
                    )
        imported = datetime.now().isoformat(timespec="seconds")
        try:
            with self.database.transaction() as c:
                file_id = self.logs.insert_file(
                    c, path.name, sha, imported, total, len(bad)
                )
                for event in events:
                    event.file_id = file_id
                    event.id = self.logs.insert_event(c, file_id, event)
                for item in bad:
                    self.logs.insert_malformed(c, file_id, item)
        except Exception as exc:
            if "UNIQUE constraint failed: log_files.sha256" in str(exc):
                raise ValueError(
                    "This file was imported by another operation."
                ) from exc
            raise
        if progress_callback:
            progress_callback({"percentage": 100, "status": "Import complete"})
        return {
            "import_id": file_id,
            "file_name": path.name,
            "imported_at": imported,
            "total_records": total,
            "accepted_records": len(events),
            "malformed_records": len(bad),
            "status": "IMPORTED",
        }

    def get_import_history(self, *, page, page_size):
        _validate_page(page, page_size)
        return self.logs.history(page, page_size)

    def get_malformed_records(self, import_id):
        return self.logs.malformed(import_id)

    def get_events(self, filters, *, page, page_size):
        _validate_page(page, page_size)
        _validate_event_filters(filters)
        return self.logs.events(filters, page, page_size)

    def get_ip_details(self, source_ip):
        try:
            normalized = str(ip_address(source_ip))
        except ValueError as error:
            raise ValidationError(
                "source_ip must be a valid IPv4 or IPv6 address."
            ) from error
        return self.logs.ip_details(normalized)

    def has_eligible_events(self):
        with self.database.connect() as c:
            return c.execute("SELECT EXISTS(SELECT 1 FROM events)").fetchone()[0] == 1

    def get_linked_events(self, event_ids):
        if not isinstance(event_ids, (list, tuple)) or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in event_ids
        ):
            raise ValidationError("event_ids must contain positive integer IDs.")
        return self.detections.evidence(list(dict.fromkeys(event_ids)))

    def dashboard(self):
        with self.database.connect() as c:
            totals = c.execute(
                "SELECT COUNT(*),SUM(outcome='FAILED'),COUNT(DISTINCT source_ip) FROM events"
            ).fetchone()
            incidents = c.execute(
                "SELECT SUM(severity='MEDIUM'),SUM(severity='HIGH') FROM incidents"
            ).fetchone()
            hours = c.execute(
                "SELECT substr(ts,1,13),COUNT(*) FROM events WHERE outcome='FAILED' GROUP BY 1 ORDER BY 1 DESC LIMIT 24"
            ).fetchall()
            ips = c.execute(
                "SELECT source_ip,COUNT(*) n FROM events WHERE outcome='FAILED' GROUP BY source_ip ORDER BY n DESC,source_ip LIMIT 10"
            ).fetchall()
            latest = c.execute(
                "SELECT i.id,i.run_id,i.source_ip,i.start_ts,i.end_ts,i.failure_count,i.severity,i.status,group_concat(ie.event_id) FROM incidents i LEFT JOIN incident_events ie ON ie.incident_id=i.id GROUP BY i.id ORDER BY i.id DESC LIMIT 8"
            ).fetchall()
        return {
            "total_events": totals[0] or 0,
            "failed_logins": totals[1] or 0,
            "unique_ips": totals[2] or 0,
            "medium_incidents": incidents[0] or 0,
            "high_incidents": incidents[1] or 0,
            "failed_per_hour": [
                {"hour": r[0][-5:], "failure_count": r[1]} for r in reversed(hours)
            ],
            "top_ips": [{"source_ip": r[0], "failure_count": r[1]} for r in ips],
            "latest_incidents": [
                {
                    "id": r[0],
                    "run_id": r[1],
                    "source_ip": r[2],
                    "start_time": r[3],
                    "end_time": r[4],
                    "failure_count": r[5],
                    "severity": r[6],
                    "status": r[7],
                    "event_ids": [int(value) for value in r[8].split(",")]
                    if r[8]
                    else [],
                }
                for r in latest
            ],
        }

    def run_detection(self, request, progress_callback=None):
        threshold = request["failure_threshold"]
        minutes = request["time_window_minutes"]
        events = self.logs.all_events()
        if not events:
            raise ValueError("Import authentication logs before running detection.")
        if progress_callback:
            progress_callback({"percentage": 15, "status": "Analyzing imported events"})
        incidents = DetectionEngine().detect(events, threshold, minutes)
        run_at = datetime.now().isoformat(timespec="seconds")
        with self.database.transaction() as c:
            run_id = self.detections.insert_run(c, threshold, minutes * 60, run_at)
            for incident in incidents:
                self.detections.insert_incident(c, run_id, incident)
        if progress_callback:
            progress_callback({"percentage": 100, "status": "Detection complete"})
        summary = next(r for r in self.detections.history() if r["run_id"] == run_id)
        return {"run": summary, "incidents": self.detections.incidents(run_id)}

    def get_run_history(self):
        return self.detections.history()

    def get_run_results(self, run_id):
        return self.detections.incidents(run_id)

    def save_review(self, run_id, incident_id, status, note):
        if not isinstance(note, str):
            raise ValidationError("Incident note must be text.")
        return self.detections.save_review(run_id, incident_id, status, note)

    def export_report(self, run_id, format_name, destination):
        run = next(
            (r for r in self.detections.history() if r["run_id"] == run_id), None
        )
        if run is None:
            raise ValueError("Detection run not found.")
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id < 1:
            raise ValidationError("run_id must be a positive integer.")
        if format_name not in {"csv", "json"}:
            raise ValidationError("Choose CSV or JSON.")
        if not isinstance(destination, (str, Path)) or not str(destination).strip():
            raise ValidationError("Choose an export destination.")
        incidents = self.detections.incidents(run_id)
        path = Path(destination)
        if format_name == "json":
            path.write_text(
                json.dumps(
                    {
                        "run": run,
                        "incidents": incidents,
                        "counts": {
                            "total": len(incidents),
                            "high": sum(i["severity"] == "HIGH" for i in incidents),
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        elif format_name == "csv":
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "run_id",
                        "failure_threshold",
                        "time_window_minutes",
                        "total_incidents",
                        "high_incidents",
                        "incident_id",
                        "source_ip",
                        "start_ts",
                        "end_ts",
                        "failure_count",
                        "severity",
                        "status",
                        "note",
                        "event_ids",
                    ],
                )
                writer.writeheader()
                if not incidents:
                    row = {
                        key: run[key]
                        for key in (
                            "run_id",
                            "failure_threshold",
                            "time_window_minutes",
                            "total_incidents",
                            "high_incidents",
                        )
                    }
                    writer.writerow(row)
                for i in incidents:
                    row = {
                        key: run[key]
                        for key in (
                            "run_id",
                            "failure_threshold",
                            "time_window_minutes",
                            "total_incidents",
                            "high_incidents",
                        )
                    }
                    row.update(
                        {
                            "incident_id": i["id"],
                            "source_ip": i["source_ip"],
                            "start_ts": i["start_ts"],
                            "end_ts": i["end_ts"],
                            "failure_count": i["failure_count"],
                            "severity": i["severity"],
                            "status": i["status"],
                            "note": i["note"],
                            "event_ids": ";".join(map(str, i["event_ids"])),
                        }
                    )
                    writer.writerow(row)
        return str(path)


def _validate_page(page, page_size):
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise ValidationError("page must be a positive integer.")
    if (
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
        or not 1 <= page_size <= 200
    ):
        raise ValidationError("page_size must be between 1 and 200.")


def _validate_event_filters(filters):
    if not isinstance(filters, dict):
        raise ValidationError("Event filters must be a mapping.")
    outcome = filters.get("outcome")
    if outcome not in (None, "", "FAILED", "SUCCESS"):
        raise ValidationError("outcome must be FAILED or SUCCESS.")
    start_value, end_value = filters.get("start_time"), filters.get("end_time")
    try:
        start = datetime.fromisoformat(start_value) if start_value else None
        end = datetime.fromisoformat(end_value) if end_value else None
    except (TypeError, ValueError) as error:
        raise ValidationError(
            "Time filters must be valid ISO-8601 timestamps."
        ) from error
    if (
        start is not None
        and start.tzinfo is not None
        or end is not None
        and end.tzinfo is not None
    ):
        raise ValidationError("Time filters must not include a timezone offset.")
    if start is not None and end is not None and start > end:
        raise ValidationError("Start time must not be later than end time.")
