"""
UI components module for channel settings and control panels.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Callable, Optional

from SourceLocalization.scripts.dashboard.models import DisplaySettings


class AnnotationDialog(tk.Toplevel):
    """Dialog for selecting or entering an annotation label."""

    def __init__(self, parent, predefined_annotations: List[str]):
        """
        Initialize the annotation dialog.

        Args:
            parent: The parent window.
            predefined_annotations: A list of common annotations to suggest.
        """
        super().__init__(parent)
        self.parent = parent
        self.result: Optional[str] = None

        self.title("Add Annotation")
        self.geometry("350x130")
        self.resizable(False, False)

        # Make window modal
        self.transient(parent)
        self.grab_set()

        self._create_widgets(predefined_annotations)
        self._center_window()

        # Bind Enter/Escape keys
        self.bind("<Return>", self._on_ok)
        self.bind("<Escape>", self._on_cancel)

        # Set focus and wait for user interaction
        self.combobox.focus_set()
        self.wait_window(self)

    def _create_widgets(self, predefined_annotations: List[str]):
        """Create the dialog's widgets."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Select or enter an annotation label:").pack(anchor=tk.W, pady=(0, 5))

        self.combo_var = tk.StringVar()
        self.combobox = ttk.Combobox(main_frame, textvariable=self.combo_var, values=predefined_annotations)
        self.combobox.pack(fill=tk.X, expand=True, pady=(0, 15))
        self.combobox.set("Seizure") # Set default value here

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="OK", command=self._on_ok, style="Accent.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT)

    def _center_window(self):
        """Center the dialog on the parent window."""
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_ok(self, event=None):
        """Handle OK button click or Enter key press."""
        self.result = self.combo_var.get().strip()
        if self.result:
            self.destroy()
        else:
            messagebox.showwarning("Input Required", "Please select or enter an annotation.", parent=self)

    def _on_cancel(self, event=None):
        """Handle Cancel button click or Escape key press."""
        self.result = None
        self.destroy()


