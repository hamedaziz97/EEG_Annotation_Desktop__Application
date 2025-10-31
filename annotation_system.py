"""
Annotation system module for selection and management of EEG annotations.
"""

from typing import List, Optional, Callable
from tkinter import messagebox

from EEG_Annotation_Desktop__Application.models import Annotation, AnnotationCollection, SelectionState
from EEG_Annotation_Desktop__Application.ui_components import AnnotationDialog


class AnnotationManager:
    """Manages annotation selection and operations."""

    def __init__(self, root_window, on_selection_change: Optional[Callable[[], None]] = None):
        """
        Initialize annotation manager.

        Args:
            root_window: The main tkinter root window, used as a parent for dialogs.
            on_selection_change: Callback for when selection changes
        """
        self.root_window = root_window
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

            # Finalize selection range
            if self.selection_state.start_time > self.selection_state.end_time:
                self.selection_state.start_time, self.selection_state.end_time = \
                    self.selection_state.end_time, self.selection_state.start_time

            # If selection is valid, open the dialog to add an annotation
            if self.selection_state.has_selection:
                self._prompt_for_annotation()
            else:
                self.clear_selection()
        else:
            self.clear_selection()

    def _prompt_for_annotation(self):
        """Open a dialog to get annotation text and add the annotation."""
        dialog = AnnotationDialog(self.root_window, self.predefined_annotations)
        annotation_text = dialog.result

        if annotation_text:
            self.add_annotation(annotation_text)
        else:
            # If the user cancelled, clear the visual selection
            self.clear_selection()

    def clear_selection(self):
        """Clear current annotation selection."""
        self.selection_state.clear()
        if self.on_selection_change:
            self.on_selection_change()

    def add_annotation(self, text: str) -> bool:
        """
        Add annotation for the current selection.

        Args:
            text: Annotation text from the dialog.

        Returns:
            True if successful, False otherwise.
        """
        if not self.selection_state.has_selection:
            # This case should ideally not be hit with the new workflow
            messagebox.showwarning("Warning", "No valid time range is selected.", parent=self.root_window)
            return False

        if not self.annotation_collection:
            messagebox.showwarning("Warning", "No annotation collection available.", parent=self.root_window)
            return False

        # Get color for the annotation
        color = self.annotation_colors.get(text, (0.5, 0.5, 0.5, 0.3)) # Default to gray

        # Create annotation
        annotation = Annotation.create(
            text=text,
            start_time=self.selection_state.start_time,
            end_time=self.selection_state.end_time,
            color=color,
            channels=self.selected_channels
        )

        # Add to collection
        self.annotation_collection.add_annotation(annotation)

        # Clear selection and trigger plot update via callback
        self.clear_selection()

        messagebox.showinfo("Success",
                           f"Annotation added: {annotation.start_time:.2f}s - {annotation.end_time:.2f}s",
                           parent=self.root_window)
        return True

    def get_annotations_in_window(self, window_start: float, window_end: float) -> List[Annotation]:
        """
        Get annotations that overlap with the current window.

        Args:
            window_start: Start time of current window
            window_end: End time of current window

        Returns:
            List of overlapping annotations
        """
        if not self.annotation_collection:
            return []

        return self.annotation_collection.get_annotations_in_range(window_start, window_end)

    def get_annotations_display_text(self, window_start: float, window_end: float) -> str:
        """
        Get formatted text for displaying annotations in current window.

        Args:
            window_start: Start time of current window
            window_end: End time of current window

        Returns:
            Formatted text string
        """
        annotations = self.get_annotations_in_window(window_start, window_end)

        if not annotations:
            return ""

        text_lines = []
        for i, annotation in enumerate(annotations, 1):
            # Calculate overlap with current window
            overlap_start = max(annotation.start_time, window_start)
            overlap_end = min(annotation.end_time, window_end)

            text_lines.append(
                f"{i}. {annotation.text} "
                f"({overlap_start:.2f}s - {overlap_end:.2f}s) "
                f"[{annotation.timestamp[:19]}]"
            )

        return "\n".join(text_lines)

    def get_selection_info(self) -> tuple:
        """Get current selection start and end times."""
        # For drawing, we need to handle the case where the user drags right-to-left
        if self.selection_state.start_time is not None and self.selection_state.end_time is not None:
            start = min(self.selection_state.start_time, self.selection_state.end_time)
            end = max(self.selection_state.start_time, self.selection_state.end_time)
            return start, end
        return None, None

    def has_selection(self) -> bool:
        """Check if there's a current selection."""
        return self.selection_state.has_selection


class AnnotationValidator:
    """Validates annotation data and operations."""

    @staticmethod
    def validate_annotation_text(text: str) -> bool:
        """Validate annotation text."""
        return bool(text and text.strip())

    @staticmethod
    def validate_time_range(start_time: float, end_time: float) -> bool:
        """Validate time range for annotation."""
        return (start_time is not None and
                end_time is not None and
                abs(end_time - start_time) >= 0.1)

    @staticmethod
    def validate_annotation_data(annotation_data: dict) -> bool:
        """Validate annotation data dictionary."""
        required_fields = ['text', 'startTime', 'endTime', 'timestamp', 'duration', 'color', 'channels']
        return all(field in annotation_data for field in required_fields)


class AnnotationFormatter:
    """Formats annotation data for display and export."""

    @staticmethod
    def format_annotation_summary(annotation: Annotation) -> str:
        """Format annotation for summary display."""
        return (f"{annotation.text} "
                f"({annotation.start_time:.2f}s - {annotation.end_time:.2f}s, "
                f"Duration: {annotation.duration:.2f}s)")

    @staticmethod
    def format_annotation_list(annotations: List[Annotation]) -> str:
        """Format list of annotations for display."""
        if not annotations:
            return "No annotations"

        lines = []
        for i, annotation in enumerate(annotations, 1):
            lines.append(f"{i}. {AnnotationFormatter.format_annotation_summary(annotation)}")

        return "\n".join(lines)

    @staticmethod
    def format_export_summary(collection: AnnotationCollection) -> str:
        """Format annotation collection for export summary."""
        total_annotations = sum(len(ann_list) for ann_list in collection.annotations.values())
        return (f"Exported {total_annotations} annotations from "
                f"{len(collection.annotations)} annotation groups")
