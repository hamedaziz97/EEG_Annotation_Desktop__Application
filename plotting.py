"""
Plotting and visualization module for EEG data display, refactored for PyQt6.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from typing import List, Optional, Tuple

from EEG_Annotation_Desktop__Application.file_handlers import FilterHandler
from EEG_Annotation_Desktop__Application.models import EEGData, DisplaySettings, SelectionState, Annotation


class EEGPlotter(QWidget):
    """Handles EEG data plotting and visualization."""
    
    def __init__(self, parent: QWidget = None):
        """Initialize the plotter."""
        super().__init__(parent)
        self.selected_annotation_channels = set()
        self.display_settings = None
        self.eeg_data = None
        self.channel_spacing = 0

        self.figure = Figure(figsize=(16, 12), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

        self.mouse_press_callback = None
        self.mouse_release_callback = None
        self.mouse_move_callback = None
        self.channel_selection_callback = None
    
    def set_mouse_callbacks(self, press_callback=None, release_callback=None, move_callback=None, channel_selection_callback=None):
        """Set callbacks for mouse events."""
        self.mouse_press_callback = press_callback
        self.mouse_release_callback = release_callback
        self.mouse_move_callback = move_callback
        self.channel_selection_callback = channel_selection_callback
    
    def _on_mouse_press(self, event):
        """Handle mouse press events."""
        if event.button == 3:  # Right-click for channel selection
            self._handle_channel_selection_click(event)
            return

        if event.button == 1 and self.mouse_press_callback: # Left-click for annotation
            self.mouse_press_callback(event)
    
    def _on_mouse_release(self, event):
        """Handle mouse release events."""
        if event.button == 1 and self.mouse_release_callback:
            self.mouse_release_callback(event)
    
    def _on_mouse_move(self, event):
        """Handle mouse move events."""
        if event.button == 1 and self.mouse_move_callback:
            self.mouse_move_callback(event)

    def _handle_channel_selection_click(self, event):
        """Handle right-clicks on the plot to select channels for annotation."""
        if not event.inaxes or self.display_settings is None or self.eeg_data is None or self.channel_spacing == 0:
            return

        ax = event.inaxes
        num_displayed_channels = len(ax.get_yticklabels())
        
        clicked_y = event.ydata
        clicked_channel_display_index = round(clicked_y / self.channel_spacing)
        clicked_channel_display_index = num_displayed_channels - 1 - clicked_channel_display_index

        if 0 <= clicked_channel_display_index < num_displayed_channels:
            displayed_channel_names = [self.eeg_data.channel_names[i] for i in self.display_settings.selected_channels] or self.eeg_data.channel_names
            channel_name = displayed_channel_names[clicked_channel_display_index]

            if channel_name in self.selected_annotation_channels:
                self.selected_annotation_channels.remove(channel_name)
            else:
                self.selected_annotation_channels.add(channel_name)
            
            if self.channel_selection_callback:
                self.channel_selection_callback(list(self.selected_annotation_channels))

    def clear_channel_selection(self):
        """Clear the set of selected channels for annotation."""
        self.selected_annotation_channels.clear()

    def plot_eeg_data(self, eeg_data: EEGData,
                      display_settings: DisplaySettings,
                      current_window_start: float,
                      selection_state: SelectionState,
                      annotations: List[Annotation] = None) -> None:
        """Plot EEG data for the current window."""
        if eeg_data is None:
            return

        self.eeg_data = eeg_data
        self.display_settings = display_settings
        self.figure.clear()

        selected_data, selected_names = self._get_selected_channel_data(
            eeg_data, display_settings.selected_channels
        )

        samples_per_window = int(display_settings.time_scale * eeg_data.sampling_freq)
        start_sample = int(current_window_start * eeg_data.sampling_freq)
        end_sample = min(start_sample + samples_per_window, selected_data.shape[1])

        window_data = selected_data[:, start_sample:end_sample]

        if (display_settings.lowpass_filter is not None) or (display_settings.highpass_filter is not None):
            window_data = FilterHandler.apply_filters_array(
                data=window_data,
                channel_names=selected_names,
                sampling_freq=eeg_data.sampling_freq,
                lowpass=display_settings.lowpass_filter,
                highpass=display_settings.highpass_filter,
            )

        num_window_samples = window_data.shape[1]
        canvas_width = self.canvas.width() or 1500
        max_points = max(800, int(canvas_width) - 50)
        decim = max(1, num_window_samples // max_points)
        if decim > 1:
            window_data = window_data[:, ::decim]

        time_axis = np.linspace(
            current_window_start,
            current_window_start + display_settings.time_scale,
            window_data.shape[1]
        )

        self.channel_spacing = self._calculate_channel_spacing(window_data)

        ax = self.figure.add_subplot(111)
        ax.set_position([0.08, 0.07, 0.90, 0.88])
        ax.margins(x=0.002)

        self._plot_channels(ax, time_axis, window_data, selected_names, self.channel_spacing)

        self._customize_plot(ax, time_axis, selected_names, display_settings,
                             current_window_start, eeg_data.channel_names)

        if annotations:
            self._draw_annotations(ax, annotations, current_window_start,
                                   display_settings.time_scale, self.channel_spacing)

        if selection_state.has_selection:
            self._draw_selection(ax, selection_state, current_window_start,
                                 display_settings.time_scale)

        self.figure.subplots_adjust(left=0.06, right=0.995, top=0.92, bottom=0.08)
        self.canvas.draw_idle()
    
    def _get_selected_channel_data(self, eeg_data: EEGData,
                                  selected_channels: List[int]) -> Tuple[np.ndarray, List[str]]:
        if not selected_channels:
            return eeg_data.data, eeg_data.channel_names
        
        selected_data = eeg_data.data[selected_channels, :]
        selected_names = [eeg_data.channel_names[i] for i in selected_channels]
        return selected_data, selected_names
    
    def _calculate_channel_spacing(self, window_data: np.ndarray) -> float:
        if window_data.size == 0:
            return 1.0
        channel_stds = np.std(window_data, axis=1)
        median_std = np.median(channel_stds[channel_stds > 0])
        if median_std == 0 or np.isnan(median_std):
            median_std = 1e-5 # Fallback for flat signals
        return median_std * 15 # Base spacing
    
    def _plot_channels(self, ax, time_axis: np.ndarray, window_data: np.ndarray,
                      channel_names: List[str], channel_spacing: float) -> None:
        num_channels = len(channel_names)

        for i in range(num_channels):
            y_offset = (num_channels - 1 - i) * channel_spacing
            color = 'red' if channel_names[i] in self.selected_annotation_channels else 'b'
            ax.plot(time_axis, window_data[i] + y_offset, color=color, linewidth=0.7)

    def _customize_plot(self, ax, time_axis: np.ndarray,
                       channel_names: List[str], display_settings: DisplaySettings, 
                       current_window_start: float, all_channel_names: List[str]) -> None:
        channel_info = (f" ({len(channel_names)}/{len(all_channel_names)} channels)" 
                       if len(channel_names) != len(all_channel_names) else "")
        
        ax.set_title(
            f'EEG Data - Window {current_window_start:.1f}-{current_window_start + display_settings.time_scale:.1f}s '
            f'| Scale: {display_settings.time_scale}s/{display_settings.amplitude_scale}x '
            f'| Filters: LP={display_settings.lowpass_filter or "None"}, HP={display_settings.highpass_filter or "None"}',
            fontsize=10, pad=2, loc='center'
        )

        ax.set_xlabel('Time (seconds)', fontsize=9, labelpad=2)
        ax.set_ylabel('Channels', fontsize=9, labelpad=2)
        
        time_grid_lines = np.arange(np.ceil(time_axis[0]), np.floor(time_axis[-1]) + 1)
        for grid_time in time_grid_lines:
            ax.axvline(x=grid_time, color='gray', alpha=0.3, linestyle='--', linewidth=0.5)
        
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
        
        time_margin = (time_axis[-1] - time_axis[0]) * 0.01 if time_axis.size > 0 else 0.01
        ax.set_xlim(time_axis[0] - time_margin, time_axis[-1] + time_margin) if time_axis.size > 0 else None
        
        num_channels = len(channel_names)
        
        # Calculate geometric center of the channel baselines
        # Bottom channel is at 0, top channel is at (num_channels - 1) * spacing
        geometric_center = (num_channels - 1) * self.channel_spacing / 2.0
        
        # Calculate view height with margins
        # We want to see from -0.5*spacing to (num_channels - 0.5)*spacing
        # Total height = num_channels * spacing
        # Apply zoom factor
        zoom_factor = 1.0 / display_settings.amplitude_scale
        view_height = num_channels * self.channel_spacing * zoom_factor
        
        # Ensure a minimum view height to avoid errors
        if view_height <= 0:
            view_height = self.channel_spacing
            
        ax.set_ylim(
            geometric_center - view_height / 2.0,
            geometric_center + view_height / 2.0
        )

        y_positions = [(num_channels - 1 - i) * self.channel_spacing for i in range(num_channels)]
        ax.set_yticks(y_positions)
        ax.set_yticklabels(channel_names, fontsize=7)
        ax.tick_params(axis='y', which='both', length=0, pad=2)
        ax.yaxis.set_ticks_position('left')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
    
    def _draw_annotations(self, ax, annotations: List[Annotation], 
                         window_start: float, window_size: float, channel_spacing: float) -> None:
        window_end = window_start + window_size
        displayed_channel_names = [self.eeg_data.channel_names[i] for i in self.display_settings.selected_channels] or self.eeg_data.channel_names
        num_displayed_channels = len(displayed_channel_names)

        for annotation in annotations:
            if not annotation.channels:
                if annotation.start_time < window_end and annotation.end_time > window_start:
                    visible_start = max(annotation.start_time, window_start)
                    visible_end = min(annotation.end_time, window_end)
                    ax.axvspan(visible_start, visible_end, color=annotation.color, zorder=0)
            else:
                for channel_name in annotation.channels:
                    if channel_name in displayed_channel_names:
                        if annotation.start_time < window_end and annotation.end_time > window_start:
                            visible_start = max(annotation.start_time, window_start)
                            visible_end = min(annotation.end_time, window_end)
                            try:
                                display_index = displayed_channel_names.index(channel_name)
                                y_pos = (num_displayed_channels - 1 - display_index) * channel_spacing
                                ax.axhspan(y_pos - channel_spacing / 2, y_pos + channel_spacing / 2, 
                                          xmin=(visible_start - window_start) / window_size, 
                                          xmax=(visible_end - window_start) / window_size, 
                                          color=annotation.color, zorder=0)
                            except ValueError:
                                pass
    
    def _draw_selection(self, ax, selection_state: SelectionState, 
                       window_start: float, window_size: float) -> None:
        if not selection_state.has_selection:
            return
        window_end = window_start + window_size
        selection_start = max(selection_state.start_time, window_start)
        selection_end = min(selection_state.end_time, window_end)
        
        if selection_start < selection_end:
            ax.axvspan(selection_start, selection_end, alpha=0.3, color='yellow', zorder=10)
    
    def clear(self):
        """Clear the current plot."""
        self.figure.clear()
        self.canvas.draw()
