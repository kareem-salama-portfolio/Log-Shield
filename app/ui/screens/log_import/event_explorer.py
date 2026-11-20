"""Log Import & Event Explorer screen and backend integration signals."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.log_import import (
    EventFilters,
    EventPage,
    EventRecord,
    ImportHistoryRecord,
    IPDetails,
    MalformedRecord,
)
from app.ui.screens.log_import.filters_panel import FilterPanel
from app.ui.screens.log_import.import_panel import ImportHistoryPanel, ImportPanel
from app.ui.screens.log_import.ip_details import IPDetailsPanel
from app.ui.screens.log_import.malformed_dialog import MalformedRecordsDialog
from app.ui.styles.tokens import Dimensions, Spacing, Typography
from app.ui.widgets.components import PageHeader, PanelCard, SecondaryButton, StatusBadge
from app.ui.widgets.styled_table import StyledTable
from app.utils.file_validation import LogFileValidationError, validate_log_file


PAGE_SIZE = 200


class EventExplorer(QWidget):
    """Second primary screen; UI emits queries and displays supplied pages."""

    import_requested = Signal(str)
    events_requested = Signal(object, int, int)
    ip_details_requested = Signal(str)
    malformed_records_requested = Signal(int)

    _COMPACT = "compact"
    _WIDE = "wide"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardContent")
        self._layout_mode: tuple[str, str] | None = None
        self._visible_events: list[EventRecord] = []
        self._history_records: list[ImportHistoryRecord] = []
        self._has_applied_filters = False
        self.current_filters: EventFilters = _empty_filters()
        self.current_page = 1
        self.page_size = PAGE_SIZE
        self.total_count: int | None = 0
        self._dialogs: list[MalformedRecordsDialog] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.XXL, Spacing.XL, Spacing.XXL, Spacing.XL)
        root.setSpacing(Spacing.LG)

        root.addWidget(
            PageHeader(
                "Log Import & Event Explorer",
                "Import authentication logs and investigate individual events.",
            )
        )

        self.top_grid = QGridLayout()
        self.top_grid.setContentsMargins(0, 0, 0, 0)
        self.top_grid.setHorizontalSpacing(Spacing.MD)
        self.top_grid.setVerticalSpacing(Spacing.MD)
        self.import_panel = ImportPanel()
        self.history_panel = ImportHistoryPanel()
        self.top_grid.addWidget(self.import_panel, 0, 0)
        self.top_grid.addWidget(self.history_panel, 0, 1)
        root.addLayout(self.top_grid)

        self.filter_panel = FilterPanel()
        root.addWidget(self.filter_panel)

        self.results_controls = self._make_results_controls()
        self.event_panel = PanelCard(
            "Authentication Events",
            "Paged results from the current query.",
            self.results_controls,
        )
        self.event_table = StyledTable(("TIMESTAMP", "SOURCE IP", "USERNAME", "OUTCOME", "LINE NO.") )
        self.event_table.setAccessibleName("Filtered authentication events")
        self.event_table.setToolTip("Select a row to request whole-IP context.")
        self.event_table.setMinimumHeight(200)
        self.event_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.event_table.itemSelectionChanged.connect(self._handle_event_selection)
        self.event_state_label = QLabel("No events imported yet. Import a log file to begin.")
        self.event_state_label.setObjectName("explorerEmptyState")
        self.event_state_label.setWordWrap(True)
        self.event_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.event_state_label.setMinimumHeight(150)
        self.event_panel.content_layout.addWidget(self.event_table)
        self.event_panel.content_layout.addWidget(self.event_state_label)

        self.ip_details_panel = IPDetailsPanel()
        self.results_grid = QGridLayout()
        self.results_grid.setContentsMargins(0, 0, 0, 0)
        self.results_grid.setHorizontalSpacing(Spacing.MD)
        self.results_grid.setVerticalSpacing(Spacing.MD)
        self.results_grid.addWidget(self.event_panel, 0, 0)
        self.results_grid.addWidget(self.ip_details_panel, 0, 1)
        self.results_grid.setColumnStretch(0, 2)
        self.results_grid.setColumnStretch(1, 1)
        root.addLayout(self.results_grid)
        root.addStretch(1)

        self.import_panel.file_picker_requested.connect(self.open_file_picker)
        self.import_panel.malformed_records_requested.connect(self.malformed_records_requested)
        self.history_panel.malformed_records_requested.connect(self.malformed_records_requested)
        self.filter_panel.filters_submitted.connect(self.request_events)
        self.filter_panel.filters_cleared.connect(self._request_unfiltered_events)
        self.previous_button.clicked.connect(self.request_previous_page)
        self.next_button.clicked.connect(self.request_next_page)

        self.set_import_history([])
        self.set_events_page(_empty_event_page())
        self._update_responsive_layout()

    def open_file_picker(self) -> None:
        """Open the native picker restricted to supported text log extensions."""
        selected, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import Log File",
            "",
            "Authentication logs (*.log *.txt)",
        )
        if selected:
            self.select_log_file(selected)

    def select_log_file(self, selected: str | Path) -> bool:
        """Validate local path metadata, then expose a pending service request."""
        try:
            path = validate_log_file(selected)
        except LogFileValidationError as error:
            self.import_panel.set_validation_error(str(error))
            return False

        self.import_panel.set_selected_file(path)
        self.import_requested.emit(str(path))
        return True

    def set_import_history(self, records: list[ImportHistoryRecord]) -> None:
        """Display one history page returned by a future service or demo adapter."""
        self._history_records = list(records)
        self.history_panel.set_records(self._history_records)

    def set_import_progress(self, percentage: int, status: str = "Import in progress…") -> None:
        """Apply a progress update delivered on the GUI thread by a worker."""
        self.import_panel.update_progress(percentage, status)

    def set_import_result(self, record: ImportHistoryRecord) -> None:
        """Display a confirmed service result and reflect it in recent history."""
        self.import_panel.set_import_result(record)
        self._history_records = [
            record,
            *(existing for existing in self._history_records if existing["import_id"] != record["import_id"]),
        ]
        self.history_panel.set_records(self._history_records)

    def set_import_failed(self, message: str) -> None:
        self.import_panel.set_import_failed(message)

    def set_events_loading(self) -> None:
        """Show an in-flight page request without blocking the Qt event loop."""
        self.event_table.hide()
        self.event_state_label.setObjectName("explorerEmptyState")
        self.event_state_label.setText("Loading events…")
        self.event_state_label.show()
        self.result_summary_label.setText("Loading results…")
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)

    def set_events_error(self, message: str) -> None:
        """Show an integration or service error without pretending there are no matches."""
        self.event_table.hide()
        self.event_state_label.setObjectName("explorerErrorState")
        self.event_state_label.setText(message)
        self.event_state_label.style().unpolish(self.event_state_label)
        self.event_state_label.style().polish(self.event_state_label)
        self.event_state_label.show()
        self.result_summary_label.setText("Results unavailable")
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.ip_details_panel.clear_selection()

    def set_events_page(self, page: EventPage) -> None:
        """Render a single backend-provided page of at most the requested size."""
        self.current_page = max(1, page["page"])
        self.page_size = max(1, min(PAGE_SIZE, page["page_size"]))
        self.total_count = page["total_count"]
        self._visible_events = list(page["items"][: self.page_size])
        self.event_table.clearContents()
        self.event_table.setRowCount(len(self._visible_events))
        self.ip_details_panel.clear_selection()

        for row, event in enumerate(self._visible_events):
            values = (
                _format_datetime(event["timestamp"]),
                event["source_ip"],
                event["username"],
                event["outcome"].upper(),
                str(event["line_no"]),
            )
            for column, value in enumerate(values):
                if column == 3:
                    tone = "error" if value == "FAILED" else "success" if value == "SUCCESS" else "neutral"
                    self.event_table.setCellWidget(row, column, StatusBadge(value, tone))
                    continue
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, event["id"])
                    item.setData(Qt.ItemDataRole.UserRole + 1, event["file_id"])
                elif column == 1:
                    item.setFont(QFont(Typography.MONOSPACE_FAMILY, Typography.SIZE_SM))
                if column == 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.event_table.setItem(row, column, item)

        self.event_table.resizeRowsToContents()
        if self._visible_events:
            self.event_state_label.hide()
            self.event_table.show()
        else:
            self.event_table.hide()
            if self.total_count == 0 and not self._has_applied_filters:
                self.event_state_label.setText("No events imported yet. Import a log file to begin.")
            else:
                self.event_state_label.setText("No events match the current filters.")
            self.event_state_label.show()
        self.event_state_label.setObjectName("explorerEmptyState")
        self.event_state_label.style().unpolish(self.event_state_label)
        self.event_state_label.style().polish(self.event_state_label)
        self._update_pagination()

    def set_ip_details(self, details: IPDetails | None) -> None:
        self.ip_details_panel.set_details(details)

    def set_ip_details_unavailable(self, source_ip: str) -> None:
        self.ip_details_panel.set_unavailable(source_ip)

    def show_malformed_records(
        self,
        records: list[MalformedRecord],
        total_count: int | None = None,
    ) -> MalformedRecordsDialog:
        """Open a retained dialog so long records remain accessible and scrollable."""
        dialog = MalformedRecordsDialog(records, total_count, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.finished.connect(lambda _result: self._forget_dialog(dialog))
        self._dialogs.append(dialog)
        dialog.open()
        return dialog

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt event name
        super().resizeEvent(event)
        self._update_responsive_layout()

    def request_events(self, filters: EventFilters) -> None:
        """Request the first page; no event rows are filtered in this widget."""
        self.current_filters = dict(filters)
        self._has_applied_filters = any(filters.values())
        self.current_page = 1
        self.ip_details_panel.clear_selection()
        self.set_events_loading()
        self.events_requested.emit(dict(filters), self.current_page, PAGE_SIZE)

    def request_previous_page(self) -> None:
        if self.previous_button.isEnabled() and self.current_page > 1:
            self._request_page(self.current_page - 1)

    def request_next_page(self) -> None:
        if self.next_button.isEnabled():
            self._request_page(self.current_page + 1)

    def _request_page(self, page: int) -> None:
        self.current_page = page
        self.set_events_loading()
        self.events_requested.emit(dict(self.current_filters), page, self.page_size)

    def _request_unfiltered_events(self) -> None:
        self.request_events(_empty_filters())

    def _make_results_controls(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)
        self.result_summary_label = QLabel("0 matching events")
        self.result_summary_label.setObjectName("resultsSummary")
        self.page_label = QLabel("Page 1")
        self.page_label.setObjectName("resultsSummary")
        self.previous_button = SecondaryButton("Previous")
        self.previous_button.setMinimumHeight(30)
        self.previous_button.setEnabled(False)
        self.next_button = SecondaryButton("Next")
        self.next_button.setMinimumHeight(30)
        self.next_button.setEnabled(False)
        layout.addWidget(self.result_summary_label)
        layout.addSpacing(Spacing.XS)
        layout.addWidget(self.page_label)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)
        return container

    def _update_pagination(self) -> None:
        total = self.total_count
        if total is None:
            self.result_summary_label.setText(
                f"{len(self._visible_events):,} events on this page · total unknown"
            )
            self.page_label.setText(f"Page {self.current_page}")
            self.next_button.setEnabled(len(self._visible_events) >= self.page_size)
        elif total == 0:
            self.result_summary_label.setText("0 matching events")
            self.page_label.setText("Page 0 of 0")
            self.next_button.setEnabled(False)
        else:
            first = (self.current_page - 1) * self.page_size + 1
            last = min(self.current_page * self.page_size, total)
            pages = max(1, (total + self.page_size - 1) // self.page_size)
            self.result_summary_label.setText(f"{first:,}–{last:,} of {total:,} events")
            self.page_label.setText(f"Page {self.current_page} of {pages}")
            self.next_button.setEnabled(self.current_page < pages)
        self.previous_button.setEnabled(self.current_page > 1)

    def _handle_event_selection(self) -> None:
        row = self.event_table.currentRow()
        if 0 <= row < len(self._visible_events):
            self.ip_details_requested.emit(self._visible_events[row]["source_ip"])
        else:
            self.ip_details_panel.clear_selection()

    def _update_responsive_layout(self) -> None:
        width = self.width()
        mode = (
            self._COMPACT if width < 880 else self._WIDE,
            self._COMPACT if width < 1120 else self._WIDE,
        )
        if mode == self._layout_mode:
            return
        self._layout_mode = mode
        self.event_table.setMaximumHeight(360 if mode[0] == self._COMPACT else 440)

        for widget in (self.import_panel, self.history_panel):
            self.top_grid.removeWidget(widget)
        if mode[0] == self._COMPACT:
            self.top_grid.addWidget(self.import_panel, 0, 0)
            self.top_grid.addWidget(self.history_panel, 1, 0)
            self.top_grid.setColumnStretch(0, 1)
            self.top_grid.setColumnStretch(1, 0)
        else:
            self.top_grid.addWidget(self.import_panel, 0, 0)
            self.top_grid.addWidget(self.history_panel, 0, 1)
            self.top_grid.setColumnStretch(0, 9)
            self.top_grid.setColumnStretch(1, 11)

        self.results_grid.removeWidget(self.event_panel)
        self.results_grid.removeWidget(self.ip_details_panel)
        if mode[1] == self._COMPACT:
            self.results_grid.addWidget(self.event_panel, 0, 0)
            self.results_grid.addWidget(self.ip_details_panel, 1, 0)
            self.results_grid.setColumnStretch(0, 1)
            self.results_grid.setColumnStretch(1, 0)
        else:
            self.results_grid.addWidget(self.event_panel, 0, 0)
            self.results_grid.addWidget(self.ip_details_panel, 0, 1)
            self.results_grid.setColumnStretch(0, 2)
            self.results_grid.setColumnStretch(1, 1)

    def _forget_dialog(self, dialog: MalformedRecordsDialog) -> None:
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)


def _empty_filters() -> EventFilters:
    return {
        "source_ip": None,
        "username": None,
        "outcome": None,
        "start_time": None,
        "end_time": None,
    }


def _empty_event_page() -> EventPage:
    return {"items": [], "page": 1, "page_size": PAGE_SIZE, "total_count": 0}


def _format_datetime(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except (AttributeError, ValueError):
        return value
