"""Scrollable dialog for parser-rejected source lines."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.log_import import MalformedRecord
from app.ui.styles.tokens import Spacing
from app.ui.widgets.styled_table import StyledTable


class MalformedRecordsDialog(QDialog):
    """Show line number, original text, and backend-supplied rejection reason."""

    def __init__(
        self,
        records: list[MalformedRecord],
        total_count: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Malformed Log Records")
        self.setMinimumSize(700, 420)
        self.resize(980, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        layout.setSpacing(Spacing.MD)

        resolved_count = len(records) if total_count is None else total_count
        self.total_count_label = QLabel(f"{resolved_count:,} malformed records")
        self.total_count_label.setObjectName("sectionTitle")
        layout.addWidget(self.total_count_label)

        self.empty_label = QLabel()
        self.empty_label.setObjectName("explorerEmptyState")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(120)
        if not records:
            self.empty_label.setText(
                "No malformed-record details were returned for this import."
                if resolved_count
                else "This import has no malformed records."
            )
        layout.addWidget(self.empty_label)

        self.records_table = StyledTable(("LINE", "RAW LOG TEXT", "REASON"))
        self.records_table.setAccessibleName("Malformed source log records")
        self.records_table.setWordWrap(True)
        self.records_table.setMinimumHeight(220)
        self.records_table.setVisible(bool(records))
        self.records_table.horizontalHeader().setMinimumSectionSize(100)
        self.records_table.setColumnWidth(0, 80)
        self.records_table.setColumnWidth(2, 160)
        self.records_table.horizontalHeader().setStretchLastSection(False)
        self.records_table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.records_table.setItem(row, 0, _table_item(str(record["line_no"]), Qt.AlignmentFlag.AlignCenter))
            raw_item = _table_item(record["raw_text"], Qt.AlignmentFlag.AlignLeft)
            raw_item.setToolTip(record["raw_text"])
            self.records_table.setItem(row, 1, raw_item)
            self.records_table.setItem(row, 2, _table_item(record["reason"], Qt.AlignmentFlag.AlignLeft))
            self.records_table.setRowHeight(row, 58)
        self.records_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.records_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.records_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.records_table.resizeRowsToContents()
        layout.addWidget(self.records_table, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.close_button = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.close_button.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        footer.addWidget(self.close_button)
        layout.addLayout(footer)
        self.empty_label.setVisible(not records)


def _table_item(text: str, alignment: Qt.AlignmentFlag) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
