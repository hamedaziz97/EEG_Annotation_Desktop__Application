"""
Main dashboard class that orchestrates all components of the EEG annotation tool.
"""

import os
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox, QSplitter, QStatusBar, QLabel,
    QToolBar, QComboBox, QToolButton
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon

from EEG_Annotation_Desktop__Application.models import EEGData, DisplaySettings, AnnotationCollection
from EEG_Annotation_Desktop__Application.file_handlers import EEGFileHandler, AnnotationFileHandler
from EEG_Annotation_Desktop__Application.plotting import EEGPlotter
from EEG_Annotation_Desktop__Application.ui_components import (
    LeftSidebarWidget, AnnotationPanel, EditAnnotationDialog, NavigationWidget
)
from EEG_Annotation_Desktop__Application.annotation_system import AnnotationManager


class EEGDashboard(QMainWindow):
    """Main dashboard class that coordinates all components."""

    def __init__(self):
        """Initialize the EEG dashboard."""
        super().__init__()
        self.setWindowTitle("EEG Annotation Tool")
        self.setGeometry(100, 100, 1800, 1000)

        # Initialize data
        self.eeg_data = None
        self.display_settings = DisplaySettings()
        self.annotation_collection = None
        self.current_window_start = 0

        # Playback timer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.playback_speed = 1.0 # 1.0 = normal speed

        # Initialize components
        self.annotation_manager = AnnotationManager(
            root_window=self,
            on_selection_change=self._on_selection_change
        )
        self.plotter = None
        self.left_sidebar = None
        self.annotation_panel = None
        self.status_bar = None

        self._setup_ui()
        self._create_toolbar()

    def _setup_ui(self):
        """Set up the user interface."""
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(main_splitter)

        # Left Sidebar
        self.left_sidebar = LeftSidebarWidget(
            on_load_file=self.load_eeg_file,
            on_channel_selection_change=self._on_channel_selection_apply,
            on_time_scale_change=self._on_time_scale_change,
            on_amplitude_scale_change=self._on_amplitude_scale_change,
            on_filter_change=self._on_filter_change,
            on_theme_change=self._toggle_theme
        )
        main_splitter.addWidget(self.left_sidebar)

        # Center Panel (Plotter)
        self.plotter = EEGPlotter()
        self.plotter.set_mouse_callbacks(
            press_callback=self._on_mouse_press,
            release_callback=self._on_mouse_release,
            move_callback=self._on_mouse_move,
            channel_selection_callback=self._on_channel_selection
        )
        main_splitter.addWidget(self.plotter)

        # Right Sidebar (Annotation Panel)
        self.annotation_panel = AnnotationPanel(
            on_add_annotation=self._on_add_annotation,
            on_delete_selected=self._on_delete_selected_annotation,
            on_save_annotations=self._on_save_annotations,
            on_load_annotations=self._on_load_annotations,
            on_edit_annotation=self._on_edit_annotation,
            on_jump_to_annotation=self._jump_to_annotation
        )
        main_splitter.addWidget(self.annotation_panel)

        # Set initial sizes for the splitter
        main_splitter.setSizes([280, 1240, 280])

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.window_info_label = QLabel("No file loaded")
        self.status_bar.addPermanentWidget(self.window_info_label)

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # App Logo and Name
        lbl_logo = QLabel(" EEG-Annotator")
        lbl_logo.setStyleSheet("font-weight: bold; font-size: 16px;")
        toolbar.addWidget(lbl_logo)
        toolbar.addSeparator()

        # File Actions
        action_open = QAction(QIcon.fromTheme("document-open"), "Open EEG File", self)
        action_open.triggered.connect(self.load_eeg_file)
        toolbar.addAction(action_open)
        
        toolbar.addSeparator()

        # Navigation
        self.navigation_widget = NavigationWidget(on_navigation=self._on_navigation)
        toolbar.addWidget(self.navigation_widget)
        
        toolbar.addSeparator()

        # Annotation Mode
        self.action_anno_mode = QAction("Annotation Mode", self)
        self.action_anno_mode.setCheckable(True)
        self.action_anno_mode.setIcon(QIcon.fromTheme("document-edit"))
        toolbar.addAction(self.action_anno_mode)

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

    def _on_filter_change(self, lowpass: float, highpass: float, notch: bool):
        """Handle filter changes."""
        self.display_settings.lowpass_filter = lowpass
        self.display_settings.highpass_filter = highpass
        # Notch filter logic to be implemented
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
        elif action == "first":
            self.current_window_start = 0
        elif action == "last":
            self.current_window_start = max(0, total_duration - time_scale)
        elif action == "play":
            self.playback_timer.start(int(1000 / self.playback_speed)) # Update every second
        elif action == "pause":
            self.playback_timer.stop()
        
        self._update_plot()
        self._update_window_info()

    def _advance_playback(self):
        """Advance the window during playback."""
        if self.eeg_data is None:
            self.playback_timer.stop()
            return
        
        if self.current_window_start + self.display_settings.time_scale < self.eeg_data.total_duration:
            self.current_window_start += 1 # Advance by 1 second
            self._update_plot()
            self._update_window_info()
        else:
            self.playback_timer.stop()
            self.navigation_widget.play_btn.setChecked(False)
            self.navigation_widget._toggle_play()

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
            self.action_anno_mode.isChecked()
        )

    def _on_mouse_move(self, event):
        """Handle mouse move events."""
        self.annotation_manager.handle_mouse_move(
            event,
            self.action_anno_mode.isChecked()
        )

    def _on_mouse_release(self, event):
        """Handle mouse release events."""
        self.annotation_manager.handle_mouse_release(
            event,
            self.action_anno_mode.isChecked()
        )

    def _on_selection_change(self):
        """Handle selection state changes."""
        if self.eeg_data is not None:
            self._update_plot()
            self._update_annotations_display()

    def _on_add_annotation(self, text: str):
        """Handle add annotation."""
        pass

    def _on_delete_selected_annotation(self):
        """Handle delete selected annotation button click."""
        selected_index = self.annotation_panel.get_selected_annotation_index()
        if selected_index is None:
            QMessageBox.warning(self, "Warning", "Please select an annotation to delete.")
            return

        if not self.annotation_collection or not self.annotation_collection.annotations:
            return

        # This logic needs to be more robust, mapping table row to original annotation
        all_annotations = self.annotation_collection.get_all_annotations()
        if selected_index < len(all_annotations):
            annotation_to_delete = all_annotations[selected_index]
            self.annotation_collection.remove_annotation(annotation_to_delete)
            self._update_plot()
            self._update_annotations_display()

    def _on_edit_annotation(self, row, col):
        """Handle edit selected annotation."""
        selected_index = self.annotation_panel.get_selected_annotation_index()
        if selected_index is None:
            return

        all_annotations = self.annotation_collection.get_all_annotations()
        if selected_index < len(all_annotations):
            annotation_to_edit = all_annotations[selected_index]
            
            dialog = EditAnnotationDialog(self, annotation_to_edit, self.annotation_manager.predefined_annotations)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    annotation_to_edit.text = result["text"]
                    annotation_to_edit.start_time = result["start_time"]
                    annotation_to_edit.end_time = result["end_time"]
                    self._update_plot()
                    self._update_annotations_display()

    def _on_save_annotations(self):
        """Handle save annotations."""
        if not self.annotation_collection or not self.annotation_collection.annotations:
            QMessageBox.warning(self, "Warning", "No annotations to save")
            return

        AnnotationFileHandler.save_annotations(self, self.annotation_collection)

    def _on_load_annotations(self):
        """Handle load annotations."""
        collection = AnnotationFileHandler.load_annotations(self)
        if collection:
            self.annotation_collection = collection
            self.annotation_manager.set_annotation_collection(collection)
            self._update_plot()
            self._update_annotations_display()

    def _jump_to_annotation(self, annotation_index: int):
        """Jump the view to a specific annotation."""
        if not self.annotation_collection or not self.eeg_data:
            return
        
        all_annotations = self.annotation_collection.get_all_annotations()
        if annotation_index < len(all_annotations):
            annotation = all_annotations[annotation_index]
            self.current_window_start = annotation.start_time
            self._update_plot()
            self._update_window_info()

    def load_eeg_file(self, file_path: str = None):
        """Load an EEG file."""
        if file_path is None:
            file_path = EEGFileHandler.get_file_dialog_path(self)

        if not file_path:
            return

        eeg_data = EEGFileHandler.load_eeg_file(file_path)
        if eeg_data is None:
            QMessageBox.critical(self, "Error", "Failed to load EEG file.\n\nSupported formats: EDF, BDF")
            return

        self.eeg_data = eeg_data
        self.display_settings.selected_channels = list(range(len(eeg_data.channel_names)))
        self.current_window_start = 0
        
        # Reset filters
        self.left_sidebar.reset_filters()
        self.display_settings.lowpass_filter = None
        self.display_settings.highpass_filter = None

        self.annotation_collection = AnnotationCollection.create_empty(
            edf_file=os.path.basename(file_path),
            window_size=self.display_settings.time_scale,
            sampling_freq=eeg_data.sampling_freq
        )
        self.annotation_manager.set_annotation_collection(self.annotation_collection)
        self.annotation_manager.clear_selection()
        
        # Update file info in the sidebar
        self.left_sidebar.update_file_info(
            filename=os.path.basename(file_path),
            duration=eeg_data.total_duration,
            sfreq=eeg_data.sampling_freq,
            n_channels=len(eeg_data.channel_names),
            channel_names=eeg_data.channel_names
        )

        self._update_plot()
        self._update_window_info()
        self._update_annotations_display()

        file_type = "EDF" if file_path.endswith('.edf') else "BDF" if file_path.endswith('.bdf') else "EEG"
        self.status_bar.showMessage(f"Loaded {file_type} file: {os.path.basename(file_path)}", 5000)

    def _update_plot(self):
        """Update the EEG plot."""
        if self.eeg_data is None:
            return

        window_end = self.current_window_start + self.display_settings.time_scale
        annotations = self.annotation_manager.get_annotations_in_window(
            self.current_window_start, window_end
        )

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

        self.window_info_label.setText(
            f"Window {current_window}/{total_windows} "
            f"({self.current_window_start:.1f}s - {self.current_window_start + time_scale:.1f}s)"
        )

    def _update_annotations_display(self):
        """Update annotations display."""
        if not self.annotation_collection:
            self.annotation_panel.update_annotations_display([])
            return
        
        all_annotations = self.annotation_collection.get_all_annotations()
        self.annotation_panel.update_annotations_display(all_annotations)

    def _toggle_theme(self, is_dark):
        """Toggle between light and dark themes."""
        if is_dark:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2e2e2e;
                    color: #e0e0e0;
                }
                QGroupBox {
                    border: 1px solid #555;
                    margin-top: 6px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 7px;
                    padding: 0 5px 0 5px;
                }
                QToolBar {
                    background-color: #3c3c3c;
                }
            """)
        else:
            self.setStyleSheet("") # Revert to default
