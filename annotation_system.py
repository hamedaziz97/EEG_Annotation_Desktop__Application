"""
Annotation system module for selection and management of EEG annotations, refactored for PyQt6.
"""

from typing import List, Optional, Callable
from PyQt6.QtWidgets import QMessageBox, QWidget

from EEG_Annotation_Desktop__Application.models import Annotation, AnnotationCollection, SelectionState
from EEG_Annotation_Desktop__Application.ui_components import AnnotationDialog


class AnnotationManager:
    """Manages annotation selection and operations."""

    def __init__(self, root_window: QWidget, on_selection_change: Optional[Callable[[], None]] = None):
        """
        Initialize annotation manager.

        Args:
            root_window: The main QWidget, used as a parent for dialogs.
            on_selection_change: Callback for when selection changes
        """
        self.parent_widget = root_window
        self.selection_state = SelectionState()
        self.annotation_collection = None
        self.on_selection_change = on_selection_change
        self.predefined_annotations = ["Seizure", "Artifact", "Spike", "Sleep"]
        self.selected_channels = []
        self.annotation_colors = {
            "Seizure": (1.0, 0.0, 0.0, 0.3),
            "Artifact": (0.0, 1.0, 0.0, 0.3),
            "Spike": (0.0, 0.0, 1.0, 0.3),
            "Sleep": (1.0, 1.0, 0.0, 0.3)
        }

    def set_annotation_collection(self, collection: AnnotationCollection):
        """Set the current annotation collection."""
        self.annotation_collection = collection

    def set_selected_channels(self, channels: List[str]):
        """Set the currently selected channels for annotation."""
        self.selected_channels = channels

    def handle_mouse_press(self, event, is_annotation_mode_enabled: bool):
        """Handle mouse press event for annotation selection."""
        if not is_annotation_mode_enabled or not event.inaxes or event.button != 1:
            return

        self.selection_state.mouse_pressed = True
        self.selection_state.start_time = event.xdata
        self.selection_state.end_time = event.xdata
        self.selection_state.is_selecting = True

        if self.on_selection_change:
            self.on_selection_change()

    def handle_mouse_move(self, event, is_annotation_mode_enabled: bool):
        """Handle mouse move event for annotation selection."""
        if (not is_annotation_mode_enabled or
            not self.selection_state.mouse_pressed or
            not self.selection_state.is_selecting or
            not event.inaxes or
            event.xdata is None):
            return

        self.selection_state.end_time = event.xdata

        if self.on_selection_change:
            self.on_selection_change()

    def handle_mouse_release(self, event, is_annotation_mode_enabled: bool):
        """Handle mouse release event for annotation selection."""
        if not is_annotation_mode_enabled or not self.selection_state.mouse_pressed:
            return

        self.selection_state.mouse_pressed = False

        if (self.selection_state.is_selecting and
            event.inaxes and
            event.xdata is not None):

            self.selection_state.end_time = event.xdata

            if self.selection_state.start_time > self.selection_state.end_time:
                self.selection_state.start_time, self.selection_state.end_time = \
                    self.selection_state.end_time, self.selection_state.start_time

            if self.selection_state.has_selection:
                self._prompt_for_annotation()
            else:
                self.clear_selection()
        else:
            self.clear_selection()

    def _prompt_for_annotation(self):
        """Open a dialog to get annotation text and add the annotation."""
        dialog = AnnotationDialog(self.parent_widget, self.predefined_annotations)
        if dialog.exec():
            annotation_text = dialog.get_result()
            if annotation_text:
                self.add_annotation(annotation_text)
            else:
                self.clear_selection()
        else:
            self.clear_selection()

    def clear_selection(self):
        """Clear current annotation selection."""
        self.selection_state.clear()
        if self.on_selection_change:
            self.on_selection_change()

    def add_annotation(self, text: str) -> bool:
        """
        Add annotation for the current selection.
        """
        if not self.selection_state.has_selection:
            QMessageBox.warning(self.parent_widget, "Warning", "No valid time range is selected.")
            return False

        if not self.annotation_collection:
            QMessageBox.warning(self.parent_widget, "Warning", "No annotation collection available.")
            return False

        color = self.annotation_colors.get(text, (0.5, 0.5, 0.5, 0.3))

        annotation = Annotation.create(
            text=text,
            start_time=self.selection_state.start_time,
            end_time=self.selection_state.end_time,
            color=color,
            channels=self.selected_channels
        )

        self.annotation_collection.add_annotation(annotation)
        self.clear_selection()

        QMessageBox.information(self.parent_widget, "Success",
                           f"Annotation added: {annotation.start_time:.2f}s - {annotation.end_time:.2f}s")
        return True

    def get_annotations_in_window(self, window_start: float, window_end: float) -> List[Annotation]:
        """Get annotations that overlap with the current window."""
        if not self.annotation_collection:
            return []
        return self.annotation_collection.get_annotations_in_range(window_start, window_end)

    def get_selection_info(self) -> tuple:
        """Get current selection start and end times."""
        if self.selection_state.start_time is not None and self.selection_state.end_time is not None:
            start = min(self.selection_state.start_time, self.selection_state.end_time)
            end = max(self.selection_state.start_time, self.selection_state.end_time)
            return start, end
        return None, None
