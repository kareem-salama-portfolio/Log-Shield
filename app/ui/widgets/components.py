"""Reusable presentation components shared by LogShield screens."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.styles.tokens import Colors, Dimensions, Shadows, Spacing
from app.ui.widgets.icons import create_icon


class PrimaryButton(QPushButton):
    """Primary action button with shared sizing and focus behavior."""

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setMinimumHeight(Dimensions.BUTTON_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(create_icon(icon_name, Colors.BACKGROUND, 16))


class SecondaryButton(QPushButton):
    """Secondary action button with shared sizing and focus behavior."""

    def __init__(self, text: str, icon_name: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setMinimumHeight(Dimensions.BUTTON_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(create_icon(icon_name, Colors.TEXT_SECONDARY, 16))


class PageHeader(QWidget):
    """Page title, supporting description, and optional right-side action."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        action: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.LG)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(Spacing.XXS)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        copy.addWidget(self.title_label)
        copy.addWidget(self.subtitle_label)

        row.addLayout(copy, 1)
        if action is not None:
            row.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)


class SectionHeader(QWidget):
    """Consistent heading block for cards and content sections."""

    def __init__(
        self,
        title: str,
        description: str = "",
        action: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Spacing.MD)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        copy.addWidget(self.title_label)
        self.description_label: QLabel | None = None
        if description:
            self.description_label = QLabel(description)
            self.description_label.setObjectName("sectionDescription")
            copy.addWidget(self.description_label)
        row.addLayout(copy, 1)
        if action is not None:
            row.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)


class PanelCard(QFrame):
    """Raised surface with a section header and a content layout."""

    def __init__(
        self,
        title: str,
        description: str = "",
        action: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panelCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        layout.setSpacing(Spacing.SM)
        self.header = SectionHeader(title, description, action)
        layout.addWidget(self.header)

        self.content = QWidget(self)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        layout.addWidget(self.content, 1)


class MetricCard(QFrame):
    """KPI card with a value, supporting detail, and line icon."""

    def __init__(
        self,
        title: str,
        value: str,
        icon_name: str,
        detail: QWidget | str | None = None,
        icon_color: str = Colors.ACCENT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XXS)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(Spacing.XS)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricLabel")
        self.title_label.setWordWrap(True)
        top.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignVCenter)

        icon_tile = QFrame()
        icon_tile.setObjectName("metricIconTile")
        icon_tile.setFixedSize(36, 36)
        tile_layout = QVBoxLayout(icon_tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(create_icon(icon_name, icon_color, 18).pixmap(18, 18))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setAccessibleName(f"{title} icon")
        tile_layout.addWidget(icon_label)
        top.addWidget(icon_tile, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        layout.addWidget(self.value_label)

        self.detail_widget: QWidget | None = None
        if isinstance(detail, QWidget):
            self.detail_widget = detail
            layout.addWidget(detail)
        elif isinstance(detail, str) and detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("metricDetail")
            layout.addWidget(detail_label)

    def set_value(self, value: str) -> None:
        """Update the displayed metric value."""
        self.value_label.setText(value)


class SeverityBadge(QLabel):
    """Compact severity marker whose text remains explicit without color."""

    def __init__(self, text: str, severity: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        normalized = severity.upper()
        if normalized not in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
            raise ValueError(f"Unsupported incident severity: {severity}")
        self.setObjectName("severityBadge")
        self.setProperty("severity", normalized)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(22)
        self.setContentsMargins(Spacing.XS, 0, Spacing.XS, 0)
        self.setAccessibleName(f"{normalized} severity")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class StatusBadge(QLabel):
    """Compact outcome/status label that retains meaning without color."""

    _TONES = {"neutral", "info", "success", "warning", "error"}

    def __init__(self, text: str, tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        normalized_tone = tone.lower()
        if normalized_tone not in self._TONES:
            raise ValueError(f"Unsupported status tone: {tone}")
        self.setObjectName("statusBadge")
        self.setProperty("tone", normalized_tone)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(22)
        self.setContentsMargins(Spacing.XS, 0, Spacing.XS, 0)
        self.setAccessibleName(text)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


class EmptyStateBanner(QFrame):
    """Prominent import prompt used while no authentication events exist."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyStateBanner")
        row = QHBoxLayout(self)
        row.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        row.setSpacing(Spacing.MD)

        icon_tile = QFrame()
        icon_tile.setObjectName("metricIconTile")
        icon_tile.setFixedSize(38, 38)
        icon_layout = QVBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon = QLabel()
        icon.setPixmap(create_icon("file-plus", Colors.ACCENT, 18).pixmap(18, 18))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setAccessibleName("Import log file")
        icon_layout.addWidget(icon)
        row.addWidget(icon_tile, 0, Qt.AlignmentFlag.AlignVCenter)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        self.title_label = QLabel("Import a log file to begin")
        self.title_label.setObjectName("emptyStateTitle")
        self.message_label = QLabel(
            "Your overview will populate after authentication events are imported."
        )
        self.message_label.setObjectName("pageSubtitle")
        self.message_label.setWordWrap(True)
        copy.addWidget(self.title_label)
        copy.addWidget(self.message_label)
        row.addLayout(copy, 1)

        self.action_button = PrimaryButton("Open Log Import", "arrow-right")
        row.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignVCenter)


def _apply_card_shadow(widget: QWidget) -> None:
    """Give elevated surfaces a small, consistent native Qt shadow."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(Shadows.CARD_BLUR)
    shadow.setOffset(0, Shadows.CARD_Y)
    shadow.setColor(QColor(0, 0, 0, Shadows.CARD_ALPHA))
    widget.setGraphicsEffect(shadow)
