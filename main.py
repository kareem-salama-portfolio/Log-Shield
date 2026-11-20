"""Application entry point for LogShield."""

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from app.ui.screens.dashboard.data_provider import get_demo_dashboard_data, get_empty_dashboard_data
from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_dark_theme


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
            print("Usage: python main.py [--demo-data]\n\nLaunch LogShield with an empty workspace or synthetic dashboard values.")
            return 0
        else:
            remaining.append(argument)

    application = QApplication([sys.argv[0], *remaining])
    application.setApplicationName("LogShield")
    application.setOrganizationName("LogShield")
    apply_dark_theme(application)

    dashboard_data = get_demo_dashboard_data() if demo_mode else get_empty_dashboard_data()
    window = MainWindow(dashboard_data=dashboard_data, demo_mode=demo_mode)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
