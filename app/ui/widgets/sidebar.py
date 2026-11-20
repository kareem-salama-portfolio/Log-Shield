"""Application navigation sidebar and reusable navigation item."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.navigation import PRIMARY_SCREENS
from app.ui.styles.tokens import Colors, Dimensions, Spacing
from app.ui.widgets.icons import create_icon


_NAV_ICONS = {
    "dashboard": "dashboard",
    "log_import": "file-plus",
    "detection_rules": "sliders",
    "incidents_reports": "triangle-alert",
}


class NavigationItem(QPushButton):
    """Sidebar button keyed by a stable screen identifier."""

    def __init__(self, screen_id: str, label: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(label.replace("&", "&&"), parent)
        self.screen_id = screen_id
        self.icon_name = icon_name
        self.setObjectName("navItem")
        self.setMinimumHeight(Dimensions.NAV_ITEM_HEIGHT)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.set_active(False)

    def set_active(self, active: bool) -> None:
        """Update checked state and accent icon for the selected route."""
        self.setProperty("active", "true" if active else "false")
        color = Colors.ROSE_LIGHT if active else Colors.TEXT_MUTED
        self.setIcon(create_icon(self.icon_name, color, Dimensions.ICON_SIZE))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class Sidebar(QFrame):
    """Persistent brand and route rail for the desktop application."""

    navigation_requested = Signal(str)

    def __init__(self, active_screen: str = "dashboard", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(Dimensions.SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.XL, Spacing.MD, Spacing.MD)
        layout.setSpacing(0)

        brand = QHBoxLayout()
        brand.setContentsMargins(Spacing.XS, 0, Spacing.XS, 0)
        brand.setSpacing(Spacing.SM)
        icon_tile = QFrame()
        icon_tile.setObjectName("brandIconTile")
        icon_tile.setFixedSize(40, 40)
        icon_layout = QVBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        brand_icon = QLabel()
        brand_icon.setPixmap(create_icon("shield", Colors.ROSE_PRIMARY, 22).pixmap(22, 22))
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setAccessibleName("LogShield shield")
        icon_layout.addWidget(brand_icon)
        brand.addWidget(icon_tile, 0, Qt.AlignmentFlag.AlignVCenter)

        brand_copy = QVBoxLayout()
        brand_copy.setContentsMargins(0, 0, 0, 0)
        brand_copy.setSpacing(1)
        brand_name = QLabel("LogShield")
        brand_name.setObjectName("brandName")
        brand_subtitle = QLabel("SECURITY LOG ANALYZER")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_copy.addWidget(brand_name)
        brand_copy.addWidget(brand_subtitle)
        brand.addLayout(brand_copy, 1)
        layout.addLayout(brand)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("sidebarDivider")
        layout.addWidget(line)
        layout.addSpacing(Spacing.XL)

        section = QLabel("WORKSPACE")
        section.setObjectName("sidebarSection")
        section.setContentsMargins(Spacing.XS, 0, 0, Spacing.XS)
        layout.addWidget(section)
        layout.addSpacing(Spacing.XS)

        self.items: dict[str, NavigationItem] = {}
        for screen_id, label in PRIMARY_SCREENS:
            item = NavigationItem(screen_id, label, _NAV_ICONS[screen_id], self)
            item.clicked.connect(lambda _checked=False, current_id=screen_id: self.navigation_requested.emit(current_id))
            self.items[screen_id] = item
            layout.addWidget(item)
            layout.addSpacing(Spacing.XXS)

        self.set_active_screen(active_screen)
        layout.addStretch(1)

        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.Shape.HLine)
        footer_line.setObjectName("sidebarDivider")
        layout.addWidget(footer_line)
        layout.addSpacing(Spacing.MD)

        footer = QHBoxLayout()
        footer.setContentsMargins(Spacing.XS, 0, Spacing.XS, 0)
        footer.setSpacing(Spacing.XS)
        status_dot = QFrame()
        status_dot.setObjectName("statusDot")
        status_dot.setFixedSize(7, 7)
        status_dot.setAccessibleName("Offline analysis ready")
        footer.addWidget(status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        footer_text = QLabel("LOCAL WORKSPACE  ·  OFFLINE")
        footer_text.setObjectName("sidebarFooter")
        footer_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        footer.addWidget(footer_text, 1)
        layout.addLayout(footer)

        version = QLabel("VERSION  0.1.0")
        version.setObjectName("sidebarFooter")
        version.setContentsMargins(Spacing.XS, Spacing.XS, 0, 0)
        layout.addWidget(version)

    def set_active_screen(self, screen_id: str) -> None:
        """Select a known screen while preserving all stable screen IDs."""
        for current_id, item in self.items.items():
            item.set_active(current_id == screen_id)
