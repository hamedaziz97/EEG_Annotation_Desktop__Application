"""
Main dashboard class that orchestrates all components of the EEG annotation tool.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import numpy as np

from EEG_Annotation_Desktop__Application.models import EEGData, DisplaySettings, AnnotationCollection
# FilterHandler is no longer needed here, as filtering is delegated to the plotter
from EEG_Annotation_Desktop__Application.file_handlers import EEGFileHandler, AnnotationFileHandler
from EEG_Annotation_Desktop__Application.plotting import EEGPlotter
from EEG_Annotation_Desktop__Application.ui_components import ControlPanel, AnnotationPanel, ChannelSettingsDialog
from EEG_Annotation_Desktop__Application.annotation_system import AnnotationManager


class EEGDashboard:
    """Main dashboard class that coordinates all components."""

    def __init__(self, root_window):
        """Initialize the EEG dashboard."""
        self.root_window = root_window
        self.root_window.title("EEG Dashboard - Annotation Tool")
        self.root_window.geometry("1200x800")

        # Initialize data
        self.eeg_data = None
        self.display_settings = DisplaySettings()
        self.annotation_collection = None
        self.current_window_start = 0

        # Initialize components
        # Pass the root_window to the AnnotationManager for dialog parenting
        self.annotation_manager = AnnotationManager(
            root_window=self.root_window,
            on_selection_change=self._on_selection_change
        )
        self.plotter = None
        self.control_panel = None
        self.annotation_panel = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create control panel
        self.control_panel = ControlPanel(
            parent=main_frame,
            on_time_scale_change=self._on_time_scale_change,
            on_amplitude_scale_change=self._on_amplitude_scale_change,
            on_filter_change=self._on_filter_change,
            on_navigation=self._on_navigation,
            on_channel_settings=self._on_channel_settings,
            on_load_file=self.load_eeg_file
        )

        # Create annotation panel
        self.annotation_panel = AnnotationPanel(
            parent=main_frame,
            on_add_annotation=self._on_add_annotation,
            on_clear_selection=self._on_clear_selection,
            on_save_annotations=self._on_save_annotations,
            on_load_annotations=self._on_load_annotations
        )

        # Create plotter
        self.plotter = EEGPlotter(main_frame)
        self.plotter.set_mouse_callbacks(
            press_callback=self._on_mouse_press,
            release_callback=self._on_mouse_release,
            move_callback=self._on_mouse_move,
            channel_selection_callback=self._on_channel_selection
        )

    def _on_time_scale_change(self, new_time_scale: float):
        """Handle time scale change."""
        self.display_settings.time_scale = new_time_scale
        if self.eeg_data is not None:
            self._update_plot()
            self._update_window_info()

    def _on_amplitude_scale_change(self, new_amplitude_scale: float):
        """Handle amplitude scale change."""
        self.display_settings.amplitude_scale = new_amplitude_scale
        if self.eeg_data is not None:
            self._update_plot()

    def _on_filter_change(self, lowpass: float, highpass: float):
        """Handle filter changes."""
        self.display_settings.lowpass_filter = lowpass
        self.display_settings.highpass_filter = highpass
        if self.eeg_data is not None:
            self._update_plot()

    def _on_navigation(self, action: str):
        """Handle navigation actions."""
        if self.eeg_data is None:
            return

        total_duration = self.eeg_data.total_duration
        time_scale = self.display_settings.time_scale

        if action == "next":
            if self.current_window_start + time_scale < total_duration:
                self.current_window_start += time_scale
        elif action == "previous":
            if self.current_window_start > 0:
                self.current_window_start = max(0, self.current_window_start - time_scale)
        elif action == "jump_forward":
            jump_distance = time_scale * 5
            if self.current_window_start + jump_distance < total_duration:
                self.current_window_start += jump_distance
            else:
                self.current_window_start = max(0, total_duration - time_scale)
        elif action == "jump_backward":
            jump_distance = time_scale * 5
            self.current_window_start = max(0, self.current_window_start - jump_distance)

        self._update_plot()
        self._update_window_info()

    def _on_channel_settings(self):
        """Handle channel settings button click."""
        if not self.eeg_data:
            messagebox.showwarning("Warning", "Please load an EEG file first")
            return

        dialog = ChannelSettingsDialog(
            parent=self.root_window,
            channel_names=self.eeg_data.channel_names,
            selected_channels=self.display_settings.selected_channels,
            on_apply=self._on_channel_selection_apply
        )
        dialog.show()

    def _on_channel_selection_apply(self, selected_channels: list):
        """Handle channel selection apply."""
        self.display_settings.selected_channels = selected_channels
        self._update_plot()

    def _on_channel_selection(self, selected_channels: list):
        """Handle annotation channel selection."""
        self.annotation_manager.set_selected_channels(selected_channels)
        self._update_plot()

    def _on_mouse_press(self, event):
        """Handle mouse press events."""
        self.annotation_manager.handle_mouse_press(
            event,
            self.annotation_panel.is_annotation_mode_enabled()
        )

    def _on_mouse_move(self, event):
        """Handle mouse move events."""
        self.annotation_manager.handle_mouse_move(
            event,
            self.annotation_panel.is_annotation_mode_enabled()
        )

    def _on_mouse_release(self, event):
        """Handle mouse release events."""
        self.annotation_manager.handle_mouse_release(
            event,
            self.annotation_panel.is_annotation_mode_enabled()
        )

    def _on_selection_change(self):
        """Handle selection state changes."""
        start_time, end_time = self.annotation_manager.get_selection_info()
        self.annotation_panel.update_selection_info(start_time, end_time)

        # The plot update will now also handle displaying the final annotation
        if self.eeg_data is not None:
            self._update_plot()
            self._update_annotations_display()

    def _on_clear_selection(self):
        """Handle clear selection."""
        self.annotation_manager.clear_selection()

    def _on_add_annotation(self, text: str):
        """Handle add annotation."""
        # This is now triggered automatically by the dialog workflow
        pass

    def _on_save_annotations(self):
        """Handle save annotations."""
        if not self.annotation_collection or not self.annotation_collection.annotations:
            messagebox.showwarning("Warning", "No annotations to save")
            return

        AnnotationFileHandler.save_annotations(self.annotation_collection)

    def _on_load_annotations(self):
        """Handle load annotations."""
        collection = AnnotationFileHandler.load_annotations()
        if collection:
            self.annotation_collection = collection
            self.annotation_manager.set_annotation_collection(collection)
            self._update_plot()
            self._update_annotations_display()

    def load_eeg_file(self, file_path: str = None):
        """Load an EEG file."""
        if file_path is None:
            file_path = EEGFileHandler.get_file_dialog_path()

        if not file_path:
            return

        eeg_data = EEGFileHandler.load_eeg_file(file_path)
        if eeg_data is None:
            messagebox.showerror("Error",
                                 "Failed to load EEG file.\n\nSupported formats: EDF, BDF")
            return

        # Store data
        self.eeg_data = eeg_data
        self.display_settings.selected_channels = list(range(len(eeg_data.channel_names)))

        # Reset window position
        self.current_window_start = 0

        # Clear previous annotations and create new annotation collection
        self.annotation_collection = AnnotationCollection.create_empty(
            edf_file=os.path.basename(file_path),
            window_size=self.display_settings.time_scale,
            sampling_freq=eeg_data.sampling_freq
        )
        self.annotation_manager.set_annotation_collection(self.annotation_collection)

        # Clear any existing selection and annotation display
        self.annotation_manager.clear_selection()
        self.annotation_panel.update_annotations_display("")

        # Update display
        self._update_plot()
        self._update_window_info()
        self._update_annotations_display()

        # Show success message
        file_type = "EDF" if file_path.endswith('.edf') else "BDF" if file_path.endswith('.bdf') else "EEG"
        messagebox.showinfo("Success",
                            f"Loaded {file_type} file with {len(eeg_data.channel_names)} channels\n"
                            f"Sampling frequency: {eeg_data.sampling_freq} Hz\n"
                            f"Duration: {eeg_data.total_duration:.1f} seconds")

    def _update_plot(self):
        """Update the EEG plot."""
        if self.eeg_data is None:
            return

        # The plotter will now handle filtering on the visible window of data.
        # We no longer need to filter the entire dataset here.
        # This is the key performance improvement.

        # Get annotations for current window
        window_end = self.current_window_start + self.display_settings.time_scale
        annotations = self.annotation_manager.get_annotations_in_window(
            self.current_window_start, window_end
        )

        # Plot data - pass the original, unfiltered eeg_data
        self.plotter.plot_eeg_data(
            eeg_data=self.eeg_data,
            display_settings=self.display_settings,
            current_window_start=self.current_window_start,
            selection_state=self.annotation_manager.selection_state,
            annotations=annotations
        )

    def _update_window_info(self):
        """Update window information display."""
        if self.eeg_data is None:
            return

        total_duration = self.eeg_data.total_duration
        time_scale = self.display_settings.time_scale
        current_window = int(self.current_window_start / time_scale) + 1
        total_windows = int(np.ceil(total_duration / time_scale))

        self.control_panel.update_window_info(
            current_window=current_window,
            total_windows=total_windows,
            window_start=self.current_window_start,
            window_end=self.current_window_start + time_scale
        )

    def _update_annotations_display(self):
        """Update annotations display."""
        if self.eeg_data is None:
            return

        window_end = self.current_window_start + self.display_settings.time_scale
        annotations_text = self.annotation_manager.get_annotations_display_text(
            self.current_window_start, window_end
        )

        self.annotation_panel.update_annotations_display(annotations_text)

    def run(self):
        """Run the dashboard application."""
        self.root_window.mainloop()