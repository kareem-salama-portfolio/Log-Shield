"""Behavior checks for the first complete LogShield screen."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.screens.dashboard.dashboard import Dashboard
from app.ui.screens.dashboard.data_provider import (
    get_demo_dashboard_data,
    get_empty_dashboard_data,
)
from app.ui.main_window import MainWindow
from app.ui.styles.theme import apply_dark_theme
from app.ui.widgets.components import SeverityBadge
from app.ui.widgets.styled_table import StyledTable


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_dark_theme(instance)
    return instance


def test_empty_dashboard_is_truthful_and_shows_import_action(application: QApplication) -> None:
    dashboard = Dashboard(get_empty_dashboard_data())

    assert not dashboard.empty_state.isHidden()
    assert dashboard.empty_state.title_label.text() == "Import a log file to begin"
    assert [card.value_label.text() for card in dashboard.metric_cards] == ["0", "0", "0", "0"]
    assert not dashboard.incident_empty_label.isHidden()
    assert "No hourly failure data" in dashboard.failed_chart.axes.texts[0].get_text()
    assert "No source IP rankings" in dashboard.top_ips_chart.axes.texts[0].get_text()
    assert dashboard.incident_table.rowCount() == 0

    dashboard.close()


def test_demo_dashboard_renders_contract_metrics_charts_and_incidents(application: QApplication) -> None:
    dashboard = Dashboard(get_demo_dashboard_data(), demo_mode=True)

    assert dashboard.empty_state.isHidden()
    assert dashboard.mode_indicator.text() == "DEMONSTRATION DATA"
    assert [card.value_label.text() for card in dashboard.metric_cards] == ["1,240", "340", "42", "4"]
    assert len(dashboard.failed_chart.axes.lines) == 1
    assert len(dashboard.top_ips_chart.axes.patches) == 5
    assert dashboard.incident_table.rowCount() == 4
    assert dashboard.incident_table.cellWidget(0, 4).text() == "HIGH"

    dashboard.close()


def test_dashboard_exposes_import_and_incident_integration_signals(application: QApplication) -> None:
    dashboard = Dashboard(get_demo_dashboard_data(), demo_mode=True)
    routes: list[str] = []
    opened: list[object] = []
    dashboard.navigation_requested.connect(routes.append)
    dashboard.incident_open_requested.connect(opened.append)

    dashboard.empty_state.action_button.click()
    dashboard._open_incident_at_row(0, 0)

    assert routes == ["log_import"]
    assert opened[0]["source_ip"] == "203.0.113.87"
    dashboard.close()


def test_dashboard_can_switch_between_empty_and_demo_snapshots(application: QApplication) -> None:
    dashboard = Dashboard(get_empty_dashboard_data())

    dashboard.update_data(get_demo_dashboard_data(), demo_mode=True)
    assert dashboard.empty_state.isHidden()
    assert dashboard.mode_indicator.text() == "DEMONSTRATION DATA"
    assert dashboard.metric_cards[0].value_label.text() == "1,240"

    dashboard.update_data(get_empty_dashboard_data())
    assert not dashboard.empty_state.isHidden()
    assert dashboard.mode_indicator.text() == "NO DATA IMPORTED"
    assert dashboard.metric_cards[0].value_label.text() == "0"
    dashboard.close()


def test_unrecognized_incident_severity_is_shown_without_reclassification(application: QApplication) -> None:
    data = get_demo_dashboard_data()
    data["latest_incidents"][0]["severity"] = "Critical"

    dashboard = Dashboard(data, demo_mode=True)
    badge = dashboard.incident_table.cellWidget(0, 4)

    assert badge.text() == "CRITICAL"
    assert badge.property("severity") == "UNKNOWN"
    dashboard.close()


def test_dashboard_layout_reflows_for_small_and_wide_windows(application: QApplication) -> None:
    dashboard = Dashboard(get_demo_dashboard_data(), demo_mode=True)
    dashboard.show()

    dashboard.resize(820, 600)
    application.processEvents()
    assert dashboard.metric_grid.getItemPosition(0)[:2] == (0, 0)
    assert dashboard.metric_grid.getItemPosition(2)[:2] == (1, 0)
    assert dashboard.chart_grid.getItemPosition(1)[:2] == (1, 0)

    dashboard.resize(1220, 800)
    application.processEvents()
    assert dashboard.metric_grid.getItemPosition(3)[:2] == (0, 3)
    assert dashboard.chart_grid.getItemPosition(1)[:2] == (0, 1)
    dashboard.close()


def test_shared_severity_and_table_components_are_accessible_and_read_only(
    application: QApplication,
) -> None:
    badge = SeverityBadge("HIGH", "HIGH")
    table = StyledTable(("SOURCE IP", "STATUS"))

    assert badge.accessibleName() == "HIGH severity"
    assert badge.property("severity") == "HIGH"
    assert not table.editTriggers()
    assert table.horizontalHeaderItem(0).text() == "SOURCE IP"

    with pytest.raises(ValueError):
        SeverityBadge("CRITICAL", "CRITICAL")
