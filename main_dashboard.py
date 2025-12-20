"""
Main dashboard class that orchestrates all components of the EEG annotation tool.
Professional UI update.
"""

import os
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMessageBox, QSplitter, QStatusBar, QLabel,
    QToolBar, QComboBox, QToolButton, QSizePolicy
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

# --- Professional QSS Stylesheet ---
STYLESHEET = """
    QMainWindow {
        background-color: #f0f2f5;
    }
    QToolBar {
        background-color: #ffffff;
        border-bottom: 1px solid #dcdfe6;
        padding: 4px;
        spacing: 8px;
    }
    QToolBar QToolButton, QToolBar QPushButton {
        background-color: transparent;
        border: 1px solid transparent;
        padding: 6px;
        border-radius: 4px;
    }
    QToolBar QToolButton:hover, QToolBar QPushButton:hover {
        background-color: #e9ecef;
        border: 1px solid #dcdfe6;
    }
    QToolBar QToolButton:pressed, QToolBar QPushButton:pressed {
        background-color: #dee2e6;
    }
    QToolBar QToolButton:checked {
        background-color: #cfe2ff;
        border: 1px solid #9ec5fe;
    }
    QSplitter::handle {
        background-color: #e9ecef;
    }
    QSplitter::handle:horizontal {
        width: 2px;
    }
    QStatusBar {
        background-color: #ffffff;
        border-top: 1px solid #dcdfe6;
    }
    QStatusBar::item {
        border: none;
    }
    /* Left & Right Sidebars */
    #leftSidebar, #rightSidebar {
        background-color: #ffffff;
        border: none;
    }
    QToolBox {
        background-color: #ffffff;
    }
    QToolBox::tab {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        color: #495057;
        font-weight: bold;
        font-size: 13px;
        padding-left: 10px;
        min-height: 32px;
        margin-top: 2px;
    }
    QToolBox::tab:selected {
        background-color: #e9ecef;
        color: #212529;
        border: 1px solid #dcdfe6;
    }
    QGroupBox {
        font-weight: bold;
        color: #343a40;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        margin-top: 8px;
        padding: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
        background-color: #ffffff;
    }
    #infoCard {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 4px;
        padding: 8px;
    }
    QPushButton {
        background-color: #ffffff;
        border: 1px solid #ced4da;
        padding: 6px 12px;
        border-radius: 4px;
        color: #212529;
    }
    QPushButton:hover {
        background-color: #f8f9fa;
    }
    QPushButton:pressed {
        background-color: #e9ecef;
    }
    QPushButton#primaryButton {
        background-color: #0d6efd;
        color: white;
        border: none;
    }
    QPushButton#primaryButton:hover {
        background-color: #0b5ed7;
    }
    QPushButton#dangerButton {
        background-color: #dc3545;
        color: white;
        border: none;
    }
    QPushButton#dangerButton:hover {
        background-color: #bb2d3b;
    }
    QTableWidget {
        border: 1px solid #e0e0e0;
        gridline-color: #e9ecef;
        background-color: #ffffff;
    }
    QHeaderView::section {
        background-color: #f8f9fa;
        padding: 4px;
        border: none;
        border-bottom: 1px solid #dcdfe6;
        font-weight: bold;
    }
    QTableWidget::item:selected {
        background-color: #cfe2ff;
        color: #000;
    }
    QLineEdit, QComboBox, QDoubleSpinBox {
        border: 1px solid #ced4da;
        padding: 5px;
        border-radius: 4px;
    }
    QSlider::groove:horizontal {
        border: 1px solid #ccc;
        height: 8px;
        background: #f0f0f0;
        margin: 2px 0;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        background: #0d6efd;
        border: 1px solid #0d6efd;
        width: 16px;
        margin: -4px 0;
        border-radius: 8px;
    }
"""

