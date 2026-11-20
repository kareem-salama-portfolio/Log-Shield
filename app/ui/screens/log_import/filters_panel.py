"""Combined event filters and date-range validation."""

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.log_import import EventFilters
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PanelCard, PrimaryButton, SecondaryButton


class FilterPanel(PanelCard):
    """Build a backend-ready AND filter request without filtering UI rows."""

    filters_submitted = Signal(object)
    filters_cleared = Signal()

    _COMPACT = "compact"
    _MEDIUM = "medium"
    _WIDE = "wide"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Event Filters", "Combine fields to narrow the server-side event query.", parent=parent)
        self._layout_mode: str | None = None
        self.has_applied_filters = False

        self.filter_grid = QGridLayout()
        self.filter_grid.setContentsMargins(0, 0, 0, 0)
        self.filter_grid.setHorizontalSpacing(Spacing.MD)
        self.filter_grid.setVerticalSpacing(Spacing.SM)
        self.content_layout.addLayout(self.filter_grid)

        self.source_ip_input = self._line_edit("Filter by source address")
        self.username_input = self._line_edit("Filter by username")
        self.outcome_selector = QComboBox()
        self.outcome_selector.addItems(("All outcomes", "FAILED", "SUCCESS"))
        self.start_enabled = QCheckBox("Set")
        self.start_datetime = self._date_time_edit()
        self.start_datetime.setEnabled(False)
        self.start_enabled.toggled.connect(self.start_datetime.setEnabled)
        self.end_enabled = QCheckBox("Set")
        self.end_datetime = self._date_time_edit()
        self.end_datetime.setEnabled(False)
        self.end_enabled.toggled.connect(self.end_datetime.setEnabled)

        self.field_widgets = [
            self._field("SOURCE IP", self.source_ip_input),
            self._field("USERNAME", self.username_input),
            self._field("OUTCOME", self.outcome_selector),
            self._datetime_field("START DATE / TIME", self.start_enabled, self.start_datetime),
            self._datetime_field("END DATE / TIME", self.end_enabled, self.end_datetime),
        ]
        self._reflow_fields(3)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(Spacing.SM)
        footer.addStretch(1)
        self.validation_message = QLabel("")
        self.validation_message.setObjectName("operationStatus")
        self.validation_message.setProperty("tone", "error")
        self.validation_message.setWordWrap(True)
        footer.addWidget(self.validation_message, 1)
        self.clear_button = SecondaryButton("Clear Filters")
        self.apply_button = PrimaryButton("Apply Filters", "activity")
        self.clear_button.clicked.connect(self.clear_filters)
        self.apply_button.clicked.connect(self.apply_filters)
        footer.addWidget(self.clear_button)
        footer.addWidget(self.apply_button)
        self.content_layout.addLayout(footer)

    @staticmethod
    def _line_edit(placeholder: str) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setClearButtonEnabled(True)
        return field

    @staticmethod
    def _date_time_edit() -> QDateTimeEdit:
        field = QDateTimeEdit(QDateTime.currentDateTime())
        field.setDisplayFormat("yyyy-MM-dd HH:mm")
        field.setCalendarPopup(True)
        field.setMinimumWidth(170)
        return field

    @staticmethod
    def _field(label: str, control: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)
        heading = QLabel(label)
        heading.setObjectName("fieldLabel")
        layout.addWidget(heading)
        layout.addWidget(control)
        return container

    @classmethod
    def _datetime_field(
        cls,
        label: str,
        enabled: QCheckBox,
        control: QDateTimeEdit,
    ) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(Spacing.XS)
        row_layout.addWidget(enabled)
        row_layout.addWidget(control, 1)
        return cls._field(label, row)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt event name
        super().resizeEvent(event)
        available = self.width()
        mode = self._COMPACT if available < 520 else self._MEDIUM if available < 1000 else self._WIDE
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        columns = {self._COMPACT: 1, self._MEDIUM: 2, self._WIDE: 5}[mode]
        self._reflow_fields(columns)

    def _reflow_fields(self, columns: int) -> None:
        while self.filter_grid.count():
            item = self.filter_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(None)
        for index, widget in enumerate(self.field_widgets):
            self.filter_grid.addWidget(widget, index // columns, index % columns)
        for column in range(5):
            self.filter_grid.setColumnStretch(column, 1 if column < columns else 0)

    def build_filters(self) -> EventFilters:
        """Return normalized optional values for the event service request."""
        outcome_index = self.outcome_selector.currentIndex()
        return {
            "source_ip": self.source_ip_input.text().strip() or None,
            "username": self.username_input.text().strip() or None,
            "outcome": None if outcome_index == 0 else self.outcome_selector.currentText(),
            "start_time": self.start_datetime.dateTime().toString(Qt.DateFormat.ISODate)
            if self.start_enabled.isChecked()
            else None,
            "end_time": self.end_datetime.dateTime().toString(Qt.DateFormat.ISODate)
            if self.end_enabled.isChecked()
            else None,
        }

    def apply_filters(self) -> bool:
        """Validate and emit the service query; return false on invalid ranges."""
        if self.start_enabled.isChecked() and self.end_enabled.isChecked():
            start = self.start_datetime.dateTime().toPython()
            end = self.end_datetime.dateTime().toPython()
            if start > end:
                self.validation_message.setText("Start date/time must be earlier than or equal to the end.")
                self.validation_message.show()
                return False

        self.validation_message.clear()
        self.validation_message.hide()
        self.has_applied_filters = any(self.build_filters().values())
        self.filters_submitted.emit(self.build_filters())
        return True

    def clear_filters(self) -> None:
        """Reset controls and request the unfiltered event page."""
        self.source_ip_input.clear()
        self.username_input.clear()
        self.outcome_selector.setCurrentIndex(0)
        self.start_enabled.setChecked(False)
        self.end_enabled.setChecked(False)
        self.validation_message.clear()
        self.validation_message.hide()
        self.has_applied_filters = False
        self.filters_cleared.emit()
