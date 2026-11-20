"""Backend-provided, whole-IP context for the selected event."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.log_import import IPDetails
from app.ui.styles.tokens import Colors, Spacing, Typography
from app.ui.widgets.components import PanelCard


class IPActivityMiniChart(QWidget):
    """Small chart rendering activity buckets returned by the event service."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.figure = Figure(figsize=(3.0, 1.0), dpi=100, facecolor="none")
        self.figure.patch.set_alpha(0)
        self.axes = self.figure.add_subplot(111)
        self.axes.patch.set_alpha(0)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.canvas.setFixedHeight(84)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.canvas.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.canvas.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.canvas.setObjectName("chartCanvas")
        layout.addWidget(self.canvas)
        self.set_points([])

    def set_points(self, points: list[dict[str, str | int]]) -> None:
        self.axes.clear()
        self.axes.set_facecolor("none")
        self.axes.tick_params(axis="both", colors=Colors.TEXT_MUTED, labelsize=7, length=0, pad=3)
        for spine in self.axes.spines.values():
            spine.set_visible(False)

        if not points:
            self.axes.set_xticks([])
            self.axes.set_yticks([])
            self.axes.text(
                0.5,
                0.5,
                "No activity timeline supplied",
                color=Colors.TEXT_MUTED,
                fontsize=Typography.SIZE_XS,
                ha="center",
                va="center",
                transform=self.axes.transAxes,
            )
        else:
            x_values = list(range(len(points)))
            values = [int(point["event_count"]) for point in points]
            self.axes.fill_between(x_values, values, 0, color=Colors.ACCENT, alpha=0.13)
            self.axes.plot(x_values, values, color=Colors.ACCENT, linewidth=1.8, marker="o", markersize=2.5)
            labels = [_time_label(str(point["timestamp"])) for point in points]
            self.axes.set_xticks([0, len(points) - 1], [labels[0], labels[-1]])
            self.axes.set_yticks([])
            self.axes.grid(axis="y", color=Colors.BORDER, linewidth=0.6)
            self.axes.margins(x=0.02, y=0.22)
        self.figure.subplots_adjust(left=0.03, right=0.98, top=0.93, bottom=0.32)
        self.canvas.draw_idle()


class IPDetailsPanel(PanelCard):
    """Renders service-provided IP statistics without deriving them from rows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "IP Details",
            "Backend-calculated context for the selected source.",
            parent=parent,
        )
        self.empty_label = QLabel("Select an event to view source IP context.")
        self.empty_label.setObjectName("explorerEmptyState")
        self.empty_label.setWordWrap(True)
        self.empty_label.setMinimumHeight(120)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.empty_label)

        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(Spacing.SM)
        self.address_label = QLabel()
        self.address_label.setObjectName("detailsAddress")
        self.address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_layout.addWidget(self.address_label)

        metrics = QGridLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setHorizontalSpacing(Spacing.XS)
        metrics.setVerticalSpacing(Spacing.XS)
        self.metric_values: dict[str, QLabel] = {}
        for index, key in enumerate(("total_events", "failed_logins", "successful_logins")):
            title = {
                "total_events": "TOTAL EVENTS",
                "failed_logins": "FAILED",
                "successful_logins": "SUCCESS",
            }[key]
            card, value_label = _metric_card(title)
            self.metric_values[key] = value_label
            metrics.addWidget(card, 0, index)
            metrics.setColumnStretch(index, 1)
        details_layout.addLayout(metrics)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(Spacing.MD)
        self.first_seen_label = QLabel()
        self.last_seen_label = QLabel()
        for label in (self.first_seen_label, self.last_seen_label):
            label.setObjectName("fieldHint")
            label.setWordWrap(True)
        time_row.addWidget(self.first_seen_label, 1)
        time_row.addWidget(self.last_seen_label, 1)
        details_layout.addLayout(time_row)

        timeline_title = QLabel("ACTIVITY TIMELINE")
        timeline_title.setObjectName("fieldLabel")
        details_layout.addWidget(timeline_title)
        self.activity_chart = IPActivityMiniChart()
        details_layout.addWidget(self.activity_chart)

        benign_note = QLabel("Observed activity is context; an IP address alone does not establish malicious intent.")
        benign_note.setObjectName("fieldHint")
        benign_note.setWordWrap(True)
        details_layout.addWidget(benign_note)
        self.content_layout.addWidget(self.details_widget)
        self.details_widget.hide()

    def clear_selection(self) -> None:
        """Show the neutral state when the event table has no selected row."""
        self.address_label.clear()
        self.empty_label.setText("Select an event to view source IP context.")
        self.empty_label.show()
        self.details_widget.hide()

    def set_unavailable(self, source_ip: str) -> None:
        """Show the selected address without making up missing statistics."""
        self.details_widget.hide()
        self.empty_label.setText(
            f"IP details for {source_ip} are unavailable until the Event Service is connected."
        )
        self.empty_label.show()

    def set_details(self, details: IPDetails | None) -> None:
        """Display a whole-IP summary returned by a service or demo adapter."""
        if details is None:
            self.clear_selection()
            self.empty_label.setText("No IP detail summary was returned for this address.")
            return
        self.address_label.setText(details["source_ip"])
        self.metric_values["total_events"].setText(f"{details['total_events']:,}")
        self.metric_values["failed_logins"].setText(f"{details['failed_logins']:,}")
        self.metric_values["successful_logins"].setText(f"{details['successful_logins']:,}")
        self.first_seen_label.setText(f"First seen\n{details['first_seen']}")
        self.last_seen_label.setText(f"Last seen\n{details['last_seen']}")
        self.activity_chart.set_points(details["activity"])
        self.empty_label.hide()
        self.details_widget.show()


def _metric_card(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("detailMetricCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(Spacing.XS, Spacing.XS, Spacing.XS, Spacing.XS)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setObjectName("detailMetricLabel")
    value = QLabel("—")
    value.setObjectName("detailMetricValue")
    layout.addWidget(label)
    layout.addWidget(value)
    return card, value


def _time_label(timestamp: str) -> str:
    if "T" in timestamp:
        return timestamp.rsplit("T", 1)[-1][:5]
    return timestamp[-5:]
