"""Shared burgundy-and-rose Qt theme for the complete LogShield interface."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.ui.styles.tokens import (
    BUTTON_STYLES,
    CARD_STYLES,
    Colors,
    Dimensions,
    GLASS_STYLES,
    INPUT_STYLES,
    Radius,
    TABLE_STYLES,
    Typography,
)


def _stylesheet() -> str:
    """Build all shared widget styling from the LogShield design tokens."""
    primary = BUTTON_STYLES["primary"]
    secondary = BUTTON_STYLES["secondary"]
    return f"""
        * {{
            font-family: '{Typography.FAMILY}';
            color: {Colors.TEXT_PRIMARY};
        }}
        QMainWindow {{ background-color: {Colors.BACKGROUND}; }}
        QWidget#appRoot {{
            background: qradialgradient(
                cx: 0.10, cy: 0.08, radius: 1.18, fx: 0.10, fy: 0.08,
                stop: 0 {Colors.BACKGROUND_ELEVATED},
                stop: 0.48 {Colors.BACKGROUND_SECONDARY},
                stop: 1 {Colors.BACKGROUND}
            );
        }}
        QStackedWidget, QScrollArea, QScrollArea::viewport,
        QWidget#dashboardContent {{ background: transparent; border: none; }}

        QFrame#sidebar {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {GLASS_STYLES['sidebar_start']},
                stop: 1 {GLASS_STYLES['sidebar_end']}
            );
            border: 1px solid {GLASS_STYLES['sidebar_border']};
            border-radius: 18px;
        }}
        QLabel#brandName {{
            color: {Colors.TEXT_PRIMARY};
            font-size: 19px;
            font-weight: {Typography.WEIGHT_BOLD};
            letter-spacing: 0.4px;
        }}
        QLabel#brandSubtitle, QLabel#sidebarFooter, QLabel#eyebrow {{
            color: {Colors.TEXT_MUTED};
            font-size: {Typography.SIZE_XS}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
            letter-spacing: 0.8px;
        }}
        QLabel#brandSubtitle {{ font-size: 9px; letter-spacing: 0.35px; }}
        QLabel#sidebarSection {{
            color: {Colors.TEXT_MUTED};
            font-size: {Typography.SIZE_XS}px;
            font-weight: {Typography.WEIGHT_BOLD};
            letter-spacing: 1.1px;
        }}
        QLabel#modeIndicator {{
            color: {Colors.TEXT_SECONDARY};
            background-color: {Colors.SURFACE_RAISED};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SMALL}px;
            font-size: {Typography.SIZE_XS}px;
            font-weight: {Typography.WEIGHT_BOLD};
            letter-spacing: 0.4px;
        }}
        QLabel#modeIndicator[demo="true"] {{
            color: {Colors.ROSE_LIGHT};
            background-color: {Colors.ACCENT_TINT};
            border-color: {Colors.ROSE_SOFT};
        }}
        QLabel#modeIndicator[demo="false"] {{
            color: {Colors.TEXT_SECONDARY};
            background-color: {Colors.SURFACE_RAISED};
            border-color: {Colors.BORDER};
        }}

        QLabel#pageTitle {{
            color: {Colors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_TITLE}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#pageSubtitle {{
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_MD}px;
        }}
        QLabel#sectionTitle {{
            color: {Colors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_LG}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#sectionDescription {{
            color: {Colors.TEXT_MUTED};
            font-size: {Typography.SIZE_SM}px;
        }}
        QLabel#metricLabel {{
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_SM}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
        }}
        QLabel#metricValue {{
            color: {Colors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_METRIC}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#metricDetail {{ color: {Colors.TEXT_MUTED}; font-size: {Typography.SIZE_XS}px; }}
        QLabel#emptyStateTitle {{
            color: {Colors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#tableEmptyMessage {{
            color: {Colors.TEXT_MUTED};
            font-size: {Typography.SIZE_MD}px;
            border-top: 1px solid {Colors.DIVIDER};
        }}
        QLabel#fieldLabel {{
            color: {Colors.TEXT_SECONDARY};
            font-size: {Typography.SIZE_SM}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#fieldHint, QLabel#detailMetricLabel {{
            color: {Colors.TEXT_MUTED};
            font-size: {Typography.SIZE_XS}px;
        }}
        QLabel#operationStatus {{ color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px; }}
        QLabel#operationStatus[tone="success"] {{ color: {Colors.SUCCESS}; }}
        QLabel#operationStatus[tone="warning"] {{ color: {Colors.WARNING}; }}
        QLabel#operationStatus[tone="error"] {{ color: {Colors.ERROR}; }}
        QLabel#operationStatus[tone="info"] {{ color: {Colors.ROSE_LIGHT}; }}
        QLabel#explorerEmptyState {{ color: {Colors.TEXT_MUTED}; font-size: {Typography.SIZE_MD}px; }}
        QLabel#explorerErrorState {{
            color: {Colors.ERROR};
            font-size: {Typography.SIZE_MD}px;
            background-color: {Colors.ERROR_TINT};
            border: 1px solid {Colors.ERROR};
            border-radius: {Radius.MEDIUM}px;
            padding: 12px;
        }}
        QLabel#resultsSummary {{ color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px; }}
        QLabel#detailsAddress {{
            color: {Colors.TEXT_PRIMARY};
            font-family: '{Typography.MONOSPACE_FAMILY}';
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QLabel#detailMetricValue {{
            color: {Colors.TEXT_PRIMARY};
            font-size: {Typography.SIZE_LG}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}

        QFrame#panelCard, QFrame#metricCard, QFrame#emptyStateBanner {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {GLASS_STYLES['card_start']},
                stop: 1 {GLASS_STYLES['card_end']}
            );
            border: 1px solid {GLASS_STYLES['card_border']};
            border-radius: {CARD_STYLES['radius']}px;
        }}
        QFrame#panelCard {{
            border-top-color: {GLASS_STYLES['card_highlight']};
        }}
        QFrame#metricCard {{ border-radius: 13px; }}
        QFrame#metricIconTile, QFrame#brandIconTile {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 {GLASS_STYLES['icon_start']},
                stop: 1 {GLASS_STYLES['icon_end']}
            );
            border: 1px solid {GLASS_STYLES['icon_border']};
            border-radius: 10px;
        }}
        QFrame#emptyStateBanner {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {GLASS_STYLES['empty_start']},
                stop: 1 {GLASS_STYLES['empty_end']}
            );
            border-color: {GLASS_STYLES['empty_border']};
        }}
        QFrame#detailMetricCard {{
            background-color: {GLASS_STYLES['detail_background']};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.MEDIUM}px;
        }}
        QFrame#sidebarDivider {{
            background-color: {GLASS_STYLES['divider']};
            border: none;
            max-height: 1px;
        }}
        QFrame#statusDot {{ background-color: {Colors.SUCCESS}; border: none; border-radius: 3px; }}
        QWidget#chartCanvas {{ background-color: transparent; border: none; }}

        QPushButton {{
            background-color: {secondary['background']};
            color: {secondary['foreground']};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.MEDIUM}px;
            padding: 0 13px;
            min-height: {Dimensions.BUTTON_HEIGHT}px;
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QPushButton:hover {{
            background-color: {secondary['hover']};
            border-color: {Colors.BORDER_HIGHLIGHT};
        }}
        QPushButton:pressed {{ background-color: {secondary['pressed']}; }}
        QPushButton:focus {{ border: 1px solid {Colors.ROSE_LIGHT}; }}
        QPushButton:disabled {{
            color: {Colors.TEXT_MUTED};
            background-color: {Colors.BACKGROUND_ELEVATED};
            border-color: {Colors.DIVIDER};
        }}
        QPushButton#primaryButton {{
            background-color: {primary['background']};
            color: {primary['foreground']};
            border: 1px solid {primary['background']};
        }}
        QPushButton#primaryButton:hover {{
            background-color: {primary['hover']};
            border-color: {primary['hover']};
        }}
        QPushButton#primaryButton:pressed {{
            background-color: {primary['pressed']};
            border-color: {primary['pressed']};
        }}
        QPushButton#primaryButton:focus {{ border: 1px solid {Colors.ROSE_LIGHT}; }}
        QPushButton#primaryButton:disabled {{
            background-color: {Colors.BACKGROUND_ELEVATED};
            color: {Colors.TEXT_MUTED};
            border-color: {Colors.DIVIDER};
        }}
        QPushButton#secondaryButton:disabled {{
            color: {Colors.TEXT_MUTED};
            background-color: {Colors.BACKGROUND_ELEVATED};
            border-color: {Colors.DIVIDER};
        }}
        QPushButton#navItem {{
            text-align: left;
            background-color: transparent;
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid transparent;
            border-left: 3px solid transparent;
            border-radius: 10px;
            padding: 0 10px;
            min-height: 40px;
            font-size: {Typography.SIZE_MD}px;
            font-weight: {Typography.WEIGHT_MEDIUM};
        }}
        QPushButton#navItem:hover {{
            background-color: {GLASS_STYLES['nav_hover']};
            color: {Colors.TEXT_PRIMARY};
            border-color: {GLASS_STYLES['nav_hover_border']};
        }}
        QPushButton#navItem[active="true"] {{
            background: qlineargradient(
                x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {GLASS_STYLES['nav_start']},
                stop: 1 {GLASS_STYLES['nav_end']}
            );
            color: {Colors.ROSE_LIGHT};
            border: 1px solid {GLASS_STYLES['nav_border']};
            border-left: 3px solid {Colors.ROSE_PRIMARY};
            font-weight: {Typography.WEIGHT_SEMIBOLD};
        }}
        QPushButton#navItem:focus {{ border-color: {Colors.BORDER_HIGHLIGHT}; }}
        QPushButton#navItem[active="true"]:focus {{ border-color: {Colors.ROSE_LIGHT}; }}

        QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QSpinBox, QPlainTextEdit {{
            background-color: {INPUT_STYLES['background']};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {INPUT_STYLES['border']};
            border-radius: {Radius.MEDIUM}px;
            padding: 7px 10px;
            selection-background-color: {Colors.ACCENT_TINT};
            selection-color: {Colors.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
        QSpinBox:focus, QPlainTextEdit:focus {{ border: 1px solid {INPUT_STYLES['focus']}; }}
        QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
        QDateTimeEdit:disabled, QSpinBox:disabled, QPlainTextEdit:disabled {{
            color: {Colors.TEXT_MUTED};
            background-color: {Colors.BACKGROUND_ELEVATED};
            border-color: {Colors.DIVIDER};
        }}
        QLineEdit::placeholder {{ color: {INPUT_STYLES['placeholder']}; }}
        QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {{
            width: 24px;
            border-left: 1px solid {Colors.DIVIDER};
            border-top-right-radius: {Radius.MEDIUM}px;
            border-bottom-right-radius: {Radius.MEDIUM}px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.SURFACE_RAISED};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_HIGHLIGHT};
            selection-background-color: {Colors.ACCENT_TINT};
            selection-color: {Colors.TEXT_PRIMARY};
            outline: none;
            padding: 4px;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 17px;
            background-color: {Colors.SURFACE_RAISED};
            border-left: 1px solid {Colors.DIVIDER};
        }}
        QSpinBox::up-button {{ border-top-right-radius: {Radius.MEDIUM}px; }}
        QSpinBox::down-button {{ border-bottom-right-radius: {Radius.MEDIUM}px; }}

        QCheckBox {{ color: {Colors.TEXT_SECONDARY}; spacing: 7px; font-size: {Typography.SIZE_SM}px; }}
        QCheckBox:disabled {{ color: {Colors.TEXT_MUTED}; }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 5px;
            background: {INPUT_STYLES['background']};
            border: 1px solid {INPUT_STYLES['border']};
        }}
        QCheckBox::indicator:hover {{ border-color: {Colors.ROSE_PRIMARY}; }}
        QCheckBox::indicator:checked {{ background: {Colors.ROSE_PRIMARY}; border-color: {Colors.ROSE_LIGHT}; }}
        QCheckBox::indicator:disabled {{ background: {Colors.BACKGROUND_ELEVATED}; border-color: {Colors.DIVIDER}; }}

        QProgressBar {{
            background-color: {Colors.BACKGROUND_SECONDARY};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER};
            border-radius: 5px;
            height: 9px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 {Colors.ROSE_SOFT}, stop: 1 {Colors.ROSE_LIGHT});
            border-radius: 4px;
        }}

        QLabel#severityBadge, QLabel#statusBadge {{
            border: 1px solid transparent;
            border-radius: {Radius.SMALL}px;
            font-size: {Typography.SIZE_XS}px;
            font-weight: {Typography.WEIGHT_BOLD};
            letter-spacing: 0.25px;
        }}
        QLabel#severityBadge[severity="HIGH"] {{
            color: {Colors.ERROR}; background-color: {Colors.ERROR_TINT}; border-color: {Colors.ERROR};
        }}
        QLabel#severityBadge[severity="MEDIUM"] {{
            color: {Colors.WARNING}; background-color: {Colors.WARNING_TINT}; border-color: {Colors.WARNING};
        }}
        QLabel#severityBadge[severity="LOW"] {{
            color: {Colors.SUCCESS}; background-color: {Colors.SUCCESS_TINT}; border-color: {Colors.SUCCESS};
        }}
        QLabel#severityBadge[severity="UNKNOWN"] {{
            color: {Colors.TEXT_SECONDARY}; background-color: {Colors.SURFACE_RAISED}; border-color: {Colors.BORDER};
        }}
        QLabel#statusBadge[tone="neutral"] {{
            color: {Colors.TEXT_SECONDARY}; background-color: {Colors.SURFACE_RAISED}; border-color: {Colors.BORDER};
        }}
        QLabel#statusBadge[tone="info"] {{
            color: {Colors.ROSE_LIGHT}; background-color: {Colors.ACCENT_TINT}; border-color: {Colors.ROSE_SOFT};
        }}
        QLabel#statusBadge[tone="success"] {{
            color: {Colors.SUCCESS}; background-color: {Colors.SUCCESS_TINT}; border-color: {Colors.SUCCESS};
        }}
        QLabel#statusBadge[tone="warning"] {{
            color: {Colors.WARNING}; background-color: {Colors.WARNING_TINT}; border-color: {Colors.WARNING};
        }}
        QLabel#statusBadge[tone="error"] {{
            color: {Colors.ERROR}; background-color: {Colors.ERROR_TINT}; border-color: {Colors.ERROR};
        }}

        QTableWidget {{
            background-color: {TABLE_STYLES['background']};
            alternate-background-color: {TABLE_STYLES['alternate']};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {GLASS_STYLES['table_border']};
            border-radius: {Radius.MEDIUM}px;
            gridline-color: transparent;
            selection-background-color: {TABLE_STYLES['selection']};
            selection-color: {Colors.TEXT_PRIMARY};
            outline: 0;
        }}
        QTableWidget::item {{
            padding: 6px 8px;
            border-bottom: 1px solid {TABLE_STYLES['divider']};
        }}
        QTableWidget::item:hover {{ background-color: {TABLE_STYLES['hover']}; }}
        QTableWidget::item:selected {{ background-color: {TABLE_STYLES['selection']}; color: {Colors.TEXT_PRIMARY}; }}
        QTableWidget:focus {{ border-color: {Colors.ROSE_PRIMARY}; }}
        QHeaderView::section {{
            background-color: {TABLE_STYLES['header']};
            color: {Colors.TEXT_MUTED};
            border: none;
            border-bottom: 1px solid {Colors.BORDER};
            padding: 9px 8px;
            min-height: 18px;
            font-size: {Typography.SIZE_XS}px;
            font-weight: {Typography.WEIGHT_BOLD};
            letter-spacing: 0.35px;
        }}
        QTableWidget[compactDensity="true"]::item {{
            padding-left: {TABLE_STYLES['compact_horizontal_padding']}px;
            padding-right: {TABLE_STYLES['compact_horizontal_padding']}px;
        }}
        QHeaderView[compactDensity="true"]::section {{
            padding-left: {TABLE_STYLES['compact_header_padding']}px;
            padding-right: {TABLE_STYLES['compact_header_padding']}px;
        }}
        QTableCornerButton::section {{ background-color: {TABLE_STYLES['header']}; border: none; }}

        QDialog, QMessageBox {{ background-color: {Colors.BACKGROUND_SECONDARY}; }}
        QMessageBox QLabel {{ color: {Colors.TEXT_PRIMARY}; min-width: 260px; }}
        QMenu {{
            background-color: {Colors.SURFACE_RAISED};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_HIGHLIGHT};
            padding: 5px;
        }}
        QMenu::item {{ padding: 6px 22px 6px 10px; border-radius: 5px; }}
        QMenu::item:selected {{ color: {Colors.ROSE_LIGHT}; background-color: {Colors.ACCENT_TINT}; }}
        QMenu::separator {{ height: 1px; background: {Colors.DIVIDER}; margin: 5px 4px; }}

        QScrollArea {{ border: none; }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px 1px 3px 3px; }}
        QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 1px 3px 1px 3px; }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {GLASS_STYLES['scroll_handle']};
            min-height: 28px;
            min-width: 28px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {Colors.ROSE_SOFT};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
            width: 0;
            height: 0;
        }}
        QStatusBar {{
            background-color: {Colors.BACKGROUND_SECONDARY};
            color: {Colors.TEXT_MUTED};
            border-top: 1px solid {Colors.DIVIDER};
            font-size: {Typography.SIZE_XS}px;
        }}
        QStatusBar::item {{ border: none; }}
        QToolTip {{
            color: {Colors.TOOLTIP_TEXT};
            background-color: {Colors.TOOLTIP_BACKGROUND};
            border: 1px solid {Colors.BORDER_HIGHLIGHT};
            border-radius: 5px;
            padding: 5px 7px;
        }}
    """


def apply_dark_theme(application: QApplication) -> None:
    """Apply LogShield's dark glass palette and shared widget styling."""
    application.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.BACKGROUND_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.TOOLTIP_BACKGROUND))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.TOOLTIP_TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.SURFACE_RAISED))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(Colors.ERROR))
    palette.setColor(QPalette.ColorRole.Link, QColor(Colors.ROSE_LIGHT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.ACCENT_TINT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.TEXT_PRIMARY))

    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(disabled, role, QColor(Colors.TEXT_MUTED))
    palette.setColor(disabled, QPalette.ColorRole.Button, QColor(Colors.BACKGROUND_ELEVATED))

    application.setPalette(palette)
    application.setStyleSheet(_stylesheet())
