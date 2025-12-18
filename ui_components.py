"""
UI components module for channel settings and control panels, refactored for PyQt6.
Professional UI update.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QDialogButtonBox, QLabel, QLineEdit,
    QDoubleSpinBox, QFormLayout, QMessageBox, QWidget, QCheckBox, QScrollArea,
    QPushButton, QHBoxLayout, QGroupBox, QListWidget, QListWidgetItem, QGridLayout,
    QSplitter, QFrame, QToolBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSlider, QStyle, QAbstractItemView, QSizePolicy, QSpacerItem
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
        self._setup_ui(predefined_annotations)

    def _setup_ui(self, predefined_annotations):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        label = QLabel("Select or enter an annotation label:")
        layout.addWidget(label)

        self.combobox = QComboBox(self)
        self.combobox.addItems(predefined_annotations)
        self.combobox.setEditable(True)
        self.combobox.setEditText("Seizure")
        layout.addWidget(self.combobox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def accept(self):
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
        self._setup_ui(predefined_annotations)

    def _setup_ui(self, predefined_annotations):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.combo_var = QComboBox(self)
        self.combo_var.addItems(predefined_annotations)
        self.combo_var.setEditable(True)
        self.combo_var.setCurrentText(self.annotation.text)
        layout.addRow("Label:", self.combo_var)

        self.start_time_spinbox = QDoubleSpinBox(self)
        self.start_time_spinbox.setRange(0, 999999)
        self.start_time_spinbox.setValue(self.annotation.start_time)
        self.start_time_spinbox.setDecimals(3)
        layout.addRow("Start (s):", self.start_time_spinbox)

        self.end_time_spinbox = QDoubleSpinBox(self)
        self.end_time_spinbox.setRange(0, 999999)
        self.end_time_spinbox.setValue(self.annotation.end_time)
        self.end_time_spinbox.setDecimals(3)
        layout.addRow("End (s):", self.end_time_spinbox)

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


class ChannelSettingsDialog(QDialog):
    """Dialog for channel selection settings."""
    # Kept for compatibility if needed, though LeftSidebarWidget now handles this inline.
    def __init__(self, parent: QWidget, channel_names: List[str],
                 selected_channels: List[int],
                 on_apply: Callable[[List[int]], None]):
        super().__init__(parent)
        self.channel_names = channel_names
        self.selected_channels = selected_channels
        self.on_apply = on_apply
        self.setWindowTitle("Channel Selection")
        self.setGeometry(0, 0, 400, 600)
        self.channel_checkboxes: List[QCheckBox] = []
        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        layout = QVBoxLayout(self)
        
        info = QLabel(f"Select channels ({len(self.channel_names)} total):")
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        for text, slot in [("All", self._select_all), ("None", self._deselect_all), ("Standard", self._select_standard_eeg)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.scroll_layout = QVBoxLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        for i, name in enumerate(self.channel_names):
            cb = QCheckBox(f"{i + 1}. {name}")
            cb.setChecked(i in self.selected_channels if self.selected_channels else True)
            self.channel_checkboxes.append(cb)
            self.scroll_layout.addWidget(cb)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _center_window(self):
        if self.parent():
            geo = self.parent().frameGeometry()
            self.move(geo.center() - self.rect().center())

    def _select_all(self):
        for cb in self.channel_checkboxes: cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.channel_checkboxes: cb.setChecked(False)

    def _select_standard_eeg(self):
        std = ['FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ']
        self._deselect_all()
        for i, name in enumerate(self.channel_names):
            if name.upper() in std: self.channel_checkboxes[i].setChecked(True)

    def accept(self):
        selected = [i for i, cb in enumerate(self.channel_checkboxes) if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Warning", "Select at least one channel.")
            return
        self.on_apply(selected)
        super().accept()


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

        self.setMinimumWidth(280)
        self.setMaximumWidth(320)
        self._create_widgets()

    def _create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbox = QToolBox()
        layout.addWidget(self.toolbox)

        # --- A. File / Dataset Section ---
        file_page = QWidget()
        file_layout = QVBoxLayout(file_page)
        file_layout.setSpacing(15)
        file_layout.setContentsMargins(10, 15, 10, 15)
        
        load_btn = QPushButton("Load EEG File")
        load_btn.setObjectName("primaryButton")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.setMinimumHeight(32)
        load_btn.clicked.connect(lambda: self.on_load_file())
        file_layout.addWidget(load_btn)
        
        # File Info Card
        info_frame = QFrame()
        info_frame.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        
        self.lbl_filename = self._create_info_label("Filename", "-")
        self.lbl_duration = self._create_info_label("Duration", "-")
        self.lbl_sfreq = self._create_info_label("Sampling Rate", "-")
        self.lbl_channels = self._create_info_label("Channels", "-")
        
        info_layout.addWidget(self.lbl_filename)
        info_layout.addWidget(self.lbl_duration)
        info_layout.addWidget(self.lbl_sfreq)
        info_layout.addWidget(self.lbl_channels)
        file_layout.addWidget(info_frame)
        
        file_layout.addStretch()
        self.toolbox.addItem(file_page, "Dataset")

        # --- B. Channel Settings ---
        channel_page = QWidget()
        channel_layout = QVBoxLayout(channel_page)
        channel_layout.setContentsMargins(10, 10, 10, 10)
        
        btn_layout = QHBoxLayout()
        for text, slot in [("All", self._select_all_channels), ("None", self._deselect_all_channels), ("Std", self._select_standard_channels)]:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        channel_layout.addLayout(btn_layout)

        self.channel_scroll = QScrollArea()
        self.channel_scroll.setWidgetResizable(True)
        self.channel_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.channel_content = QWidget()
        self.channel_list_layout = QVBoxLayout(self.channel_content)
        self.channel_list_layout.setSpacing(2)
        self.channel_scroll.setWidget(self.channel_content)
        channel_layout.addWidget(self.channel_scroll)
        
        apply_channels_btn = QPushButton("Apply Selection")
        apply_channels_btn.setObjectName("primaryButton")
        apply_channels_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_channels_btn.clicked.connect(self._apply_channel_selection)
        channel_layout.addWidget(apply_channels_btn)

        self.toolbox.addItem(channel_page, "Channels")

        # --- C. Filter Settings ---
        filter_page = QWidget()
        filter_layout = QFormLayout(filter_page)
        filter_layout.setContentsMargins(10, 15, 10, 15)
        filter_layout.setSpacing(10)
        
        self.lp_spin = QDoubleSpinBox()
        self.lp_spin.setRange(0, 500)
        self.lp_spin.setSpecialValueText("None")
        filter_layout.addRow("Lowpass (Hz):", self.lp_spin)
        
        self.hp_spin = QDoubleSpinBox()
        self.hp_spin.setRange(0, 100)
        self.hp_spin.setSpecialValueText("None")
        filter_layout.addRow("Highpass (Hz):", self.hp_spin)
        
        self.notch_check = QCheckBox("Notch (50/60Hz)")
        filter_layout.addRow("", self.notch_check)
        
        btn_filter_layout = QHBoxLayout()
        apply_filter_btn = QPushButton("Apply")
        apply_filter_btn.setObjectName("primaryButton")
        apply_filter_btn.clicked.connect(self._on_filter_change)
        btn_filter_layout.addWidget(apply_filter_btn)
        
        reset_filter_btn = QPushButton("Reset")
        reset_filter_btn.clicked.connect(self.reset_filters)
        btn_filter_layout.addWidget(reset_filter_btn)
        filter_layout.addRow(btn_filter_layout)
        
        self.toolbox.addItem(filter_page, "Filters")

        # --- D. Display Settings ---
        display_page = QWidget()
        display_layout = QFormLayout(display_page)
        display_layout.setContentsMargins(10, 15, 10, 15)
        display_layout.setSpacing(10)
        
        self.time_scale_combo = QComboBox()
        self.time_scale_combo.addItems(["5", "10", "20", "30", "60"])
        self.time_scale_combo.setCurrentText("20")
        self.time_scale_combo.currentTextChanged.connect(self._on_time_scale_change)
        display_layout.addRow("Window (s):", self.time_scale_combo)

        self.amp_slider = QSlider(Qt.Orientation.Horizontal)
        self.amp_slider.setRange(0, len(self.amplitude_values) - 1)
        self.amp_slider.setValue(3)
        self.amp_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.amp_slider.setTickInterval(1)
        self.amp_slider.valueChanged.connect(self._on_amplitude_slider_change)
        
        self.lbl_amp_value = QLabel("1.0 µV")
        self.lbl_amp_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        display_layout.addRow("Amplitude:", self.lbl_amp_value)
        display_layout.addRow(self.amp_slider)

        self.theme_check = QCheckBox("Dark Mode")
        self.theme_check.toggled.connect(self.on_theme_change)
        display_layout.addRow(self.theme_check)
        
        self.toolbox.addItem(display_page, "Display")

    def _create_info_label(self, title, value):
        lbl = QLabel(f"<b>{title}:</b> {value}")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        return lbl

    def update_file_info(self, filename: str, duration: float, sfreq: float, n_channels: int, channel_names: List[str]):
        self.lbl_filename.setText(f"<b>File:</b> {filename}")
        self.lbl_duration.setText(f"<b>Duration:</b> {duration:.1f} s")
        self.lbl_sfreq.setText(f"<b>Rate:</b> {sfreq} Hz")
        self.lbl_channels.setText(f"<b>Channels:</b> {n_channels}")
        self.channel_names = channel_names
        self._populate_channel_list()

    def _populate_channel_list(self):
        while self.channel_list_layout.count():
            item = self.channel_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.channel_checkboxes = []
        for i, name in enumerate(self.channel_names):
            cb = QCheckBox(f"{i+1}. {name}")
            cb.setChecked(True)
            self.channel_checkboxes.append(cb)
            self.channel_list_layout.addWidget(cb)

    def _select_all_channels(self):
        for cb in self.channel_checkboxes: cb.setChecked(True)

    def _deselect_all_channels(self):
        for cb in self.channel_checkboxes: cb.setChecked(False)

    def _select_standard_channels(self):
        std = ['FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ', 'T7', 'T8', 'P7', 'P8', 'FC1', 'FC2', 'CP1', 'CP2']
        for i, name in enumerate(self.channel_names):
            self.channel_checkboxes[i].setChecked(name.upper() in std)

    def _apply_channel_selection(self):
        self.on_channel_selection_change([i for i, cb in enumerate(self.channel_checkboxes) if cb.isChecked()])

    def _on_time_scale_change(self, value: str):
        try: self.on_time_scale_change(float(value))
        except: pass

    def _on_amplitude_slider_change(self, value: int):
        val = self.amplitude_values[value]
        self.lbl_amp_value.setText(f"{val} µV")
        self.on_amplitude_scale_change(val)

    def _on_filter_change(self):
        lp = self.lp_spin.value()
        hp = self.hp_spin.value()
        self.on_filter_change(None if lp == 0 else lp, None if hp == 0 else hp, self.notch_check.isChecked())

    def reset_filters(self):
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
        layout.setSpacing(8)
        
        for icon, tooltip, action in [
            (QStyle.StandardPixmap.SP_MediaSkipBackward, "First", "first"),
            (QStyle.StandardPixmap.SP_MediaSeekBackward, "Previous Window", "previous")
        ]:
            btn = QPushButton()
            btn.setIcon(self.style().standardIcon(icon))
            btn.setToolTip(tooltip)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda _, a=action: self.on_navigation(a))
            layout.addWidget(btn)
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.setToolTip("Play / Pause")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setCheckable(True)
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)
        
        for icon, tooltip, action in [
            (QStyle.StandardPixmap.SP_MediaSeekForward, "Next Window", "next"),
            (QStyle.StandardPixmap.SP_MediaSkipForward, "Last", "last")
        ]:
            btn = QPushButton()
            btn.setIcon(self.style().standardIcon(icon))
            btn.setToolTip(tooltip)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda _, a=action: self.on_navigation(a))
            layout.addWidget(btn)
        
        layout.addStretch()

    def _toggle_play(self):
        self.is_playing = not self.is_playing
        icon = QStyle.StandardPixmap.SP_MediaPause if self.is_playing else QStyle.StandardPixmap.SP_MediaPlay
        self.play_btn.setIcon(self.style().standardIcon(icon))
        self.on_navigation("play" if self.is_playing else "pause")


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Header
        header = QLabel("Annotations")
        header.setObjectName("panelHeader")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)

        # A. Actions
        action_group = QGroupBox("Add Annotation")
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(10, 15, 10, 10)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Seizure", "Artifact", "Sleep", "Spike", "Custom"])
        action_layout.addWidget(self.type_combo, 1)
        
        add_btn = QPushButton("Add")
        add_btn.setObjectName("primaryButton")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_add_click)
        action_layout.addWidget(add_btn)
        layout.addWidget(action_group)

        # B. Filter & List
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter annotations...")
        self.search_input.textChanged.connect(self._filter_annotations)
        layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Label", "Start", "Dur"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.on_edit_annotation)
        self.table.itemClicked.connect(self._on_table_item_clicked)
        layout.addWidget(self.table)

        # C. File Operations
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.on_save_annotations)
        btn_layout.addWidget(save_btn)
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.on_load_annotations)
        btn_layout.addWidget(load_btn)
        
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("dangerButton")
        del_btn.clicked.connect(self.on_delete_selected)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)

    def _on_add_click(self):
        pass

    def update_annotations_display(self, annotations: List[Annotation]):
        self.table.setRowCount(0)
        filter_text = self.search_input.text().lower()
        row = 0
        for i, ann in enumerate(annotations):
            if filter_text and filter_text not in ann.text.lower(): continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ann.text))
            self.table.setItem(row, 1, QTableWidgetItem(f"{ann.start_time:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{ann.duration:.2f}"))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, i)
            row += 1

    def get_selected_annotation_index(self) -> Optional[int]:
        row = self.table.currentRow()
        return self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if row >= 0 else None

    def _on_table_item_clicked(self, item):
        idx = self.table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        self.on_jump_to_annotation(idx)

    def _filter_annotations(self):
        pass

    def is_annotation_mode_enabled(self) -> bool:
        return True
