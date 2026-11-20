"""Application entry point for LogShield."""

import os
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIRECTORY / "data" / "matplotlib"))

from PySide6.QtWidgets import QApplication

from app.database.connection import Database
from app.services.application_services import LogService
from app.ui.main_window import MainWindow
from app.ui.screens.dashboard.data_provider import (
    get_demo_dashboard_data,
    get_empty_dashboard_data,
)
from app.ui.styles.theme import apply_dark_theme
from app.utils.logging_config import configure_logging


def main(argv: Sequence[str] | None = None) -> int:
    """Create and run the desktop application.

    ``--demo-data`` selects clearly synthetic values for UI review. Normal
    launches start with the truthful empty dashboard until a service exists.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    demo_mode = False
    remaining: list[str] = []
    while arguments:
        argument = arguments.pop(0)
        if argument in {"--demo-data", "--demo"}:
            demo_mode = True
        elif argument in {"-h", "--help"}:
            print(
                "Usage: python main.py [--demo-data]\n\nLaunch LogShield with an empty workspace or synthetic dashboard values."
            )
            return 0
        else:
            remaining.append(argument)

    application = QApplication([sys.argv[0], *remaining])
    application.setApplicationName("LogShield")
    application.setOrganizationName("LogShield")
    apply_dark_theme(application)

    dashboard_data = (
        get_demo_dashboard_data() if demo_mode else get_empty_dashboard_data()
    )
    data_directory = Path(__file__).parent / "data"
    configure_logging(data_directory)
    service = (
        None if demo_mode else LogService(Database(data_directory / "logshield.db"))
    )
    if service is not None:
        dashboard_data = service.dashboard()
    window = MainWindow(
        dashboard_data=dashboard_data,
        demo_mode=demo_mode,
        import_service=service,
        event_service=service,
        detection_service=service,
        dashboard_service=service,
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
