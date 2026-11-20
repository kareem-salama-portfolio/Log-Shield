PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS log_files (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    imported_at TEXT NOT NULL,
    line_count INTEGER NOT NULL CHECK (line_count >= 0),
    malformed_count INTEGER NOT NULL CHECK (malformed_count >= 0)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES log_files(id) ON DELETE CASCADE,
    line_no INTEGER NOT NULL CHECK (line_no > 0),
    ts TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    username TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('FAILED', 'SUCCESS')),
    UNIQUE (file_id, line_no)
);
CREATE INDEX IF NOT EXISTS idx_events_ip_ts ON events(source_ip, ts);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS malformed_lines (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES log_files(id) ON DELETE CASCADE,
    line_no INTEGER NOT NULL CHECK (line_no > 0),
    raw_text TEXT NOT NULL,
    reason TEXT NOT NULL,
    UNIQUE (file_id, line_no)
);

CREATE TABLE IF NOT EXISTS detection_runs (
    id INTEGER PRIMARY KEY,
    threshold INTEGER NOT NULL CHECK (threshold BETWEEN 3 AND 20),
    window_seconds INTEGER NOT NULL CHECK (window_seconds BETWEEN 60 AND 3600),
    run_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES detection_runs(id) ON DELETE CASCADE,
    source_ip TEXT NOT NULL,
    start_ts TEXT NOT NULL,
    end_ts TEXT NOT NULL,
    failure_count INTEGER NOT NULL CHECK (failure_count >= 3),
    severity TEXT NOT NULL CHECK (severity IN ('MEDIUM', 'HIGH')),
    status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'REVIEWED', 'FALSE_POSITIVE')),
    note TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 500),
    status_updated_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_incidents_run ON incidents(run_id, start_ts);

CREATE TABLE IF NOT EXISTS incident_events (
    incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    PRIMARY KEY (incident_id, event_id)
);
