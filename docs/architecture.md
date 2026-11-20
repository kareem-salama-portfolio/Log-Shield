# Architecture boundaries

The project separates presentation, application workflows, analysis, and persistence:

```text
UI screens and widgets -> service interfaces -> algorithms and database layer
```

- UI screens do not issue SQL. They call services and render returned application data.
- Services expose workflows using plain Python values and models. They do not import PySide6 widgets.
- Algorithms remain independent of Qt and persistence so they can be called and tested on their own.
- The database package owns SQLite access, schema changes, and queries. Other layers do not open connections or issue SQL.
- Potentially slow imports and analysis must be run away from the GUI event loop. When those workflows are implemented, the UI integration should dispatch work through Qt's worker/thread facilities and deliver results back to widgets on the GUI thread. Service and algorithm code must remain usable without a GUI event loop.
- SQLite and local files keep analysis data on the user's device; network access is not part of the application architecture.

The four primary screens are the Security Overview Dashboard, Log Import and Event Explorer, Detection Rules and Runs, and Incidents and Reports. `app/ui/navigation.py` records their stable identifiers and labels. All four are implemented in the shared main-window stack and use the same navigation shell.

The dashboard consumes the plain `DashboardData` structure in `app/models/dashboard.py`. `app/ui/screens/dashboard/data_provider.py` currently supplies an empty snapshot by default and fixed synthetic values for visual review. It contains no SQL, parsing, or detection logic. When a dashboard service is implemented, wire it at the application entry point in `main.py` and pass its returned structure to `MainWindow(dashboard_data=...)`. The UI can then continue to render that data without owning data access.

## Log import and event service boundary

No production import or event services exist yet. The plain data structures live in `app/models/log_import.py`; the structural service protocols live in `app/services/ui_contracts.py`. They are a single future integration boundary, not working backend implementations.

| UI operation | Request | Response |
|---|---|---|
| Import file | Validated local `Path` | `ImportHistoryRecord`: opaque `import_id`, `file_name`, `imported_at`, `total_records`, `accepted_records`, `malformed_records`, `status` |
| Import history | `page`, `page_size` | `ImportHistoryPage`: `items`, `page`, `page_size`, optional `total_count` |
| Filtered events | `EventFilters` (optional source IP, username, outcome, ISO start/end) plus `page` and `page_size` | `EventPage`: page of expected event records, page metadata, optional total count |
| IP details | `source_ip` | `IPDetails`: total/failed/successful counts, first/last seen, and backend-provided activity buckets |
| Malformed records | opaque `import_id` | line number, raw text, and parser-supplied reason for each record |

Supplied filter fields are combined with AND semantics. Event requests use a default page size of 200; the UI displays at most the returned page and never filters a complete event collection locally. Import history includes an opaque `import_id` so malformed details can be requested without deriving an identifier from the file name.

The file picker restricts selection to `.log` and `.txt`; `app/utils/file_validation.py` checks only the extension, regular-file status, and 20 MB size limit. It never opens or parses file contents. A valid selection emits `EventExplorer.import_requested`; with no ImportService attached, the UI states that the file was not imported. Future import calls must run in a worker, forward `ImportProgress` updates over Qt signals, and call the result slot only after the service confirms completion.

`app/ui/screens/log_import/data_provider.py` supplies an empty history/page and fixed synthetic records for visual development. `main.py --demo-data` opts into those fixtures. The mock provider returns pages and whole-IP summaries; it is kept separate from widgets and contains no parser, SQL, severity classification, or detection code. Regular launches remain empty and do not fabricate import history.

## Detection rules and run service boundary

`app/models/detection.py` defines plain request and response shapes. `app/services/ui_contracts.py` extends the existing `EventService` with `has_eligible_events()` and defines the `DetectionService` protocol:

| UI operation | Request | Response |
|---|---|---|
| Check run readiness | No parameters | Boolean from `EventService.has_eligible_events()` |
| Start detection | `failure_threshold`, `time_window_minutes` | Confirmed `DetectionRunResult` containing a run summary and the returned incident records |
| Load run history | No parameters | Run summaries containing run ID, start time, configured threshold/window, total incidents, and HIGH incidents |
| Load selected run | `run_id` | Incident records belonging to that run |

The HIGH severity checkbox remains a UI-only value. The detection request includes only threshold and time window because no agreed backend meaning exists for that toggle. Its operational semantics require confirmation from the backend and algorithm owners before it can be sent.

`app/ui/screens/detection_rules/run_worker.py` executes detection, history, and selected-run result service calls on a Qt worker thread. The service protocol uses plain Python types and callbacks; it does not depend on PySide6. Optional progress fields are rendered only when supplied. A run result is added to history only after the service returns it. Failed runs leave previously displayed history intact.

The backend owns brute-force detection, sliding-window calculations and inclusive boundaries, incident grouping/merging, severity classification, successful-login escalation, and persistence. The UI only submits the agreed threshold/window and renders returned incident fields with the existing severity badge. It does not calculate detection windows, group incidents, infer severity, or derive totals. Results are scoped to the selected `run_id`; stale asynchronous responses are ignored and mismatched incident records are not shown. Selecting an incident emits an integration signal to Incidents & Reports with the originating run and incident selected.

`app/ui/screens/detection_rules/data_provider.py` contains explicitly synthetic historical data for demo mode only. It includes multiple run IDs, a zero-incident run, and sample MEDIUM and HIGH incidents. It never executes a detection run. The regular launch displays service-unavailable states until an EventService and DetectionService are connected.

Use `python main.py --demo-data` only for visual development. A regular launch uses zero dashboard values, an empty import history and event page, and the dashboard import prompt. Dashboard incident summaries do not include run or incident IDs, so they open Incidents & Reports without selecting a record; Detection Rules handoff carries the exact run and selected incident.

## Incidents & Reports service boundary

`app/ui/screens/incidents_reports/` renders detection run summaries, the incidents returned for the selected run, incident contract fields, linked evidence, analyst review inputs, and run-level export actions. It reuses `DetectionService.get_run_history()` and `DetectionService.get_run_results(run_id)` through the existing `DetectionServiceWorker`. The screen does not run detection or mix records from different runs. Selecting an incident in Detection Rules passes its run and selected result set to Incidents & Reports.

The current service protocols do not yet support all Incidents & Reports actions:

| UI action | Existing contract | Missing capability before production integration |
|---|---|---|
| Load incident evidence | `EventService.get_events()` returns a filtered page | An exact lookup for events linked to an incident, keyed by its `event_ids`, with a clear stale/missing-event response. A paged IP query is not an equivalent substitute. |
| Save analyst review | `DetectionIncident` has `status` and `note` fields | A review-save operation keyed by run and incident, returning the persisted incident after confirmation. The backend must own persistence and any review timestamps. |
| Export CSV or JSON | No export protocol is defined | An export operation accepting the selected run, format, and destination and returning a confirmed path or a useful failure. It must include run parameters/counts from backend-owned data. |

The screen exposes Qt request signals for these missing service operations. Until services are connected, evidence displays a service-unavailable state, review save reports that no changes were saved, and CSV/JSON export reports that no report was written. The native Qt file picker selects the destination; the UI does not build report contents or write files. Future review/export operations must run away from the GUI thread and return confirmed results or errors through Qt signals.

`app/ui/screens/incidents_reports/data_provider.py` contains isolated synthetic evidence fixtures for `--demo-data` only. The fixtures are filtered by the incident's `event_ids` in that demo provider and include failed and successful outcomes plus an incident with no linked evidence. Normal application mode does not load these fixtures. Detection run history/results in the existing detection demo provider also include a zero-incident run and the review status variants.
