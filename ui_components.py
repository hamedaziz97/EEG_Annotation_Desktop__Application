"""
UI components module for channel settings and control panels, refactored for PyQt6.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel, QLineEdit,
    QDoubleSpinBox, QFormLayout, QMessageBox, QWidget, QCheckBox, QScrollArea,
    QPushButton, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem, QGridLayout,
    QSplitter, QFrame, QToolBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSlider, QStyle, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from typing import List, Callable, Optional, Dict

from EEG_Annotation_Desktop__Application.models import Annotation


class AnnotationDialog(QDialog):
    """Dialog for selecting or entering an annotation label."""

    def __init__(self, parent: QWidget, predefined_annotations: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Add Annotation")
        self.setMinimumWidth(350)

        self.result: Optional[str] = None

        layout = QVBoxLayout(self)

        label = QLabel("Select or enter an annotation label:")
        layout.addWidget(label)

        self.combobox = QComboBox(self)
        self.combobox.addItems(predefined_annotations)
        self.combobox.setEditable(True)
        self.combobox.setEditText("Seizure")  # Default value
        layout.addWidget(self.combobox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def accept(self):
        """Handle OK button click."""
        self.result = self.combobox.currentText().strip()
        if self.result:
            super().accept()
        else:
            QMessageBox.warning(self, "Input Required", "Please select or enter an annotation.")

    def get_result(self) -> Optional[str]:
        return self.result


class EditAnnotationDialog(QDialog):
    """Dialog for editing an annotation label and time range."""

    def __init__(self, parent: QWidget, annotation: Annotation, predefined_annotations: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Edit Annotation")
        self.setMinimumWidth(350)

        self.result: Optional[dict] = None
        self.annotation = annotation

        layout = QFormLayout(self)

        self.combo_var = QComboBox(self)
        self.combo_var.addItems(predefined_annotations)
        self.combo_var.setEditable(True)
        self.combo_var.setCurrentText(annotation.text)
        layout.addRow("Annotation Label:", self.combo_var)

        self.start_time_spinbox = QDoubleSpinBox(self)
        self.start_time_spinbox.setRange(0, 999999)
        self.start_time_spinbox.setValue(annotation.start_time)
        self.start_time_spinbox.setDecimals(2)
        layout.addRow("Start Time (s):", self.start_time_spinbox)

        self.end_time_spinbox = QDoubleSpinBox(self)
        self.end_time_spinbox.setRange(0, 999999)
        self.end_time_spinbox.setValue(annotation.end_time)
        self.end_time_spinbox.setDecimals(2)
        layout.addRow("End Time (s):", self.end_time_spinbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def accept(self):
        label = self.combo_var.currentText().strip()
        if not label:
            QMessageBox.warning(self, "Input Required", "Please enter an annotation label.")
            return

        start_time = self.start_time_spinbox.value()
        end_time = self.end_time_spinbox.value()

        if start_time >= end_time:
            QMessageBox.warning(self, "Invalid Input", "Start time must be less than end time.")
            return

        self.result = {
            "text": label,
            "start_time": start_time,
            "end_time": end_time
        }
        super().accept()

    def get_result(self) -> Optional[dict]:
        return self.result


class LeftSidebarWidget(QWidget):
    """Left sidebar with file, channel, filter, and display settings."""

    def __init__(self, on_load_file: Callable[[], None],
                 on_channel_selection_change: Callable[[List[int]], None],
                 on_time_scale_change: Callable[[float], None],
                 on_amplitude_scale_change: Callable[[float], None],
                 on_filter_change: Callable[[float, float, bool], None],
                 on_theme_change: Callable[[bool], None]):
        super().__init__()
        self.on_load_file = on_load_file
        self.on_channel_selection_change = on_channel_selection_change
        self.on_time_scale_change = on_time_scale_change
        self.on_amplitude_scale_change = on_amplitude_scale_change
        self.on_filter_change = on_filter_change
        self.on_theme_change = on_theme_change
        
        self.channel_names = []
        self.channel_checkboxes = []
        self.amplitude_values = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]

        self.setMinimumWidth(260)
        self.setMaximumWidth(320)

        self._create_widgets()

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.toolbox = QToolBox()
        main_layout.addWidget(self.toolbox)

        # --- A. File Section ---
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        
        load_btn = QPushButton("Load EEG File")
        load_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        load_btn.clicked.connect(lambda: self.on_load_file())
        file_layout.addWidget(load_btn)
        
        # File Info Labels
        self.lbl_filename = QLabel("Filename: -")
        self.lbl_filename.setWordWrap(True)
        self.lbl_duration = QLabel("Duration: -")
        self.lbl_sfreq = QLabel("Sampling Rate: -")
        self.lbl_channels = QLabel("Channels: -")
        
        info_box = QGroupBox("File Info")
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(self.lbl_filename)
        info_layout.addWidget(self.lbl_duration)
        info_layout.addWidget(self.lbl_sfreq)
        info_layout.addWidget(self.lbl_channels)
        file_layout.addWidget(info_box)
        
        file_layout.addStretch()
        self.toolbox.addItem(file_widget, "File")

        # --- B. Channel Settings ---
        channel_widget = QWidget()
        channel_layout = QVBoxLayout(channel_widget)
        
        btn_layout = QHBoxLayout()
        sel_all_btn = QPushButton("All")
        sel_all_btn.clicked.connect(self._select_all_channels)
        btn_layout.addWidget(sel_all_btn)
        
        sel_none_btn = QPushButton("None")
        sel_none_btn.clicked.connect(self._deselect_all_channels)
        btn_layout.addWidget(sel_none_btn)
        
        sel_std_btn = QPushButton("Standard")
        sel_std_btn.clicked.connect(self._select_standard_channels)
        btn_layout.addWidget(sel_std_btn)
        channel_layout.addLayout(btn_layout)

        self.channel_scroll = QScrollArea()
        self.channel_scroll.setWidgetResizable(True)
        self.channel_content = QWidget()
        self.channel_list_layout = QVBoxLayout(self.channel_content)
        self.channel_scroll.setWidget(self.channel_content)
        channel_layout.addWidget(self.channel_scroll)
        
        apply_channels_btn = QPushButton("Apply Channel Selection")
        apply_channels_btn.clicked.connect(self._apply_channel_selection)
        channel_layout.addWidget(apply_channels_btn)

        self.toolbox.addItem(channel_widget, "Channels")

        # --- C. Filter Settings ---
        filter_widget = QWidget()
        filter_layout = QFormLayout(filter_widget)
        
        self.lp_spin = QDoubleSpinBox()
        self.lp_spin.setRange(0, 500)
        self.lp_spin.setValue(0) # 0 means None
        self.lp_spin.setSpecialValueText("None")
        filter_layout.addRow("LP Filter (Hz):", self.lp_spin)
        
        self.hp_spin = QDoubleSpinBox()
        self.hp_spin.setRange(0, 100)
        self.hp_spin.setValue(0) # 0 means None
        self.hp_spin.setSpecialValueText("None")
        filter_layout.addRow("HP Filter (Hz):", self.hp_spin)
        
        self.notch_check = QCheckBox("Notch Filter (50/60Hz)")
        filter_layout.addRow(self.notch_check)
        
        btn_filter_layout = QHBoxLayout()
        apply_filter_btn = QPushButton("Apply")
        apply_filter_btn.clicked.connect(self._on_filter_change)
        btn_filter_layout.addWidget(apply_filter_btn)
        
        reset_filter_btn = QPushButton("Reset")
        reset_filter_btn.clicked.connect(self.reset_filters)
        btn_filter_layout.addWidget(reset_filter_btn)
        filter_layout.addRow(btn_filter_layout)
        
        self.toolbox.addItem(filter_widget, "Filters")

        # --- D. Display Settings ---
        display_widget = QWidget()
        display_layout = QFormLayout(display_widget)
        
        self.time_scale_combo = QComboBox()
        self.time_scale_combo.addItems(["5", "10", "20", "30", "60"])
        self.time_scale_combo.setCurrentText("20")
        self.time_scale_combo.currentTextChanged.connect(self._on_time_scale_change)
        display_layout.addRow("Time Window (s):", self.time_scale_combo)

        # Amplitude Slider
        self.amp_slider = QSlider(Qt.Orientation.Horizontal)
        self.amp_slider.setRange(0, len(self.amplitude_values) - 1)
        self.amp_slider.setValue(3) # Default to 1.0 (index 3)
        self.amp_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.amp_slider.setTickInterval(1)
        self.amp_slider.valueChanged.connect(self._on_amplitude_slider_change)
        
        self.lbl_amp_value = QLabel("1.0 µV")
        display_layout.addRow("Amplitude:", self.lbl_amp_value)
        display_layout.addRow(self.amp_slider)

        # Theme Toggle
        self.theme_check = QCheckBox("Dark Mode")
        self.theme_check.toggled.connect(self.on_theme_change)
        display_layout.addRow(self.theme_check)
        
        self.toolbox.addItem(display_widget, "Display")

    def update_file_info(self, filename: str, duration: float, sfreq: float, n_channels: int, channel_names: List[str]):
        """Update the file information labels and channel list."""
        self.lbl_filename.setText(f"Filename: {filename}")
        self.lbl_duration.setText(f"Duration: {duration:.1f} s")
        self.lbl_sfreq.setText(f"Sampling Rate: {sfreq} Hz")
        self.lbl_channels.setText(f"Channels: {n_channels}")
        
        self.channel_names = channel_names
        self._populate_channel_list()

    def _populate_channel_list(self):
        # Clear existing
        for i in reversed(range(self.channel_list_layout.count())): 
            self.channel_list_layout.itemAt(i).widget().setParent(None)
        self.channel_checkboxes = []
        
        for i, name in enumerate(self.channel_names):
            cb = QCheckBox(f"{i+1}. {name}")
            cb.setChecked(True)
            self.channel_checkboxes.append(cb)
            self.channel_list_layout.addWidget(cb)

    def _select_all_channels(self):
        for cb in self.channel_checkboxes:
            cb.setChecked(True)

    def _deselect_all_channels(self):
        for cb in self.channel_checkboxes:
            cb.setChecked(False)

    def _select_standard_channels(self):
        standard_channels = [
            'FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2',
            'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ',
            'T7', 'T8', 'P7', 'P8', 'FC1', 'FC2', 'CP1', 'CP2'
        ]
        standard_upper = [ch.upper() for ch in standard_channels]
        
        for i, name in enumerate(self.channel_names):
            self.channel_checkboxes[i].setChecked(name.upper() in standard_upper)

    def _apply_channel_selection(self):
        selected_indices = [i for i, cb in enumerate(self.channel_checkboxes) if cb.isChecked()]
        self.on_channel_selection_change(selected_indices)

    def _on_time_scale_change(self, value: str):
        try:
            self.on_time_scale_change(float(value))
        except (ValueError, TypeError):
            pass

    def _on_amplitude_slider_change(self, value: int):
        amp_val = self.amplitude_values[value]
        self.lbl_amp_value.setText(f"{amp_val} µV")
        self.on_amplitude_scale_change(amp_val)

    def _on_filter_change(self):
        lp = self.lp_spin.value()
        hp = self.hp_spin.value()
        notch = self.notch_check.isChecked()
        
        lp_val = None if lp == 0 else lp
        hp_val = None if hp == 0 else hp
        
        self.on_filter_change(lp_val, hp_val, notch)

    def reset_filters(self):
        """Reset filter settings to default."""
        self.lp_spin.setValue(0)
        self.hp_spin.setValue(0)
        self.notch_check.setChecked(False)
        self.on_filter_change(None, None, False)


class NavigationWidget(QWidget):
    """Navigation controls widget."""

    def __init__(self, on_navigation: Callable[[str], None]):
        super().__init__()
        self.on_navigation = on_navigation
        self.is_playing = False
        self._create_widgets()

    def _create_widgets(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # First / Start
        first_btn = QPushButton()
        first_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        first_btn.setToolTip("First / Start")
        first_btn.setFixedSize(36, 36)
        first_btn.clicked.connect(lambda: self.on_navigation("first"))
        layout.addWidget(first_btn)
        
        # Previous Window
        prev_btn = QPushButton()
        prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        prev_btn.setToolTip("Previous Window")
        prev_btn.setFixedSize(36, 36)
        prev_btn.clicked.connect(lambda: self.on_navigation("previous"))
        layout.addWidget(prev_btn)
        
        # Play / Pause
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.setToolTip("Play / Pause")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCheckable(True)
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)
        
        # Next Window
        next_btn = QPushButton()
        next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        next_btn.setToolTip("Next Window")
        next_btn.setFixedSize(36, 36)
        next_btn.clicked.connect(lambda: self.on_navigation("next"))
        layout.addWidget(next_btn)
        
        # Last / End
        last_btn = QPushButton()
        last_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        last_btn.setToolTip("Last / End")
        last_btn.setFixedSize(36, 36)
        last_btn.clicked.connect(lambda: self.on_navigation("last"))
        layout.addWidget(last_btn)
        
        layout.addStretch()

    def _toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.on_navigation("play")
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.on_navigation("pause")


class AnnotationPanel(QWidget):
    """Panel for annotation controls and display."""

    def __init__(self, on_add_annotation: Callable[[str], None],
                 on_delete_selected: Callable[[], None],
                 on_save_annotations: Callable[[], None],
                 on_load_annotations: Callable[[], None],
                 on_edit_annotation: Callable[[], None],
                 on_jump_to_annotation: Callable[[int], None]):
        super().__init__()
        self.on_add_annotation = on_add_annotation
        self.on_delete_selected = on_delete_selected
        self.on_save_annotations = on_save_annotations
        self.on_load_annotations = on_load_annotations
        self.on_edit_annotation = on_edit_annotation
        self.on_jump_to_annotation = on_jump_to_annotation
        
        self.setMinimumWidth(280)
        self.setMaximumWidth(320)

        self._create_widgets()

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- A. Annotation Actions ---
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        add_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Seizure", "Artifact", "Sleep", "Spike", "Custom"])
        add_layout.addWidget(self.type_combo)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add_click)
        add_layout.addWidget(add_btn)
        action_layout.addLayout(add_layout)
        
        main_layout.addWidget(action_group)

        # --- B. Annotation List (Table) ---
        list_group = QGroupBox("Annotation List")
        list_layout = QVBoxLayout(list_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Label", "Start", "Dur"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.on_edit_annotation)
        self.table.itemClicked.connect(self._on_table_item_clicked)
        
        list_layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.on_save_annotations)
        btn_layout.addWidget(save_btn)
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.on_load_annotations)
        btn_layout.addWidget(load_btn)
        
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self.on_delete_selected)
        btn_layout.addWidget(del_btn)
        
        list_layout.addLayout(btn_layout)
        main_layout.addWidget(list_group)

        # --- C. Filters ---
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout(filter_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by label...")
        self.search_input.textChanged.connect(self._filter_annotations)
        filter_layout.addRow("Search:", self.search_input)
        
        main_layout.addWidget(filter_group)

    def _on_add_click(self):
        # Trigger add with currently selected type
        # Note: Actual adding usually requires a time selection on plot
        pass

    def update_annotations_display(self, annotations: List[Annotation]):
        self.table.setRowCount(0)
        filter_text = self.search_input.text().lower()
        
        row = 0
        for i, ann in enumerate(annotations):
            if filter_text and filter_text not in ann.text.lower():
                continue
                
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ann.text))
            self.table.setItem(row, 1, QTableWidgetItem(f"{ann.start_time:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{ann.duration:.2f}"))
            
            # Store the original index or object if needed
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, i) 
            row += 1

    def get_selected_annotation_index(self) -> Optional[int]:
        current_row = self.table.currentRow()
        if current_row >= 0:
            # Retrieve original index from UserRole
            return self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        return None

    def _on_table_item_clicked(self, item):
        row = item.row()
        # Get original index
        idx = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.on_jump_to_annotation(idx)

    def _filter_annotations(self):
        # Triggered when search text changes
        # We need the full list of annotations to re-filter. 
        # For now, this is handled by the main window pushing updates.
        pass

    def is_annotation_mode_enabled(self) -> bool:
        # Simplified: always enabled or controlled by toolbar
        return True 