class EEGDashboard(QMainWindow):
    """Main dashboard class that coordinates all components."""

    def __init__(self):
        """Initialize the EEG dashboard."""
        super().__init__()
        self.setWindowTitle("EEG Annotation Tool")
        self.setGeometry(100, 100, 1800, 1000)
        self.setStyleSheet(STYLESHEET)

        # Data
        self.eeg_data = None
        self.display_settings = DisplaySettings()
        self.annotation_collection = None
        self.current_window_start = 0

        # Playback
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.playback_speed = 1.0

        # Components
        self.annotation_manager = AnnotationManager(self, self._on_selection_change)
        self._setup_ui()
        self._create_toolbar()

    def _setup_ui(self):
        """Set up the main UI layout."""
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
        self.left_sidebar.setObjectName("leftSidebar")
        main_splitter.addWidget(self.left_sidebar)

        # Center Panel
        self.plotter = EEGPlotter()
        self.plotter.set_mouse_callbacks(self._on_mouse_press, self._on_mouse_release, self._on_mouse_move, self._on_channel_selection)
        main_splitter.addWidget(self.plotter)

        # Right Sidebar
        self.annotation_panel = AnnotationPanel(
            on_add_annotation=self._on_add_annotation,
            on_delete_selected=self._on_delete_selected_annotation,
            on_save_annotations=self._on_save_annotations,
            on_load_annotations=self._on_load_annotations,
            on_edit_annotation=self._on_edit_annotation,
            on_jump_to_annotation=self._jump_to_annotation
        )
        self.annotation_panel.setObjectName("rightSidebar")
        main_splitter.addWidget(self.annotation_panel)

        main_splitter.setSizes([300, 1200, 300])
        main_splitter.setStretchFactor(1, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.window_info_label = QLabel("No file loaded.")
        self.status_bar.addPermanentWidget(self.window_info_label)

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(22, 22))
        self.addToolBar(toolbar)

        # Logo
        lbl_logo = QLabel(" EEG-Annotator")
        lbl_logo.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50;")
        toolbar.addWidget(lbl_logo)
        toolbar.addSeparator()

        # File
        action_open = self._create_action("document-open", "Open EEG File", self.load_eeg_file)
        toolbar.addAction(action_open)
        toolbar.addSeparator()

        # Transport
        self.navigation_widget = NavigationWidget(self._on_navigation)
        toolbar.addWidget(self.navigation_widget)
        
        speed_combo = QComboBox()
        speed_combo.addItems(["0.5x", "1x", "2x"])
        speed_combo.setCurrentIndex(1)
        speed_combo.currentTextChanged.connect(self._set_playback_speed)
        toolbar.addWidget(speed_combo)
        toolbar.addSeparator()

        # Annotation Mode
        self.action_anno_mode = self._create_action("edit-select", "Annotation Mode", checkable=True)
        toolbar.addAction(self.action_anno_mode)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Utilities
        action_zoom_in = self._create_action("zoom-in", "Zoom In", lambda: self._zoom(1.2))
        action_zoom_out = self._create_action("zoom-out", "Zoom Out", lambda: self._zoom(0.8))
        toolbar.addAction(action_zoom_in)
        toolbar.addAction(action_zoom_out)

    def _create_action(self, icon_name, tooltip, callback=None, checkable=False):
        action = QAction(QIcon.fromTheme(icon_name), tooltip, self)
        if callback: action.triggered.connect(callback)
        if checkable: action.setCheckable(True)
        return action

    def _on_time_scale_change(self, val): self.display_settings.time_scale = val; self._update_all()
    def _on_amplitude_scale_change(self, val): self.display_settings.amplitude_scale = val; self._update_all()
    def _on_filter_change(self, lp, hp, notch):
        self.display_settings.lowpass_filter = lp
        self.display_settings.highpass_filter = hp
        self._update_all()

    def _on_navigation(self, action):
        if not self.eeg_data: return
        ts = self.display_settings.time_scale
        if action == "next": self.current_window_start += ts
        elif action == "previous": self.current_window_start -= ts
        elif action == "first": self.current_window_start = 0
        elif action == "last": self.current_window_start = self.eeg_data.total_duration - ts
        elif action == "play": self.playback_timer.start(int(1000 / self.playback_speed))
        elif action == "pause": self.playback_timer.stop()
        self.current_window_start = max(0, min(self.current_window_start, self.eeg_data.total_duration - ts))
        self._update_all()

    def _advance_playback(self):
        if not self.eeg_data or self.current_window_start + self.display_settings.time_scale >= self.eeg_data.total_duration:
            self.playback_timer.stop()
            self.navigation_widget.play_btn.setChecked(False)
            self.navigation_widget._toggle_play()
        else:
            self.current_window_start += 1
            self._update_all()

    def _on_channel_selection_apply(self, sel): self.display_settings.selected_channels = sel; self._update_all()
    def _on_channel_selection(self, sel): self.annotation_manager.set_selected_channels(sel); self._update_all()
    def _on_mouse_press(self, e): self.annotation_manager.handle_mouse_press(e, self.action_anno_mode.isChecked())
    def _on_mouse_move(self, e): self.annotation_manager.handle_mouse_move(e, self.action_anno_mode.isChecked())
    def _on_mouse_release(self, e): self.annotation_manager.handle_mouse_release(e, self.action_anno_mode.isChecked())
    def _on_selection_change(self): self._update_all()
    def _on_add_annotation(self, text): pass

    def _on_delete_selected_annotation(self):
        indices = self.annotation_panel.get_selected_annotation_indices()
        if not indices:
            return QMessageBox.warning(self, "Warning", "Select at least one annotation to delete.")
        
        all_annotations = self.annotation_collection.get_all_annotations()
        
        # Collect annotations to delete
        to_delete = []
        for idx in indices:
            if idx < len(all_annotations):
                to_delete.append(all_annotations[idx])
        
        # Remove them
        for ann in to_delete:
            self.annotation_collection.remove_annotation(ann)
            
        self._update_all()

    def _on_edit_annotation(self, row, col):
        idx = self.annotation_panel.get_selected_annotation_index()
        if idx is None: return
        ann = self.annotation_collection.get_all_annotations()[idx]
        dialog = EditAnnotationDialog(self, ann, self.annotation_manager.predefined_annotations)
        if dialog.exec() and dialog.result:
            ann.text = dialog.result["text"]
            ann.start_time = dialog.result["start_time"]
            ann.end_time = dialog.result["end_time"]
            self._update_all()

    def _on_save_annotations(self):
        if not self.annotation_collection or not self.annotation_collection.annotations:
            return QMessageBox.warning(self, "Warning", "No annotations to save.")
        AnnotationFileHandler.save_annotations(self, self.annotation_collection)

    def _on_load_annotations(self):
        coll = AnnotationFileHandler.load_annotations(self)
        if coll:
            self.annotation_collection = coll
            self.annotation_manager.set_annotation_collection(coll)
            self._update_all()

    def _jump_to_annotation(self, idx):
        if not self.annotation_collection or not self.eeg_data: return
        ann = self.annotation_collection.get_all_annotations()[idx]
        self.current_window_start = ann.start_time
        self._update_all()

    def load_eeg_file(self, file_path=None):
        if file_path is None: file_path = EEGFileHandler.get_file_dialog_path(self)
        if not file_path: return

        eeg_data = EEGFileHandler.load_eeg_file(file_path)
        if not eeg_data: return QMessageBox.critical(self, "Error", "Failed to load EEG file.")

        self.eeg_data = eeg_data
        self.display_settings.selected_channels = list(range(len(eeg_data.channel_names)))
        self.current_window_start = 0
        self.left_sidebar.reset_filters()

        self.annotation_collection = AnnotationCollection.create_empty(os.path.basename(file_path), self.display_settings.time_scale, eeg_data.sampling_freq)
        self.annotation_manager.set_annotation_collection(self.annotation_collection)
        self.annotation_manager.clear_selection()
        
        self.left_sidebar.update_file_info(os.path.basename(file_path), eeg_data.total_duration, eeg_data.sampling_freq, len(eeg_data.channel_names), eeg_data.channel_names)
        self._update_all()
        self.status_bar.showMessage(f"Loaded {os.path.basename(file_path)}", 5000)

    def _update_all(self):
        if not self.eeg_data: return
        self._update_plot()
        self._update_window_info()
        self._update_annotations_display()

    def _update_plot(self):
        annotations = self.annotation_collection.get_all_annotations() if self.annotation_collection else []
        self.plotter.plot_eeg_data(self.eeg_data, self.display_settings, self.current_window_start, self.annotation_manager.selection_state, annotations)

    def _update_window_info(self):
        total_windows = int(np.ceil(self.eeg_data.total_duration / self.display_settings.time_scale))
        current_window = int(self.current_window_start / self.display_settings.time_scale) + 1
        self.window_info_label.setText(f"Window {current_window}/{total_windows} ({self.current_window_start:.1f}s - {self.current_window_start + self.display_settings.time_scale:.1f}s)")

    def _update_annotations_display(self):
        annotations = self.annotation_collection.get_all_annotations() if self.annotation_collection else []
        self.annotation_panel.update_annotations_display(annotations)

    def _set_playback_speed(self, text):
        self.playback_speed = float(text.replace('x', ''))
        if self.playback_timer.isActive():
            self.playback_timer.setInterval(int(1000 / self.playback_speed))

    def _zoom(self, factor):
        current_val = self.left_sidebar.amp_slider.value()
        new_val = max(0, min(len(self.left_sidebar.amplitude_values) - 1, int(current_val * factor)))
        self.left_sidebar.amp_slider.setValue(new_val)

    def _toggle_theme(self, is_dark):
        dark_stylesheet = STYLESHEET.replace("#f0f2f5", "#2b2b2b").replace("#ffffff", "#3c3c3c").replace("#2c3e50", "#d0d0d0").replace("#495057", "#b0b0b0").replace("#212529", "#e0e0e0").replace("#e9ecef", "#454545").replace("#dcdfe6", "#555555")
        self.setStyleSheet(dark_stylesheet if is_dark else STYLESHEET)
