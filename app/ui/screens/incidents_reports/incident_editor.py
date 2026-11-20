"""Incident review editor and three-choice unsaved-changes dialog."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.detection import DetectionIncident
from app.ui.styles.tokens import Spacing
from app.ui.widgets.components import PanelCard, PrimaryButton, SecondaryButton, StatusBadge


MAX_NOTE_LENGTH = 500


class IncidentEditorPanel(PanelCard):
    """Edit the contract's review status and note; persist only through a signal."""

    save_requested = Signal(int, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Review Status & Notes",
            "Update analyst review fields for the selected incident.",
            parent=parent,
        )
        self.incident: DetectionIncident | None = None
        self._saved_status = "NEW"
        self._saved_note = ""
        self._saving = False

        status_label = QLabel("Review Status")
        status_label.setObjectName("fieldLabel")
        self.status_selector = QComboBox()
        self.status_selector.setObjectName("incidentStatusSelector")
        for label, value in (("New", "NEW"), ("Reviewed", "REVIEWED"), ("False Positive", "FALSE_POSITIVE")):
            self.status_selector.addItem(label, value)
        self.status_selector.setAccessibleName("Incident review status")
        self.content_layout.addWidget(status_label)
        self.content_layout.addWidget(self.status_selector)

        note_header = QHBoxLayout()
        note_header.setContentsMargins(0, Spacing.SM, 0, 0)
        note_label = QLabel("Analyst Note")
        note_label.setObjectName("fieldLabel")
        self.character_counter = QLabel(f"0 / {MAX_NOTE_LENGTH}")
        self.character_counter.setObjectName("fieldHint")
        self.character_counter.setAccessibleName("Note character count")
        note_header.addWidget(note_label)
        note_header.addStretch(1)
        note_header.addWidget(self.character_counter)
        self.content_layout.addLayout(note_header)

        self.note_editor = QPlainTextEdit()
        self.note_editor.setObjectName("incidentNoteEditor")
        self.note_editor.setPlaceholderText("Add a concise review note…")
        self.note_editor.setAccessibleName(f"Incident note, maximum {MAX_NOTE_LENGTH} characters")
        self.note_editor.setMinimumHeight(88)
        self.note_editor.setMaximumHeight(140)
        self.content_layout.addWidget(self.note_editor)

        state_row = QHBoxLayout()
        state_row.setContentsMargins(0, Spacing.SM, 0, 0)
        state_row.setSpacing(Spacing.SM)
        self.state_badge = StatusBadge("NO INCIDENT", "neutral")
        state_row.addWidget(self.state_badge, 0, Qt.AlignmentFlag.AlignTop)
        self.state_message = QLabel("Select an incident to edit its review status or note.")
        self.state_message.setObjectName("operationStatus")
        self.state_message.setWordWrap(True)
        state_row.addWidget(self.state_message, 1)
        self.content_layout.addLayout(state_row)

        self.save_button = PrimaryButton("Save Changes")
        self.save_button.setAccessibleName("Save incident review changes")
        self.save_button.setEnabled(False)
        self.content_layout.addSpacing(Spacing.XS)
        self.content_layout.addWidget(self.save_button)

        self.status_selector.currentIndexChanged.connect(self._refresh_dirty_state)
        self.note_editor.textChanged.connect(self._handle_note_changed)
        self.save_button.clicked.connect(self.save_changes)
        self._set_form_enabled(False)

    @property
    def current_status(self) -> str:
        value = self.status_selector.currentData()
        return str(value) if value is not None else "NEW"

    @property
    def current_note(self) -> str:
        return self.note_editor.toPlainText()

    @property
    def is_dirty(self) -> bool:
        return self.incident is not None and (
            self.current_status != self._saved_status or self.current_note != self._saved_note
        )

    @property
    def is_saving(self) -> bool:
        return self._saving

    def set_incident(self, incident: DetectionIncident | None) -> None:
        self.incident = dict(incident) if incident is not None else None
        self._saving = False
        self.status_selector.blockSignals(True)
        self.note_editor.blockSignals(True)
        if incident is None:
            self._saved_status = "NEW"
            self._saved_note = ""
            self.status_selector.setCurrentIndex(0)
            self.note_editor.setPlainText("")
            self.state_badge.setText("NO INCIDENT")
            self.state_badge.setProperty("tone", "neutral")
            self.state_message.setText("Select an incident to edit its review status or note.")
            self.state_message.setProperty("tone", "neutral")
        else:
            status = incident["status"].upper()
            index = self.status_selector.findData(status)
            if index < 0:
                index = 0
            self.status_selector.setCurrentIndex(index)
            note = incident["note"][:MAX_NOTE_LENGTH]
            self.note_editor.setPlainText(note)
            self._saved_status = status
            self._saved_note = note
            self.state_badge.setText("LOADED")
            self.state_badge.setProperty("tone", "neutral")
            self.state_message.setText(f"Editing incident #{incident['id']}.")
            self.state_message.setProperty("tone", "neutral")
        self.status_selector.blockSignals(False)
        self.note_editor.blockSignals(False)
        self._set_form_enabled(incident is not None)
        self._update_counter()
        self._refresh_dirty_state()
        self._refresh_status_style()

    def save_changes(self) -> bool:
        if self.incident is None or not self.is_dirty or self._saving:
            return False
        self._saving = True
        self._set_form_enabled(False)
        self.state_badge.setText("SAVING")
        self.state_badge.setProperty("tone", "info")
        self.state_message.setText("Waiting for the review service to confirm the save…")
        self.state_message.setProperty("tone", "info")
        self.save_button.setEnabled(False)
        self._refresh_status_style()
        self.save_requested.emit(self.incident["id"], self.current_status, self.current_note)
        return True

    def set_save_success(self, updated_incident: DetectionIncident) -> bool:
        if self.incident is None or updated_incident["id"] != self.incident["id"]:
            return False
        if updated_incident["run_id"] != self.incident["run_id"]:
            self.set_save_failure("The review service returned an incident from a different run.")
            return False
        self.set_incident(updated_incident)
        self.state_badge.setText("SAVED")
        self.state_badge.setProperty("tone", "success")
        self.state_message.setText("Review changes were saved by the service.")
        self.state_message.setProperty("tone", "success")
        self._refresh_status_style()
        return True

    def set_save_failure(self, message: str) -> None:
        self._saving = False
        self._set_form_enabled(self.incident is not None)
        self.state_badge.setText("SAVE FAILED")
        self.state_badge.setProperty("tone", "error")
        self.state_message.setText(message)
        self.state_message.setProperty("tone", "error")
        self.save_button.setEnabled(self.incident is not None and self.is_dirty)
        self._refresh_status_style()

    def _handle_note_changed(self) -> None:
        note = self.note_editor.toPlainText()
        if len(note) > MAX_NOTE_LENGTH:
            cursor = self.note_editor.textCursor()
            position = min(cursor.position(), MAX_NOTE_LENGTH)
            self.note_editor.blockSignals(True)
            self.note_editor.setPlainText(note[:MAX_NOTE_LENGTH])
            cursor = self.note_editor.textCursor()
            cursor.setPosition(position)
            self.note_editor.setTextCursor(cursor)
            self.note_editor.blockSignals(False)
        self._update_counter()
        self._refresh_dirty_state()

    def _update_counter(self) -> None:
        count = min(len(self.current_note), MAX_NOTE_LENGTH)
        self.character_counter.setText(f"{count} / {MAX_NOTE_LENGTH}")
        self.character_counter.setAccessibleName(f"{count} of {MAX_NOTE_LENGTH} characters")

    def _refresh_dirty_state(self, *_args: object) -> None:
        if self._saving:
            return
        if self.incident is None:
            self.save_button.setEnabled(False)
            return
        if self.is_dirty:
            self.state_badge.setText("UNSAVED")
            self.state_badge.setProperty("tone", "warning")
            self.state_message.setText("Changes are local until the review service confirms a save.")
            self.state_message.setProperty("tone", "warning")
            self.save_button.setEnabled(True)
        else:
            self.state_badge.setText("READY")
            self.state_badge.setProperty("tone", "neutral")
            self.state_message.setText(f"Incident #{self.incident['id']} is up to date.")
            self.state_message.setProperty("tone", "neutral")
            self.save_button.setEnabled(False)
        self._refresh_status_style()

    def _set_form_enabled(self, enabled: bool) -> None:
        self.status_selector.setEnabled(enabled and not self._saving)
        self.note_editor.setEnabled(enabled and not self._saving)

    def _refresh_status_style(self) -> None:
        for widget in (self.state_badge, self.state_message):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()


class UnsavedChangesDialog(QDialog):
    """Non-blocking prompt with explicit save, discard, and cancel actions."""

    decision_made = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Unsaved Incident Changes")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        title = QLabel("You have unsaved changes")
        title.setObjectName("sectionTitle")
        body = QLabel("Save your incident review edits before switching incidents or leaving this screen?")
        body.setObjectName("pageSubtitle")
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_button = PrimaryButton("Save Changes")
        self.discard_button = SecondaryButton("Discard Changes")
        self.cancel_button = SecondaryButton("Cancel Navigation")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.discard_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.save_button.clicked.connect(lambda: self._choose("save"))
        self.discard_button.clicked.connect(lambda: self._choose("discard"))
        self.cancel_button.clicked.connect(lambda: self._choose("cancel"))
        self.rejected.connect(lambda: self.decision_made.emit("cancel"))

    def _choose(self, choice: str) -> None:
        self.decision_made.emit(choice)
        self.done(QDialog.DialogCode.Accepted)
