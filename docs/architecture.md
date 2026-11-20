# Architecture

```text
PySide6 screens -> application services -> algorithms and repositories -> SQLite
```

- Widgets emit user requests and display plain service responses. They do not issue SQL.
- The import screen delegates file parsing to an import worker; detection/history calls use the detection worker. Qt signals return progress/results to the GUI thread.
- `LogService` coordinates the parser/detection engine with repositories and the database. The parser and detection engine remain GUI-independent and database-independent.
- `Database` creates the schema on startup, enables foreign keys on every connection, closes connections deterministically, and provides explicit write transactions.
- `LogRepository` owns log files, malformed lines, event queries and per-IP aggregates. `DetectionRepository` owns reproducible runs, incidents, evidence links and review state.
- All user values passed to SQLite use parameterized queries. Schema checks enforce event outcomes, detection bounds, incident status/severity, unique source-file hashes, and per-file line uniqueness.
- Synthetic preview providers are separate from the production database services. Demo mode is read-only.

## Storage and workflows

A file's SHA-256 digest is checked before import and protected by a UNIQUE constraint during the transaction. Valid events and malformed lines are stored with the log-file row in one transaction. Detection sorts eligible events by timestamp and source line, applies an inclusive sliding window independently per IP, then persists a run and all incidents/evidence links atomically. Status and note updates are scoped to both run ID and incident ID and record the change timestamp. Report exports use backend-owned run parameters and incident records.

The dashboard aggregates stored event and incident data. Event search/filter requests are paged in SQL and combine supplied filters with AND semantics. The incident detail view retrieves its exact linked event IDs rather than substituting a general IP query.
