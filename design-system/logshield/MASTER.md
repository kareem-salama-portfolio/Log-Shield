# LogShield Visual Design System

This is the shared visual source of truth for the native PySide6 application. The attached Security Overview screenshot establishes the visual direction. Qt surfaces use translucency, gradients, thin borders, rounded corners, and restrained shadows to approximate glass; widgets do not use browser-only backdrop blur.

## Product and layout

- Product: offline desktop application for authentication-log review.
- Framework: native PySide6 widgets with Matplotlib charts.
- Preserve the four existing destinations and their current order: Security Overview, Log Import & Explorer, Detection Rules, Incidents & Reports.
- Use one shared shell, spacing system, component language, and interaction treatment across every screen.
- Keep the existing page information, service states, keyboard navigation, and screen behavior intact.
- The shell uses an inset 232 px sidebar, scrollable content, and the existing compact layouts for narrower desktop windows.

## Color palette

| Role | Token | Hex |
|---|---|---|
| Main background | `Colors.BACKGROUND` | `#10090E` |
| Secondary background | `Colors.BACKGROUND_SECONDARY` | `#180D15` |
| Elevated background | `Colors.BACKGROUND_ELEVATED` | `#21121D` |
| Glass surface | `Colors.SURFACE` | `#291722` |
| Strong glass surface | `Colors.SURFACE_RAISED` | `#351C2A` |
| Hover surface | `Colors.SURFACE_HOVER` | `#422536` |
| Subtle border | `Colors.BORDER` | `#583344` |
| Highlight border | `Colors.BORDER_HIGHLIGHT` | `#855066` |
| Primary text | `Colors.TEXT_PRIMARY` | `#F7EDF1` |
| Secondary text | `Colors.TEXT_SECONDARY` | `#C6ADB8` |
| Supporting text | `Colors.TEXT_MUTED` | `#A58E99` |
| Rose primary | `Colors.ROSE_PRIMARY` | `#D9799C` |
| Rose light | `Colors.ROSE_LIGHT` | `#F0A4BD` |
| Rose soft | `Colors.ROSE_SOFT` | `#B95C80` |
| Muted magenta | `Colors.MAGENTA_MUTED` | `#A84D75` |
| Success | `Colors.SUCCESS` | `#69B88C` |
| Warning | `Colors.WARNING` | `#D7A36F` |
| Error | `Colors.ERROR` | `#D96B79` |

- Keep rose accents restrained and use semantic success, warning, and error colors only for their state meanings.
- Do not use blue, cyan, navy, or gold as UI accents.
- Severity and status labels always retain visible text; color only reinforces meaning.

## Glass surfaces and effects

- The application background is near-black burgundy with a faint rose-plum radial wash.
- Sidebar and cards use layered burgundy/plum gradients with alpha, rounded corners, and thin rose borders.
- Matplotlib chart canvases are transparent so the card surface remains visible behind plots.
- Shared cards use a low-opacity native Qt drop shadow. Focus and selected navigation use a clear rose border/tint, without broad neon glow.
- Tables and inputs use inset dark surfaces with rose selection/focus states.
- Native OS file dialogs retain their platform appearance; application-owned dialogs use the shared Qt palette.

## Typography and spacing

- Use Segoe UI on Windows with the platform fallback elsewhere. Use Cascadia Code only for technical identifiers when already present.
- Type sizes: 10, 11, 13, 15, 18, 27, and 28 px. Weights: 400, 500, 600, and 700.
- Use the 4 px spacing scale from `Spacing.XXS` (4) through `Spacing.XXXL` (40).
- Cards use 14 px corners; the sidebar uses 18 px; controls use 9 px; compact badges use 6 px.
- Buttons are at least 38 px tall. Standard table rows are 42 px with 36 px headers.

## Shared components and accessibility

- Cards use one shared surface system, consistent padding, subtle borders, and low shadows.
- Primary actions use rose with a dark foreground; secondary actions use raised glass surfaces and a visible border.
- Inputs use the secondary background and a rose focus border. Disabled controls have muted text and surfaces.
- Tables use quiet headers, alternating burgundy rows, minimal dividers, visible keyboard selection, and consistent compact-density variants.
- Navigation uses consistent local SVG line icons and a rose glass selected state.
- Icon paths use one 24 px viewBox, 1.8 px stroke, and 18–22 px display sizing.
- Keep text contrast readable, make keyboard focus visible, and do not rely on color alone.

## Charts

- Matplotlib figure and axes are transparent over their glass cards.
- Use rose for the failure trend and a restrained ordered rose/magenta series for source comparisons.
- Ticks and labels use secondary/muted text; grid lines use the subtle border token.
- Empty charts show plain centered text. Keep axis labels legible at wide and compact sizes.
