"""Matplotlib charts used by the Security Overview Dashboard."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.models.dashboard import DashboardData
from app.ui.styles.tokens import Colors, Typography


class _DashboardChart(QWidget):
    """Common dark chart canvas with compact dashboard sizing."""

    empty_message = "No chart data available"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.figure = Figure(figsize=(5.4, 1.8), dpi=100, facecolor="none")
        self.figure.patch.set_alpha(0)
        self.axes = self.figure.add_subplot(111)
        self.axes.patch.set_alpha(0)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setObjectName("chartCanvas")
        self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.canvas.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.canvas.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.canvas.setMinimumHeight(155)
        layout.addWidget(self.canvas)

    def _style_axes(self) -> None:
        self.axes.set_facecolor("none")
        self.axes.tick_params(axis="both", colors=Colors.TEXT_MUTED, labelsize=8, length=0, pad=6)
        self.axes.xaxis.label.set_color(Colors.TEXT_SECONDARY)
        self.axes.yaxis.label.set_color(Colors.TEXT_SECONDARY)
        self.axes.xaxis.label.set_size(Typography.SIZE_XS)
        self.axes.yaxis.label.set_size(Typography.SIZE_XS)
        for spine in self.axes.spines.values():
            spine.set_color(Colors.BORDER)
            spine.set_linewidth(0.7)

    def _show_empty(self, message: str | None = None) -> None:
        self.axes.clear()
        self._style_axes()
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        for spine in self.axes.spines.values():
            spine.set_visible(False)
        self.axes.text(
            0.5,
            0.5,
            message or self.empty_message,
            color=Colors.TEXT_MUTED,
            fontsize=Typography.SIZE_MD,
            ha="center",
            va="center",
            transform=self.axes.transAxes,
        )
        self.canvas.draw_idle()


class FailedLoginsChart(_DashboardChart):
    """Line chart of failed logins grouped by hour."""

    empty_message = "No hourly failure data yet"

    def __init__(self, data: DashboardData, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.update_data(data)

    def update_data(self, data: DashboardData) -> None:
        points = data["failed_per_hour"]
        if not points:
            self._show_empty()
            return

        self.axes.clear()
        self._style_axes()
        positions = list(range(len(points)))
        values = [point["failure_count"] for point in points]
        labels = [point["hour"] for point in points]

        self.axes.plot(
            positions,
            values,
            color=Colors.ROSE_PRIMARY,
            linewidth=2.1,
            marker="o",
            markersize=4,
            markerfacecolor=Colors.SURFACE,
            markeredgecolor=Colors.ROSE_LIGHT,
            markeredgewidth=1.5,
            zorder=3,
        )
        self.axes.fill_between(positions, values, 0, color=Colors.ROSE_SOFT, alpha=0.17, zorder=2)
        tick_step = max(1, (len(labels) + 5) // 6)
        tick_positions = positions[::tick_step]
        if positions[-1] not in tick_positions:
            tick_positions.append(positions[-1])
        self.axes.set_xticks(tick_positions, [labels[position] for position in tick_positions])
        self.axes.set_ylabel("Failed logins", labelpad=8)
        self.axes.set_xlabel("Hour")
        self.axes.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
        self.axes.yaxis.grid(True, color=Colors.BORDER, linewidth=0.7, alpha=0.85)
        self.axes.xaxis.grid(False)
        self.axes.set_axisbelow(True)
        self.axes.margins(x=0.04, y=0.16)
        self.figure.subplots_adjust(left=0.12, right=0.98, top=0.98, bottom=0.25)
        self.canvas.draw_idle()


class TopSourceIPsChart(_DashboardChart):
    """Horizontal ranking of source IP addresses by failure count."""

    empty_message = "No source IP rankings available"

    def __init__(self, data: DashboardData, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.update_data(data)

    def update_data(self, data: DashboardData) -> None:
        points = sorted(data["top_ips"], key=lambda point: point["failure_count"], reverse=True)[:7]
        if not points:
            self._show_empty()
            return

        self.axes.clear()
        self._style_axes()
        labels = [point["source_ip"] for point in reversed(points)]
        values = [point["failure_count"] for point in reversed(points)]
        colors = list(Colors.CHART_SERIES[:len(points)])
        bars = self.axes.barh(labels, values, color=colors, height=0.54, zorder=3)
        self.axes.set_xlabel("Failed logins")
        self.axes.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
        self.axes.xaxis.grid(True, color=Colors.BORDER, linewidth=0.7, alpha=0.85)
        self.axes.yaxis.grid(False)
        self.axes.set_axisbelow(True)
        self.axes.set_xlim(0, max(values) * 1.25 if values else 1)
        self.axes.margins(y=0.16)
        for bar, value in zip(bars, values):
            self.axes.text(
                value + max(values) * 0.025,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,}",
                va="center",
                ha="left",
                color=Colors.TEXT_SECONDARY,
                fontsize=Typography.SIZE_XS,
            )
        self.figure.subplots_adjust(left=0.33, right=0.96, top=0.98, bottom=0.25)
        self.canvas.draw_idle()
