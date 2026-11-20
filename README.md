# LogShield

LogShield is an offline desktop application foundation for analyzing local authentication logs, reviewing suspicious login activity, grouping detections into incidents, and exporting reports. It is built with Python, PySide6, SQLite, and Matplotlib.

This repository contains the desktop shell, shared Burgundy and Rose glass design system, Security Overview Dashboard, Log Import & Event Explorer, Detection Rules & Runs, and Incidents & Reports. The production log parser, import/event services, persistence, detection algorithm, incident-review persistence, exact evidence lookup, and report export service are not connected yet.

## Requirements

- Python 3.11 or 3.12
- A graphical desktop environment supported by Qt

SQLite is included with Python. Runtime package versions are listed in `requirements.txt`; pytest is included in `requirements-dev.txt`.

## Set up

From the repository directory, create and activate a virtual environment in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

For Python 3.12, replace `py -3.11` with `py -3.12`.

On macOS or Linux, create and activate the environment with:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Run

With the virtual environment active, launch the desktop application:

```sh
python main.py
```

The default launch uses an empty local workspace and displays “Import a log file to begin.” The import and detection screens report when their backend services are unavailable. File selection checks extension and size locally; without an ImportService it explicitly leaves the file unimported. To preview the implemented screens with isolated synthetic data, run:

```sh
python main.py --demo-data
```

On Windows, render review captures of the implemented screens, major dialogs, and key empty, loading, error, review, export, and compact states with:

```powershell
python tools\capture_dashboard_previews.py
```

The PNG files are saved under `screenshots/`. The responsive review set covers 1440×900, 1280×800, 1024×768, and 900×700 logical pixels.

## Run tests

```sh
python -m pytest
```

## Project layout

- `app/ui/` contains the desktop shell, presentation code, reusable widgets, screen packages, and visual theme.
- `app/ui/styles/tokens.py` is the source for color, type, spacing, radius, and component style tokens.
- `app/ui/widgets/` contains shared buttons, cards, navigation, severity badges, icons, and table styling.
- `app/ui/screens/dashboard/` contains the Security Overview Dashboard, Matplotlib charts, and its temporary data adapter.
- `app/ui/screens/log_import/` contains file controls, filters, import history, paged event table, IP details, malformed-record dialog, and an isolated demo adapter.
- `app/ui/screens/detection_rules/` contains rule settings, run history, selected-run results, a Qt worker adapter, and an isolated synthetic history provider. It does not run detection logic.
- `app/ui/screens/incidents_reports/` contains run-scoped incident review, linked evidence display, unsaved-change handling, and native CSV/JSON destination selection. Review saving, exact evidence lookup, and report creation remain service integration points.
- `app/services/` is the boundary for application workflows exposed to the UI.
- `app/services/ui_contracts.py` and `app/models/` define the import, event, and detection service boundaries and plain data fields. See `docs/architecture.md` for the missing Incidents & Reports service capabilities.
- `app/algorithms/` will hold GUI-independent detection and analysis logic.
- `app/models/` will hold application data structures.
- `app/database/` will isolate SQLite connections, schema, and persistence operations.
- `app/utils/` will contain small shared helpers without UI or persistence responsibilities.
- `data/` is reserved for local runtime data and is ignored by Git.
- `docs/architecture.md` records the dependency boundaries for future implementation.
- `design-system/logshield/MASTER.md` records the UI/UX Pro Max-informed visual rules used by the dashboard.
- `tests/` contains automated checks.

The HIGH severity option is visible for design continuity, but it is intentionally excluded from run requests until its operational meaning is confirmed by the backend and algorithm owners. The regular application launch never displays synthetic runs; `--demo-data` labels its history as synthetic and does not start a run.