class ChannelSettingsDialog:
    """Dialog for channel selection settings."""

    def __init__(self, parent, channel_names: List[str],
                 selected_channels: List[int],
                 on_apply: Callable[[List[int]], None]):
        """
        Initialize channel settings dialog.

        Args:
            parent: Parent window
            channel_names: List of all available channel names
            selected_channels: Currently selected channel indices
            on_apply: Callback function when apply is clicked
        """
        self.parent = parent
        self.channel_names = channel_names
        self.selected_channels = selected_channels
        self.on_apply = on_apply

        self.window = None
        self.channel_vars = []

    def show(self):
        """Show the channel settings dialog."""
        if not self.channel_names:
            messagebox.showwarning("Warning", "Please load an EEG file first")
            return

        # Create channel selection window
        self.window = tk.Toplevel(self.parent)
        self.window.title("Channel Selection Settings")
        self.window.geometry("420x560")
        self.window.resizable(True, True)

        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()

        self._create_widgets()
        self._center_window()

    def _create_widgets(self):
        """Create dialog widgets."""
        # Create main frame with scrollbar
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Info label
        info_label = ttk.Label(main_frame,
                              text=f"Select channels to display ({len(self.channel_names)} total channels):")
        info_label.pack(anchor=tk.W, pady=(0, 10))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(button_frame, text="Select All",
                  command=self._select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Deselect All",
                  command=self._deselect_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Select Standard EEG",
                  command=self._select_standard_eeg).pack(side=tk.LEFT)

        # Create scrollable frame for channel checkboxes with reliable scrolling
        channel_frame = ttk.Frame(main_frame)
        channel_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(channel_frame, highlightthickness=0)
        v_scroll = ttk.Scrollbar(channel_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Make inner frame resize with canvas width
        def _configure_inner(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = event.width
            canvas.itemconfig(inner_window, width=canvas_width)
        scrollable_frame.bind("<Configure>", _configure_inner)

        inner_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # Create channel variables and checkboxes
        self.channel_vars = []
        for i, channel_name in enumerate(self.channel_names):
            var = tk.BooleanVar()
            var.set(i in self.selected_channels if self.selected_channels else True)
            self.channel_vars.append(var)

            checkbox = ttk.Checkbutton(scrollable_frame, text=f"{i + 1:2d}. {channel_name}",
                                       variable=var)
            checkbox.pack(fill=tk.X, anchor=tk.W, padx=5, pady=2)

        # Mouse wheel scrolling (Windows/Mac/Linux)
        def _on_mousewheel(event):
            delta = 0
            if event.num == 4:  # Linux scroll up
                delta = -1
            elif event.num == 5:  # Linux scroll down
                delta = 1
            else:
                delta = -1 * int(event.delta / 120)  # Windows/Mac
            canvas.yview_scroll(delta, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)

        # OK and Cancel buttons
        button_frame2 = ttk.Frame(main_frame)
        button_frame2.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(button_frame2, text="Apply",
                  command=self._apply_selection).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame2, text="Cancel",
                  command=self._cancel).pack(side=tk.RIGHT)

    def _center_window(self):
        """Center the window on screen."""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def _select_all(self):
        """Select all channels."""
        for var in self.channel_vars:
            var.set(True)

    def _deselect_all(self):
        """Deselect all channels."""
        for var in self.channel_vars:
            var.set(False)

    def _select_standard_eeg(self):
        """Select standard EEG channels (10-20 system)."""
        standard_channels = [
            'FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2',
            'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ',
            'T7', 'T8', 'P7', 'P8', 'FC1', 'FC2', 'CP1', 'CP2'
        ]

        self._deselect_all()
        for i, channel_name in enumerate(self.channel_names):
            if channel_name.upper() in [ch.upper() for ch in standard_channels]:
                self.channel_vars[i].set(True)

    def _apply_selection(self):
        """Apply the selected channels."""
        new_selected_channels = []
        for i, var in enumerate(self.channel_vars):
            if var.get():
                new_selected_channels.append(i)

        if not new_selected_channels:
            messagebox.showwarning("Warning", "Please select at least one channel")
            return

        self.on_apply(new_selected_channels)
        self.window.destroy()

    def _cancel(self):
        """Cancel channel selection."""
        self.window.destroy()


class ControlPanel:
    """Control panel with display settings and navigation controls."""

    def __init__(self, parent, on_time_scale_change: Callable[[float], None],
                 on_amplitude_scale_change: Callable[[float], None],
                 on_filter_change: Callable[[float, float], None],
                 on_navigation: Callable[[str], None],
                 on_channel_settings: Callable[[], None],
                 on_load_file: Callable[[], None] = None):
        """
        Initialize control panel.
        """
        self.parent = parent
        self.on_time_scale_change = on_time_scale_change
        self.on_amplitude_scale_change = on_amplitude_scale_change
        self.on_filter_change = on_filter_change
        self.on_navigation = on_navigation
        self.on_channel_settings = on_channel_settings
        self.on_load_file = on_load_file

        self._create_widgets()

    def _create_widgets(self):
        """Create control panel widgets."""
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Group file and channel buttons ---
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(side=tk.LEFT, padx=(0, 10), fill='y')
        ttk.Button(file_frame, text="Load EEG File",
                  command=self._on_load_file).pack(pady=(0, 2), fill='x')
        ttk.Button(file_frame, text="Channel Settings",
                  command=self.on_channel_settings).pack(pady=(2, 0), fill='x')

        # --- Display settings ---
        scale_frame = ttk.LabelFrame(control_frame, text="Display Settings")
        scale_frame.pack(side=tk.LEFT, padx=(0, 10), fill='y')

        # Time scale
        ttk.Label(scale_frame, text="Time Scale (s):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.time_scale_var = tk.StringVar(value="20")
        time_scale_combo = ttk.Combobox(scale_frame, textvariable=self.time_scale_var,
                                       values=["5", "10", "20", "30", "60"], width=8)
        time_scale_combo.grid(row=0, column=1, padx=5, pady=2)
        time_scale_combo.bind('<<ComboboxSelected>>', self._on_time_scale_change)

        # Amplitude scale
        ttk.Label(scale_frame, text="Amplitude:").grid(row=0, column=2, sticky=tk.W, padx=(10, 5), pady=2)
        self.amplitude_scale_var = tk.StringVar(value="1.0")
        amplitude_scale_combo = ttk.Combobox(scale_frame, textvariable=self.amplitude_scale_var,
                                           values=["0.1", "0.2", "0.5", "1.0", "2.0", "5.0", "10.0", "20.0", "50.0"],
                                           width=8)
        amplitude_scale_combo.grid(row=0, column=3, padx=5, pady=2)
        amplitude_scale_combo.bind('<<ComboboxSelected>>', self._on_amplitude_scale_change)

        # Filter controls
        ttk.Label(scale_frame, text="LP Filter (Hz):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.lowpass_var = tk.StringVar(value="None")
        lowpass_combo = ttk.Combobox(scale_frame, textvariable=self.lowpass_var,
                                     values=["None", "30", "50", "70", "100"], width=8)
        lowpass_combo.grid(row=1, column=1, padx=5, pady=2)
        lowpass_combo.bind('<<ComboboxSelected>>', self._on_filter_change)

        ttk.Label(scale_frame, text="HP Filter (Hz):").grid(row=1, column=2, sticky=tk.W, padx=(10, 5), pady=2)
        self.highpass_var = tk.StringVar(value="None")
        highpass_combo = ttk.Combobox(scale_frame, textvariable=self.highpass_var,
                                     values=["None", "0.1", "0.5", "1.0", "5.0"], width=8)
        highpass_combo.grid(row=1, column=3, padx=5, pady=2)
        highpass_combo.bind('<<ComboboxSelected>>', self._on_filter_change)

        # --- Navigation ---
        nav_frame = ttk.LabelFrame(control_frame, text="Navigation")
        nav_frame.pack(side=tk.LEFT, padx=(0, 10), fill='y')

        ttk.Button(nav_frame, text="<<", command=lambda: self.on_navigation("jump_backward"), width=4).pack(side=tk.LEFT, padx=2, pady=5)
        ttk.Button(nav_frame, text="<", command=lambda: self.on_navigation("previous"), width=4).pack(side=tk.LEFT, padx=2, pady=5)
        ttk.Button(nav_frame, text=">", command=lambda: self.on_navigation("next"), width=4).pack(side=tk.LEFT, padx=2, pady=5)
        ttk.Button(nav_frame, text=">>", command=lambda: self.on_navigation("jump_forward"), width=4).pack(side=tk.LEFT, padx=2, pady=5)

        # --- Window Info ---
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(side=tk.LEFT, padx=(0, 10), fill='y', expand=True)
        self.window_info_label = ttk.Label(info_frame, text="No file loaded", anchor='center')
        self.window_info_label.pack(padx=5, pady=5, expand=True, fill='both')

    def _on_load_file(self):
        """Handle load file button click."""
        if self.on_load_file:
            self.on_load_file()

    def _on_time_scale_change(self, event=None):
        """Handle time scale change."""
        try:
            new_time_scale = float(self.time_scale_var.get())
            self.on_time_scale_change(new_time_scale)
        except ValueError:
            pass

    def _on_amplitude_scale_change(self, event=None):
        """Handle amplitude scale change."""
        try:
            new_amplitude_scale = float(self.amplitude_scale_var.get())
            self.on_amplitude_scale_change(new_amplitude_scale)
        except ValueError:
            pass

    def _on_filter_change(self, event=None):
        """Handle filter setting changes."""
        try:
            lp_value = self.lowpass_var.get()
            lowpass = None if lp_value == "None" else float(lp_value)

            hp_value = self.highpass_var.get()
            highpass = None if hp_value == "None" else float(hp_value)

            self.on_filter_change(lowpass, highpass)
        except ValueError:
            pass

    def update_window_info(self, current_window: int, total_windows: int,
                          window_start: float, window_end: float):
        """Update window information label."""
        self.window_info_label.config(
            text=f"Window {current_window}/{total_windows}\n"
                 f"({window_start:.1f}s - {window_end:.1f}s)"
        )

    def get_display_settings(self) -> DisplaySettings:
        """Get current display settings."""
        time_scale = float(self.time_scale_var.get())
        amplitude_scale = float(self.amplitude_scale_var.get())

        lowpass = None
        if self.lowpass_var.get() != "None":
            lowpass = float(self.lowpass_var.get())

        highpass = None
        if self.highpass_var.get() != "None":
            highpass = float(self.highpass_var.get())

        return DisplaySettings(
            time_scale=time_scale,
            amplitude_scale=amplitude_scale,
            lowpass_filter=lowpass,
            highpass_filter=highpass
        )


class AnnotationPanel:
    """Panel for annotation controls and display."""

    def __init__(self, parent, on_add_annotation: Callable[[str], None],
                 on_clear_selection: Callable[[], None],
                 on_save_annotations: Callable[[], None],
                 on_load_annotations: Callable[[], None]):
        """
        Initialize annotation panel.
        """
        self.parent = parent
        self.on_add_annotation = on_add_annotation
        self.on_clear_selection = on_clear_selection
        self.on_save_annotations = on_save_annotations
        self.on_load_annotations = on_load_annotations

        self._create_widgets()

    def _create_widgets(self):
        """Create annotation panel widgets."""
        # --- Main Annotation Frame ---
        main_frame = ttk.LabelFrame(self.parent, text="Annotations")
        main_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Top row: Mode, Entry, Add button ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        self.annotation_mode_var = tk.BooleanVar()
        self.annotation_mode_checkbox = ttk.Checkbutton(top_frame, text="Enable Selection",
                                                      variable=self.annotation_mode_var)
        self.annotation_mode_checkbox.pack(side=tk.LEFT, padx=(0, 10))

        # This section is now deprecated by the new dialog workflow, but kept for layout
        ttk.Label(top_frame, text="Annotation Text:").pack(side=tk.LEFT, padx=(0, 5))
        self.annotation_entry = ttk.Entry(top_frame, state='disabled') # Disabled
        self.annotation_entry.pack(side=tk.LEFT, padx=(0, 5), fill='x', expand=True)

        ttk.Button(top_frame, text="Add Annotation",
                  command=self._on_add_annotation, state='disabled').pack(side=tk.LEFT, padx=(0, 5)) # Disabled

        # --- Middle row: Selection info and clear button ---
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.selection_info_label = ttk.Label(middle_frame, text="Selection: None")
        self.selection_info_label.pack(side=tk.LEFT, padx=(0, 10), fill='x', expand=True)

        ttk.Button(middle_frame, text="Clear Selection",
                  command=self.on_clear_selection).pack(side=tk.LEFT, padx=(0, 5))

        # --- Bottom row: File operations ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Button(bottom_frame, text="Save Annotations",
                  command=self.on_save_annotations).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bottom_frame, text="Load Annotations",
                  command=self.on_load_annotations).pack(side=tk.LEFT)

        # --- Current annotations display ---
        display_frame = ttk.Frame(self.parent)
        display_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(display_frame, text="Annotations in Current Window:").pack(anchor=tk.W)
        self.current_annotations_text = tk.Text(display_frame, height=4, relief='solid', borderwidth=1)
        self.current_annotations_text.pack(fill=tk.X, pady=(2,0))

    def _on_add_annotation(self):
        """Handle add annotation button click."""
        # This is now handled by the dialog, but we can leave the hook here.
        messagebox.showinfo("Info", "To add an annotation, enable selection and drag on the plot.", parent=self.parent)

    def update_selection_info(self, start_time: Optional[float], end_time: Optional[float]):
        """Update the selection information label."""
        if start_time is not None and end_time is not None:
            duration = abs(end_time - start_time)
            self.selection_info_label.config(
                text=f"Selection: {start_time:.2f}s - {end_time:.2f}s (Duration: {duration:.2f}s)"
            )
        else:
            self.selection_info_label.config(text="Selection: None")

    def update_annotations_display(self, annotations_text: str):
        """Update the current annotations display."""
        self.current_annotations_text.delete(1.0, tk.END)
        self.current_annotations_text.insert(tk.END, annotations_text)

    def is_annotation_mode_enabled(self) -> bool:
        """Check if annotation mode is enabled."""
        return self.annotation_mode_var.get()
