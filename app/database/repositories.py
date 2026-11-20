"""Parameterized SQLite repositories for LogShield workflows."""

from datetime import datetime

from app.models.event import Event


class LogRepository:
    def __init__(self, database):
        self.database = database

    def insert_file(self, conn, filename, digest, imported_at, total, malformed):
        return conn.execute(
            "INSERT INTO log_files(filename,sha256,imported_at,line_count,malformed_count) VALUES(?,?,?,?,?)",
            (filename, digest, imported_at, total, malformed),
        ).lastrowid

    def insert_event(self, conn, file_id, event):
        return conn.execute(
            "INSERT INTO events(file_id,line_no,ts,source_ip,username,outcome) VALUES(?,?,?,?,?,?)",
            (
                file_id,
                event.line_no,
                event.timestamp.isoformat(),
                event.source_ip,
                event.username,
                event.outcome,
            ),
        ).lastrowid

    def insert_malformed(self, conn, file_id, item):
        conn.execute(
            "INSERT INTO malformed_lines(file_id,line_no,raw_text,reason) VALUES(?,?,?,?)",
            (file_id, item.line_no, item.line_raw, item.reason),
        )

    def history(self, page, page_size):
        with self.database.connect() as c:
            total = c.execute("SELECT COUNT(*) FROM log_files").fetchone()[0]
            rows = c.execute(
                "SELECT id,filename,imported_at,line_count,malformed_count FROM log_files ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, (page - 1) * page_size),
            ).fetchall()
        return {
            "items": [
                {
                    "import_id": r[0],
                    "file_name": r[1],
                    "imported_at": r[2],
                    "total_records": r[3],
                    "accepted_records": r[3] - r[4],
                    "malformed_records": r[4],
                    "status": "IMPORTED",
                }
                for r in rows
            ],
            "page": page,
            "page_size": page_size,
            "total_count": total,
        }

    def malformed(self, file_id):
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT line_no,raw_text,reason FROM malformed_lines WHERE file_id=? ORDER BY line_no",
                (file_id,),
            ).fetchall()
        return [{"line_no": r[0], "raw_text": r[1], "reason": r[2]} for r in rows]

    def events(self, filters, page, page_size):
        clauses = []
        args = []
        for field in ("source_ip", "username", "outcome"):
            value = filters.get(field)
            if value:
                clauses.append(f"{field} = ?")
                args.append(value)
        for field, op in (("start_time", ">="), ("end_time", "<=")):
            value = filters.get(field)
            if value:
                clauses.append(f"ts {op} ?")
                args.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as c:
            total = c.execute("SELECT COUNT(*) FROM events" + where, args).fetchone()[0]
            rows = c.execute(
                "SELECT id,ts,source_ip,username,outcome,file_id,line_no FROM events"
                + where
                + " ORDER BY ts,line_no LIMIT ? OFFSET ?",
                (*args, page_size, (page - 1) * page_size),
            ).fetchall()
        return {
            "items": [
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "source_ip": r[2],
                    "username": r[3],
                    "outcome": r[4],
                    "file_id": r[5],
                    "line_no": r[6],
                }
                for r in rows
            ],
            "page": page,
            "page_size": page_size,
            "total_count": total,
        }

    def all_events(self):
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT id,file_id,line_no,ts,source_ip,username,outcome FROM events ORDER BY ts,line_no"
            ).fetchall()
        return [
            Event(
                id=r[0],
                file_id=r[1],
                line_no=r[2],
                timestamp=datetime.fromisoformat(r[3]),
                source_ip=r[4],
                username=r[5],
                outcome=r[6],
            )
            for r in rows
        ]

    def ip_details(self, ip):
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT ts,outcome FROM events WHERE source_ip=? ORDER BY ts", (ip,)
            ).fetchall()
        if not rows:
            return None
        buckets = {}
        for r in rows:
            hour = r[0][:13]
            buckets[hour] = buckets.get(hour, 0) + 1
        return {
            "source_ip": ip,
            "total_events": len(rows),
            "failed_logins": sum(r[1] == "FAILED" for r in rows),
            "successful_logins": sum(r[1] == "SUCCESS" for r in rows),
            "first_seen": rows[0][0],
            "last_seen": rows[-1][0],
            "activity": [
                {"timestamp": k, "event_count": v} for k, v in buckets.items()
            ],
        }


