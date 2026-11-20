"""Security Overview Dashboard presentation and navigation integration points."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.dashboard import DashboardData, IncidentSummary
from app.ui.screens.dashboard.charts import FailedLoginsChart, TopSourceIPsChart
from app.ui.styles.tokens import Colors, Dimensions, Spacing, Typography
from app.ui.widgets.components import (
    EmptyStateBanner,
    MetricCard,
    PanelCard,
    SecondaryButton,
    SeverityBadge,
)
from app.ui.widgets.icons import create_icon
from app.ui.widgets.styled_table import StyledTable


class Dashboard(QWidget):
    """Data-driven overview screen, independent of database access."""

    navigation_requested = Signal(str)
    incident_open_requested = Signal(object)

    _LAYOUT_WIDE = "wide"
    _LAYOUT_COMPACT = "compact"

    def __init__(self, data: DashboardData, demo_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data = data
        self.demo_mode = demo_mode
        self._layout_mode: tuple[str, str] | None = None
        self.setObjectName("dashboardContent")

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        root.setSpacing(Spacing.LG)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(Spacing.LG)
        header_copy = QVBoxLayout()
        header_copy.setContentsMargins(0, 0, 0, 0)
        header_copy.setSpacing(Spacing.XXS)

        eyebrow = QLabel("SECURITY OPERATIONS  /  OVERVIEW")
        eyebrow.setObjectName("eyebrow")
        self.title_label = QLabel("Security Overview")
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel("Authentication activity and the latest security signals in one view.")
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        header_copy.addWidget(eyebrow)
        header_copy.addWidget(self.title_label)
        header_copy.addWidget(self.subtitle_label)
        self.header_copy = header_copy
        self.header_row = header_row
        header_row.addLayout(header_copy, 1)

        self.mode_indicator = QLabel("DEMONSTRATION DATA" if demo_mode else "NO DATA IMPORTED")
        self.mode_indicator.setObjectName("modeIndicator")
        self.mode_indicator.setProperty("demo", "true" if demo_mode else "false")
        self.mode_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_indicator.setMinimumHeight(28)
        self.mode_indicator.setContentsMargins(Spacing.SM, 0, Spacing.SM, 0)
        self.mode_indicator.setAccessibleName(
            "Synthetic demonstration data" if demo_mode else "No imported data"
        )
        self.mode_indicator.setMinimumWidth(146)
        header_row.addWidget(self.mode_indicator, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header_row)

        self.empty_state = EmptyStateBanner()
        self.empty_state.action_button.clicked.connect(
            lambda: self.navigation_requested.emit("log_import")
        )
        self.empty_state.setVisible(data["total_events"] == 0)
        root.addWidget(self.empty_state)

        self.metric_grid = QGridLayout()
        self.metric_grid.setContentsMargins(0, 0, 0, 0)
        self.metric_grid.setHorizontalSpacing(Spacing.MD)
        self.metric_grid.setVerticalSpacing(Spacing.MD)
        self.metric_grid.setColumnStretch(0, 1)
        self.metric_grid.setColumnStretch(1, 1)
        self.metric_grid.setColumnStretch(2, 1)
        self.metric_grid.setColumnStretch(3, 1)

        self.incident_breakdown = QWidget()
        breakdown_layout = QHBoxLayout(self.incident_breakdown)
        breakdown_layout.setContentsMargins(0, 0, 0, 0)
        breakdown_layout.setSpacing(Spacing.XS)
        self.high_badge = SeverityBadge(f"HIGH  {data['high_incidents']}", "HIGH")
        self.medium_badge = SeverityBadge(f"MEDIUM  {data['medium_incidents']}", "MEDIUM")
        breakdown_layout.addWidget(self.high_badge)
        breakdown_layout.addWidget(self.medium_badge)
        breakdown_layout.addStretch(1)

        self.metric_cards = [
            MetricCard("Total Events", f"{data['total_events']:,}", "activity", "Events in this dataset"),
            MetricCard("Failed Logins", f"{data['failed_logins']:,}", "key-round", "Recorded authentication failures"),
            MetricCard("Unique IP Addresses", f"{data['unique_ips']:,}", "globe", "Distinct observed sources"),
            MetricCard(
                "Security Incidents",
                f"{data['medium_incidents'] + data['high_incidents']:,}",
                "shield-alert",
                self.incident_breakdown,
                icon_color=Colors.ROSE_PRIMARY,
            ),
        ]
        for card in self.metric_cards:
            card.setMinimumHeight(120)
            self.metric_grid.addWidget(card, 0, 0)
        root.addLayout(self.metric_grid)

        self.chart_grid = QGridLayout()
        self.chart_grid.setContentsMargins(0, 0, 0, 0)
        self.chart_grid.setHorizontalSpacing(Spacing.MD)
        self.chart_grid.setVerticalSpacing(Spacing.MD)
        self.failed_chart = FailedLoginsChart(data)
        self.top_ips_chart = TopSourceIPsChart(data)
        self.failed_panel = PanelCard("Failed Logins Over Time", "Hourly failure volume")
        self.failed_panel.content_layout.addWidget(self.failed_chart)
        self.top_ips_panel = PanelCard("Top Source IPs", "Leading sources by failed logins")
        self.top_ips_panel.content_layout.addWidget(self.top_ips_chart)
        self.chart_grid.addWidget(self.failed_panel, 0, 0)
        self.chart_grid.addWidget(self.top_ips_panel, 0, 1)
        self.chart_grid.setColumnStretch(0, 1)
        self.chart_grid.setColumnStretch(1, 1)
        root.addLayout(self.chart_grid)

        incidents_action = SecondaryButton("View all incidents", "arrow-right")
        incidents_action.clicked.connect(lambda: self.navigation_requested.emit("incidents_reports"))
        self.incidents_panel = PanelCard(
            "Latest Security Incidents",
            "Recent grouped authentication activity",
            incidents_action,
        )
        self.incident_table = StyledTable(
            ("SOURCE IP", "START TIME", "END TIME", "FAILURES", "SEVERITY", "STATUS")
        )
        self.incident_table.setAccessibleName("Latest security incidents")
        self.incident_table.setToolTip("Select a row to open its future incident detail view.")
        self.incident_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.incident_table.setMinimumHeight(0)
        self.incident_table.cellClicked.connect(self._open_incident_at_row)
        self.incident_empty_label = QLabel("No incidents to display")
        self.incident_empty_label.setObjectName("tableEmptyMessage")
        self.incident_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.incident_empty_label.setMinimumHeight(82)
        self.incidents_panel.content_layout.addWidget(self.incident_table)
        self.incidents_panel.content_layout.addWidget(self.incident_empty_label)
        self.root_layout = root
        self.root_layout.addWidget(self.incidents_panel)
        self._populate_incidents(data["latest_incidents"])
        root.addStretch(1)
        self._update_responsive_layout()

    def update_data(self, data: DashboardData, demo_mode: bool = False) -> None:
        """Replace the plain dashboard snapshot without reaching into storage."""
        self.data = data
        self.demo_mode = demo_mode
        has_events = data["total_events"] > 0
        self.empty_state.setVisible(not has_events)
        self.mode_indicator.setText("DEMONSTRATION DATA" if demo_mode else ("DATA LOADED" if has_events else "NO DATA IMPORTED"))
        self.mode_indicator.setProperty("demo", "true" if demo_mode else "false")
        self.mode_indicator.style().unpolish(self.mode_indicator)
        self.mode_indicator.style().polish(self.mode_indicator)
        for card, value in zip(
            self.metric_cards[:3],
            (data["total_events"], data["failed_logins"], data["unique_ips"]),
        ):
            card.set_value(f"{value:,}")
        self.metric_cards[3].set_value(f"{data['medium_incidents'] + data['high_incidents']:,}")
        self.high_badge.setText(f"HIGH  {data['high_incidents']}")
        self.medium_badge.setText(f"MEDIUM  {data['medium_incidents']}")
        self.failed_chart.update_data(data)
        self.top_ips_chart.update_data(data)
        self._populate_incidents(data["latest_incidents"])

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt event name
        super().resizeEvent(event)
        self._update_responsive_layout()

    def _update_responsive_layout(self) -> None:
        width = self.width()
        mode = (
            self._LAYOUT_COMPACT if width < 1000 else self._LAYOUT_WIDE,
            self._LAYOUT_COMPACT if width < 1120 else self._LAYOUT_WIDE,
        )
        if mode == self._layout_mode:
            return
        self._layout_mode = mode

        if mode[0] == self._LAYOUT_COMPACT:
            self.header_row.removeWidget(self.mode_indicator)
            self.header_copy.addWidget(self.mode_indicator, 0, Qt.AlignmentFlag.AlignLeft)
        else:
            self.header_copy.removeWidget(self.mode_indicator)
            self.header_row.addWidget(self.mode_indicator, 0, Qt.AlignmentFlag.AlignTop)

        metric_columns = 2 if mode[0] == self._LAYOUT_COMPACT else 4
        for column in range(4):
            self.metric_grid.setColumnStretch(column, 1 if column < metric_columns else 0)
        for card in self.metric_cards:
            self.metric_grid.removeWidget(card)
        for index, card in enumerate(self.metric_cards):
            self.metric_grid.addWidget(card, index // metric_columns, index % metric_columns)

        self.chart_grid.removeWidget(self.failed_panel)
        self.chart_grid.removeWidget(self.top_ips_panel)
        if mode[1] == self._LAYOUT_COMPACT:
            self.chart_grid.addWidget(self.failed_panel, 0, 0)
            self.chart_grid.addWidget(self.top_ips_panel, 1, 0)
            self.chart_grid.setColumnStretch(0, 1)
            self.chart_grid.setColumnStretch(1, 0)
        else:
            self.chart_grid.addWidget(self.failed_panel, 0, 0)
            self.chart_grid.addWidget(self.top_ips_panel, 0, 1)
            self.chart_grid.setColumnStretch(0, 1)
            self.chart_grid.setColumnStretch(1, 1)

    def _populate_incidents(self, incidents: list[IncidentSummary]) -> None:
        self.incident_table.setRowCount(len(incidents))
        self.incident_empty_label.setVisible(not incidents)
        self.incident_table.setVisible(bool(incidents))
        for row, incident in enumerate(incidents):
            self.incident_table.setRowHeight(row, Dimensions.TABLE_ROW_HEIGHT)
            values = (
                incident["source_ip"],
                _format_incident_time(incident["start_time"]),
                _format_incident_time(incident["end_time"]),
                f"{incident['failure_count']:,}",
                incident["severity"].upper(),
                incident["status"],
            )
            for column, value in enumerate(values):
                if column == 4:
                    display_severity = value.strip().upper() or "UNKNOWN"
                    badge_style = (
                        display_severity
                        if display_severity in {"HIGH", "MEDIUM", "LOW"}
                        else "UNKNOWN"
                    )
                    badge = SeverityBadge(display_severity, badge_style)
                    badge.setAccessibleName(f"{display_severity} severity")
                    self.incident_table.setCellWidget(row, column, badge)
                    continue
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column in (3,):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                elif column == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_SM))
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.incident_table.setItem(row, column, item)
        self.incident_table.resizeRowsToContents()
        self.incident_table.setVisible(bool(incidents))

    def _open_incident_at_row(self, row: int, _column: int) -> None:
        if 0 <= row < len(self.data["latest_incidents"]):
            self.incident_open_requested.emit(dict(self.data["latest_incidents"][row]))


def _format_incident_time(value: str) -> str:
    """Format ISO-like timestamps for compact table display."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return value
    return parsed.strftime("%Y-%m-%d  %H:%M")
