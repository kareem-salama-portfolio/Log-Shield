"""Smoke checks for the desktop application shell."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_dark_theme
from app.ui.styles.tokens import Colors


@pytest.fixture(scope="session")
def application() -> QApplication:
    """Create one Qt application for the UI smoke tests."""
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_dark_theme(instance)
    return instance


def test_main_window_has_application_title_and_usable_size(application: QApplication) -> None:
    window = MainWindow()

    assert window.windowTitle().startswith("LogShield")
    assert window.minimumWidth() >= 800
    assert window.minimumHeight() >= 560
    assert window.sidebar.items["dashboard"].property("active") == "true"
    assert window.dashboard.data["total_events"] == 0

    window.close()


def test_dark_theme_uses_logshield_design_tokens(application: QApplication) -> None:
    assert application.palette().window().color().name() == Colors.BACKGROUND.lower()
    assert "QTableWidget" in application.styleSheet()
    assert Colors.HIGH in application.styleSheet()


def test_navigation_switches_between_dashboard_and_event_explorer(application: QApplication) -> None:
    window = MainWindow()

    window.sidebar.items["log_import"].click()

    assert window.screen_stack.currentWidget() is window.event_explorer_scroll
    assert window.sidebar.items["log_import"].property("active") == "true"

    window.sidebar.items["dashboard"].click()

    assert window.screen_stack.currentWidget() is window.dashboard_scroll
    assert window.sidebar.items["dashboard"].property("active") == "true"
    window.close()


def test_dashboard_import_action_opens_event_explorer(application: QApplication) -> None:
    window = MainWindow()

    window.dashboard.empty_state.action_button.click()

    assert window.screen_stack.currentWidget() is window.event_explorer_scroll
    assert window.sidebar.items["log_import"].property("active") == "true"
    window.close()
