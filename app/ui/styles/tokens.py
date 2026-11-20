"""Centralized LogShield desktop design tokens.

The burgundy and rose palette is shared by Qt widgets, Matplotlib charts, and
small screen-specific visual details so every screen stays in the same system.
"""


class Colors:
    """Named palette roles for surfaces, text, semantic states, and charts."""

    BACKGROUND = "#10090E"
    BACKGROUND_SECONDARY = "#180D15"
    BACKGROUND_ELEVATED = "#21121D"
    SURFACE = "#291722"
    SURFACE_RAISED = "#351C2A"
    SURFACE_HOVER = "#422536"
    BORDER = "#583344"
    BORDER_HIGHLIGHT = "#855066"
    DIVIDER = "#432B37"

    TEXT_PRIMARY = "#F7EDF1"
    TEXT_SECONDARY = "#C6ADB8"
    TEXT_MUTED = "#A58E99"

    ROSE_PRIMARY = "#D9799C"
    ROSE_LIGHT = "#F0A4BD"
    ROSE_SOFT = "#B95C80"
    MAGENTA_MUTED = "#A84D75"
    ROSE_TINT = "#432331"

    # Semantic state colors remain distinct from the brand accent.
    SUCCESS = "#69B88C"
    SUCCESS_TINT = "#20362C"
    WARNING = "#D7A36F"
    WARNING_TINT = "#3B292B"
    ERROR = "#D96B79"
    ERROR_TINT = "#3D202B"

    # Existing names are retained as roles for presentation code that uses an
    # accent or severity label; all values now resolve to the approved palette.
    ACCENT = ROSE_PRIMARY
    ACCENT_HOVER = ROSE_LIGHT
    ACCENT_TINT = ROSE_TINT
    HIGH = ERROR
    HIGH_TINT = ERROR_TINT
    MEDIUM = WARNING
    MEDIUM_TINT = WARNING_TINT

    TOOLTIP_BACKGROUND = SURFACE_RAISED
    TOOLTIP_TEXT = TEXT_PRIMARY

    CHART_SERIES = (
        "#87435F",
        "#9B4A69",
        MAGENTA_MUTED,
        ROSE_SOFT,
        "#C56B8B",
        ROSE_PRIMARY,
        ROSE_LIGHT,
    )


class Spacing:
    """Four-pixel based spacing scale, in device-independent pixels."""

    XXS = 4
    XS = 8
    SM = 12
    MD = 16
    LG = 20
    XL = 24
    XXL = 32
    XXXL = 40


class Typography:
    """Desktop type scale and weights."""

    FAMILY = "Segoe UI"
    MONOSPACE_FAMILY = "Cascadia Code"
    SIZE_XS = 10
    SIZE_SM = 11
    SIZE_MD = 13
    SIZE_LG = 15
    SIZE_XL = 18
    SIZE_TITLE = 28
    SIZE_METRIC = 27

    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Radius:
    """Corner radii for compact controls through primary glass panels."""

    SMALL = 6
    MEDIUM = 9
    LARGE = 14
    XL = 18


class Dimensions:
    """Stable layout dimensions used by shared widgets."""

    SIDEBAR_WIDTH = 232
    NAV_ITEM_HEIGHT = 44
    BUTTON_HEIGHT = 38
    TABLE_ROW_HEIGHT = 42
    TABLE_HEADER_HEIGHT = 36
    ICON_SIZE = 18


class Shadows:
    """Subtle Qt shadow settings; kept low to preserve readable surfaces."""

    CARD_BLUR = 18
    CARD_Y = 5
    CARD_ALPHA = 62


BUTTON_STYLES = {
    "primary": {
        "background": Colors.ROSE_PRIMARY,
        "foreground": Colors.BACKGROUND,
        "hover": Colors.ROSE_LIGHT,
        "pressed": Colors.ROSE_SOFT,
    },
    "secondary": {
        "background": Colors.SURFACE_RAISED,
        "foreground": Colors.TEXT_PRIMARY,
        "hover": Colors.SURFACE_HOVER,
        "pressed": Colors.BACKGROUND_ELEVATED,
    },
}

INPUT_STYLES = {
    "background": Colors.BACKGROUND_SECONDARY,
    "border": Colors.BORDER,
    "focus": Colors.ROSE_LIGHT,
    "placeholder": Colors.TEXT_MUTED,
}

TABLE_STYLES = {
    "background": Colors.SURFACE,
    "alternate": Colors.BACKGROUND_ELEVATED,
    "header": Colors.BACKGROUND_ELEVATED,
    "hover": Colors.SURFACE_HOVER,
    "selection": "#563044",
    "divider": Colors.DIVIDER,
    "compact_horizontal_padding": 4,
    "compact_header_padding": 5,
}

CARD_STYLES = {
    "background": Colors.SURFACE,
    "border": Colors.BORDER_HIGHLIGHT,
    "radius": Radius.LARGE,
    "padding": Spacing.XL,
}

GLASS_STYLES = {
    "sidebar_start": "rgba(53, 28, 42, 246)",
    "sidebar_end": "rgba(24, 13, 21, 242)",
    "sidebar_border": "rgba(133, 80, 102, 145)",
    "card_start": "rgba(53, 28, 42, 232)",
    "card_end": "rgba(33, 18, 29, 242)",
    "card_border": "rgba(133, 80, 102, 118)",
    "card_highlight": "rgba(240, 164, 189, 105)",
    "icon_start": "rgba(185, 92, 128, 88)",
    "icon_end": "rgba(53, 28, 42, 228)",
    "icon_border": "rgba(217, 121, 156, 106)",
    "empty_start": "rgba(67, 35, 49, 236)",
    "empty_end": "rgba(41, 23, 34, 236)",
    "empty_border": "rgba(217, 121, 156, 135)",
    "detail_background": "rgba(33, 18, 29, 205)",
    "divider": "rgba(133, 80, 102, 90)",
    "nav_hover": "rgba(66, 37, 54, 172)",
    "nav_hover_border": "rgba(133, 80, 102, 90)",
    "nav_start": "rgba(185, 92, 128, 150)",
    "nav_end": "rgba(67, 35, 49, 198)",
    "nav_border": "rgba(217, 121, 156, 172)",
    "table_border": "rgba(88, 51, 68, 112)",
    "scroll_handle": "rgba(185, 92, 128, 134)",
}
