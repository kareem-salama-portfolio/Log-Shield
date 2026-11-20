"""Detection configuration controls and honest run-operation states."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.detection import DetectionProgress, DetectionRunRequest
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PanelCard, PrimaryButton, StatusBadge


class RuleSettingsPanel(PanelCard):
    """Collect the agreed run parameters and display service operation state."""

    run_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Detection Configuration",
            "Set the failure pattern window and review the current run readiness.",
            parent=parent,
        )
        self._events_available: bool | None = None
        self._event_availability_error: str | None = None
        self._detection_service_available = False
        self._detection_service_error: str | None = None
        self._is_running = False

        self.failure_threshold = _numeric_input(
            "failureThresholdInput", 3, 20, 5, " failures", "Failure Threshold, 3 to 20 failed attempts"
        )
        self.time_window = _numeric_input(
            "timeWindowInput", 1, 60, 10, " min", "Time Window, 1 to 60 minutes"
        )

        fields = QGridLayout()
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setHorizontalSpacing(Spacing.MD)
        fields.setVerticalSpacing(Spacing.XS)

        failure_label = QLabel("Failure Threshold")
        failure_label.setObjectName("fieldLabel")
        failure_label.setBuddy(self.failure_threshold)
        fields.addWidget(failure_label, 0, 0)
        fields.addWidget(self.failure_threshold, 1, 0)
        failure_hint = QLabel("Failed attempts per source")
        failure_hint.setObjectName("fieldHint")
        fields.addWidget(failure_hint, 2, 0)

        window_label = QLabel("Time Window")
        window_label.setObjectName("fieldLabel")
        window_label.setBuddy(self.time_window)
        fields.addWidget(window_label, 0, 1)
        fields.addWidget(self.time_window, 1, 1)
        window_hint = QLabel("Minutes")
        window_hint.setObjectName("fieldHint")
        fields.addWidget(window_hint, 2, 1)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        self.content_layout.addLayout(fields)

        high_row = QVBoxLayout()
        high_row.setContentsMargins(0, Spacing.SM, 0, 0)
        high_row.setSpacing(Spacing.XXS)
        self.high_severity_toggle = QCheckBox("HIGH severity option")
        self.high_severity_toggle.setObjectName("highSeverityToggle")
        self.high_severity_toggle.setAccessibleName("HIGH severity option; backend meaning not confirmed")
        self.high_severity_toggle.setToolTip(
            "This control is not included in detection requests until its backend meaning is confirmed."
        )
        self.high_severity_hint = QLabel(
            "Its operational meaning is pending backend confirmation; this value is not sent with a run request."
        )
        self.high_severity_hint.setObjectName("fieldHint")
        self.high_severity_hint.setWordWrap(True)
        high_row.addWidget(self.high_severity_toggle)
        high_row.addWidget(self.high_severity_hint)
        self.content_layout.addLayout(high_row)

        operation_row = QHBoxLayout()
        operation_row.setContentsMargins(0, Spacing.SM, 0, 0)
        operation_row.setSpacing(Spacing.SM)
        self.operation_badge = StatusBadge("READY", "neutral")
        operation_row.addWidget(self.operation_badge, 0, Qt.AlignmentFlag.AlignTop)
        self.operation_message = QLabel("Checking detection readiness…")
        self.operation_message.setObjectName("operationStatus")
        self.operation_message.setWordWrap(True)
        operation_row.addWidget(self.operation_message, 1)
        self.content_layout.addLayout(operation_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("detectionProgressBar")
        self.progress_bar.setAccessibleName("Detection run progress")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.content_layout.addWidget(self.progress_bar)

        self.run_button = PrimaryButton("Run Detection")
        self.run_button.setAccessibleName("Run Detection")
        self.run_button.clicked.connect(self.request_detection)
        self.content_layout.addSpacing(Spacing.SM)
        self.content_layout.addWidget(self.run_button)
        self._refresh_availability()

    def set_event_availability(
        self,
        available: bool | None,
        error_message: str | None = None,
    ) -> None:
        """Update whether the event service confirms eligible imported events."""
        self._events_available = available
        self._event_availability_error = error_message
        self._refresh_availability()

    def set_detection_service_available(
        self,
        available: bool,
        error_message: str | None = None,
    ) -> None:
        """Update whether a production detection service is connected."""
        self._detection_service_available = available
        self._detection_service_error = error_message
        self._refresh_availability()

    def set_running(self, status: str = "Detection is running…") -> None:
        """Lock duplicate requests while a real worker is active."""
        self._is_running = True
        self.operation_badge.setText("RUNNING")
        self.operation_badge.setProperty("tone", "info")
        self.operation_message.setText(status)
        self.operation_message.setProperty("tone", "info")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self._refresh_status_styles()
        self._refresh_availability()

    def set_progress(self, progress: DetectionProgress) -> None:
        """Display only progress values supplied by the service."""
        if not self._is_running:
            return
        percentage = progress.get("percentage")
        if percentage is None:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(max(0, min(100, int(percentage))))
        status = progress.get("status")
        if status:
            self.operation_message.setText(status)

    def set_run_completed(self, run_id: int, *, worker_active: bool = False) -> None:
        """Show completion after a service has returned a persisted run."""
        self._is_running = worker_active
        self.progress_bar.hide()
        self.operation_badge.setText("COMPLETED")
        self.operation_badge.setProperty("tone", "success")
        self.operation_message.setText(f"Run #{run_id} completed and stored.")
        self.operation_message.setProperty("tone", "success")
        self._refresh_status_styles()
        self._update_run_button()

    def set_run_failed(self, message: str, *, worker_active: bool = False) -> None:
        """Show a failed service result without changing run history."""
        self._is_running = worker_active
        self.progress_bar.hide()
        self.operation_badge.setText("FAILED")
        self.operation_badge.setProperty("tone", "error")
        self.operation_message.setText(message)
        self.operation_message.setProperty("tone", "error")
        self._refresh_status_styles()
        self._update_run_button()

    def set_worker_finished(self) -> None:
        """Re-enable a valid new request after the worker thread has actually exited."""
        self._is_running = False
        self._update_run_button()

    def request_detection(self) -> bool:
        """Emit only the agreed threshold and window after readiness checks."""
        if self._is_running or not self.run_button.isEnabled():
            return False
        request: DetectionRunRequest = {
            "failure_threshold": self.failure_threshold.value(),
            "time_window_minutes": self.time_window.value(),
        }
        self.set_running()
        self.run_requested.emit(request)
        return True

    def _refresh_availability(self) -> None:
        self._update_run_button()
        if self._is_running:
            return

        if self._events_available is False:
            message = "Import authentication logs before running detection."
            badge, tone = "NO EVENTS", "warning"
        elif self._event_availability_error:
            message = self._event_availability_error
            badge, tone = "EVENT SERVICE", "error"
        elif self._events_available is None:
            message = "Event service unavailable. Import authentication logs before running detection."
            badge, tone = "UNAVAILABLE", "error"
        elif not self._detection_service_available:
            message = self._detection_service_error or "Detection service unavailable. No run was started."
            badge, tone = "UNAVAILABLE", "error"
        else:
            message = "Eligible authentication events are available."
            badge, tone = "READY", "success"

        self.operation_badge.setText(badge)
        self.operation_badge.setProperty("tone", tone)
        self.operation_message.setText(message)
        self.operation_message.setProperty("tone", tone)
        self._refresh_status_styles()

    def _update_run_button(self) -> None:
        can_run = (
            self._events_available is True
            and self._detection_service_available
            and not self._is_running
        )
        self.run_button.setEnabled(can_run)

    def _refresh_status_styles(self) -> None:
        for widget in (self.operation_badge, self.operation_message):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


def _numeric_input(
    object_name: str,
    minimum: int,
    maximum: int,
    default: int,
    suffix: str,
    accessible_name: str,
) -> QSpinBox:
    field = QSpinBox()
    field.setObjectName(object_name)
    field.setRange(minimum, maximum)
    field.setValue(default)
    field.setSuffix(suffix)
    field.setAccessibleName(accessible_name)
    return field
