"""
Plotting and visualization module for EEG data display.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from typing import List, Optional, Tuple
from SourceLocalization.scripts.dashboard.file_handlers import FilterHandler

from SourceLocalization.scripts.dashboard.models import EEGData, DisplaySettings, SelectionState, Annotation


class EEGPlotter:
    """Handles EEG data plotting and visualization."""
    
    def __init__(self, parent_widget):
        """
        Initialize the plotter.
        
        Args:
            parent_widget: Parent tkinter widget to embed the plot
        """
        self.parent_widget = parent_widget

        # Create figure WITHOUT constrained_layout
        self.figure = Figure(figsize=(16, 12), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, parent_widget)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Connect mouse events
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

        # Callbacks for mouse events
        self.mouse_press_callback = None
        self.mouse_release_callback = None
        self.mouse_move_callback = None
    
    def set_mouse_callbacks(self, press_callback=None, release_callback=None, move_callback=None):
        """Set callbacks for mouse events."""
        self.mouse_press_callback = press_callback
        self.mouse_release_callback = release_callback
        self.mouse_move_callback = move_callback
    
    def _on_mouse_press(self, event):
        """Handle mouse press events."""
        if self.mouse_press_callback:
            self.mouse_press_callback(event)
    
    def _on_mouse_release(self, event):
        """Handle mouse release events."""
        if self.mouse_release_callback:
            self.mouse_release_callback(event)
    
    def _on_mouse_move(self, event):
        """Handle mouse move events."""
        if self.mouse_move_callback:
            self.mouse_move_callback(event)
    
    def plot_eeg_data(self, eeg_data: EEGData,
                      display_settings: DisplaySettings,
                      current_window_start: float,
                      selection_state: SelectionState,
                      annotations: List[Annotation] = None) -> None:
        """
        Plot EEG data for the current window.
        """
        if eeg_data is None:
            return

        self.figure.clear()

        # Get selected channel data
        selected_data, selected_names = self._get_selected_channel_data(
            eeg_data, display_settings.selected_channels
        )

        # Calculate sample indices for current window
        samples_per_window = int(display_settings.time_scale * eeg_data.sampling_freq)
        start_sample = int(current_window_start * eeg_data.sampling_freq)
        end_sample = min(start_sample + samples_per_window, selected_data.shape[1])

        # Get data for current window
        window_data = selected_data[:, start_sample:end_sample]

        # Apply filtering only on the window (fast) if requested
        if (display_settings.lowpass_filter is not None) or (display_settings.highpass_filter is not None):
            window_data = FilterHandler.apply_filters_array(
                data=window_data,
                channel_names=selected_names,
                sampling_freq=eeg_data.sampling_freq,
                lowpass=display_settings.lowpass_filter,
                highpass=display_settings.highpass_filter,
            )

        # Decimate for performance when the window contains many samples
        # Target roughly one x-value per pixel
        num_window_samples = window_data.shape[1]
        canvas_width = self.canvas.get_tk_widget().winfo_width() or 1500
        max_points = max(800, int(canvas_width) - 50)
        decim = max(1, num_window_samples // max_points)
        if decim > 1:
            window_data = window_data[:, ::decim]

        # Time axis matching the (possibly decimated) data
        time_axis = np.linspace(
            current_window_start,
            current_window_start + display_settings.time_scale,
            window_data.shape[1]
        )

        # Calculate channel spacing
        channel_spacing = self._calculate_channel_spacing(
            window_data, display_settings.amplitude_scale
        )

        # Create plot
        ax = self.figure.add_subplot(111)

        # Force the axes to fill almost the entire canvas
        ax.set_position([0.08, 0.07, 0.90, 0.88])  # [left, bottom, width, height]
        ax.margins(x=0.002)

        # Plot channels
        self._plot_channels(ax, time_axis, window_data, selected_names,
                            channel_spacing, display_settings.amplitude_scale)

        # Customize plot appearance
        self._customize_plot(ax, time_axis, window_data, selected_names, display_settings,
                             current_window_start, eeg_data.channel_names)

        # Draw annotations and selection
        if annotations:
            self._draw_annotations(ax, annotations, current_window_start,
                                   display_settings.time_scale)

        if selection_state.has_selection:
            self._draw_selection(ax, selection_state, current_window_start,
                                 display_settings.time_scale)

        # Reduce default padding around plot
        self.figure.subplots_adjust(left=0.06, right=0.995, top=0.92, bottom=0.08)

        self.canvas.draw_idle()
    
    def _get_selected_channel_data(self, eeg_data: EEGData,
                                  selected_channels: List[int]) -> Tuple[np.ndarray, List[str]]:
        """Get data for selected channels only."""
        if not selected_channels:
            return eeg_data.data, eeg_data.channel_names
        
        selected_data = eeg_data.data[selected_channels, :]
        selected_names = [eeg_data.channel_names[i] for i in selected_channels]
        return selected_data, selected_names
    
    def _calculate_channel_spacing(self, window_data: np.ndarray, 
                                 amplitude_scale: float) -> float:
        """Calculate appropriate channel spacing."""
        channel_stds = np.std(window_data, axis=1)
        median_std = np.median(channel_stds)
        base_channel_spacing = median_std * 6  # Base spacing without amplitude scaling
        
        # Apply amplitude scaling to spacing (inverse for spacing)
        scaled_channel_spacing = base_channel_spacing / amplitude_scale
        
        # Minimum spacing to ensure visibility
        if scaled_channel_spacing < 1e-6:
            scaled_channel_spacing = 1e-5
        
        return scaled_channel_spacing
    
    def _plot_channels(self, ax, time_axis: np.ndarray, window_data: np.ndarray,
                      channel_names: List[str], channel_spacing: float, 
                      amplitude_scale: float) -> None:
        """Plot all EEG channels efficiently using LineCollection."""
        from matplotlib.collections import LineCollection

        num_channels = len(channel_names)

        # Compute Y offsets (top-to-bottom) and add to scaled data in one shot
        baselines = np.arange(num_channels - 1, -1, -1, dtype=float) * channel_spacing
        plot_data = window_data * amplitude_scale + baselines[:, None]

        # Build segments array for LineCollection: (n_lines, N, 2)
        x = time_axis[np.newaxis, :].repeat(num_channels, axis=0)
        segments = np.stack((x, plot_data), axis=2)

        lc = LineCollection(segments, colors='b', linewidths=0.7, alpha=0.9)
        ax.add_collection(lc)

    def _customize_plot(self, ax, time_axis: np.ndarray, window_data: np.ndarray,
                       channel_names: List[str], display_settings: DisplaySettings, 
                       current_window_start: float, all_channel_names: List[str]) -> None:
        """Customize plot appearance and styling."""
        # Labels and title
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
        
        # Add time grid lines every second
        time_grid_lines = np.arange(np.ceil(time_axis[0]), np.floor(time_axis[-1]) + 1)
        for grid_time in time_grid_lines:
            ax.axvline(x=grid_time, color='gray', alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add subtle horizontal grid
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
        
        # Set axis limits
        time_margin = (time_axis[-1] - time_axis[0]) * 0.01
        ax.set_xlim(time_axis[0] - time_margin, time_axis[-1] + time_margin)
        
        # Set y-axis limits and place tick labels at each channel baseline
        num_channels = len(channel_names)
        channel_spacing = self._calculate_channel_spacing(
            window_data, display_settings.amplitude_scale
        )
        y_margin = channel_spacing * 0.5
        ax.set_ylim(-y_margin, num_channels * channel_spacing + y_margin)

        # Place y-ticks aligned with traces and label them with channel names
        y_positions = [(num_channels - i - 1) * channel_spacing for i in range(num_channels)]
        ax.set_yticks(y_positions)
        ax.set_yticklabels(channel_names, fontsize=7)
        ax.tick_params(axis='y', which='both', length=0, pad=2)
        ax.yaxis.set_ticks_position('left')
        
        # Style the plot to look more like medical EEG software
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
    
    def _draw_annotations(self, ax, annotations: List[Annotation], 
                         window_start: float, window_size: float) -> None:
        """Draw existing annotations on the plot."""
        window_end = window_start + window_size
        
        for annotation in annotations:
            start_time = annotation.start_time
            end_time = annotation.end_time
            
            # Check if annotation overlaps with current window
            if start_time < window_end and end_time > window_start:
                # Calculate visible portion
                visible_start = max(start_time, window_start)
                visible_end = min(end_time, window_end)
                
                ax.axvspan(visible_start, visible_end, color=annotation.color,
                          label='Annotation' if not ax.get_legend_handles_labels()[1] else "")
    
    def _draw_selection(self, ax, selection_state: SelectionState, 
                       window_start: float, window_size: float) -> None:
        """Draw current selection if active."""
        window_end = window_start + window_size
        selection_start = max(selection_state.start_time, window_start)
        selection_end = min(selection_state.end_time, window_end)
        
        if selection_start < selection_end:
            ax.axvspan(selection_start, selection_end, alpha=0.3, color='yellow',
                      label='Current Selection', zorder=10)
    
    def clear(self):
        """Clear the current plot."""
        self.figure.clear()
        self.canvas.draw()