class DetectionRepository:
    def __init__(self, database):
        self.database = database

    def insert_run(self, conn, threshold, seconds, run_at):
        return conn.execute(
            "INSERT INTO detection_runs(threshold,window_seconds,run_at) VALUES(?,?,?)",
            (threshold, seconds, run_at),
        ).lastrowid

    def insert_incident(self, conn, run_id, incident):
        from datetime import datetime

        incident_id = conn.execute(
            "INSERT INTO incidents(run_id,source_ip,start_ts,end_ts,failure_count,severity,status,note,status_updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                incident.source_ip,
                incident.start_ts.isoformat(),
                incident.end_ts.isoformat(),
                incident.failure_count,
                incident.severity,
                incident.status,
                incident.note,
                datetime.now().isoformat(timespec="seconds"),
            ),
        ).lastrowid
        conn.executemany(
            "INSERT INTO incident_events(incident_id,event_id) VALUES(?,?)",
            ((incident_id, eid) for eid in incident.event_ids),
        )

    def history(self):
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT r.id,r.run_at,r.threshold,r.window_seconds,COUNT(i.id),SUM(CASE WHEN i.severity='HIGH' THEN 1 ELSE 0 END) FROM detection_runs r LEFT JOIN incidents i ON i.run_id=r.id GROUP BY r.id ORDER BY r.id DESC"
            ).fetchall()
        return [
            {
                "run_id": r[0],
                "started_at": r[1],
                "failure_threshold": r[2],
                "time_window_minutes": r[3] // 60,
                "total_incidents": r[4],
                "high_incidents": r[5] or 0,
            }
            for r in rows
        ]

    def incidents(self, run_id):
        with self.database.connect() as c:
            rows = c.execute(
                "SELECT id,run_id,source_ip,start_ts,end_ts,failure_count,severity,status,note,status_updated_at FROM incidents WHERE run_id=? ORDER BY start_ts,id",
                (run_id,),
            ).fetchall()
            out = []
            for r in rows:
                ids = [
                    x[0]
                    for x in c.execute(
                        "SELECT event_id FROM incident_events WHERE incident_id=? ORDER BY event_id",
                        (r[0],),
                    )
                ]
                out.append(
                    {
                        "id": r[0],
                        "run_id": r[1],
                        "source_ip": r[2],
                        "start_ts": r[3],
                        "end_ts": r[4],
                        "failure_count": r[5],
                        "severity": r[6],
                        "status": r[7],
                        "note": r[8],
                        "status_updated_at": r[9],
                        "event_ids": ids,
                    }
                )
        return out

    def evidence(self, event_ids):
        if not event_ids:
            return []
        marks = ",".join("?" for _ in event_ids)
        with self.database.connect() as c:
            rows = c.execute(
                f"SELECT id,ts,source_ip,username,outcome,file_id,line_no FROM events WHERE id IN ({marks}) ORDER BY ts,line_no",
                tuple(event_ids),
            ).fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "source_ip": r[2],
                "username": r[3],
                "outcome": r[4],
                "file_id": r[5],
                "line_no": r[6],
            }
            for r in rows
        ]

    def save_review(self, run_id, incident_id, status, note):
        if status not in {"NEW", "REVIEWED", "FALSE_POSITIVE"} or len(note) > 500:
            raise ValueError("Invalid incident review values.")
        with self.database.transaction() as c:
            from datetime import datetime

            cur = c.execute(
                "UPDATE incidents SET status=?,note=?,status_updated_at=? WHERE run_id=? AND id=?",
                (
                    status,
                    note,
                    datetime.now().isoformat(timespec="seconds"),
                    run_id,
                    incident_id,
                ),
            )
            if not cur.rowcount:
                raise ValueError("Incident does not belong to the selected run.")
        return next(i for i in self.incidents(run_id) if i["id"] == incident_id)
