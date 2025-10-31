import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import json
import os
from datetime import datetime
import mne
# Just to test the git push

class eegDashboard:
    def __init__(self, rootWindow):
        self.rootWindow = rootWindow
        self.rootWindow.title("EEG Dashboard - Annotation Tool")
        self.rootWindow.geometry("1200x800")

        # Initialize variables
        self.eegData = None
        self.samplingFreq = None
        self.channelNames = []
        self.selectedChannels = []  # List of selected channel indices
        self.currentWindowStart = 0
        self.windowSizeSeconds = 20
        self.annotations = {}
        self.annotationFilePath = None
        self.edfFilePath = None

        # Scale and resolution settings
        self.timeScale = 20  # seconds per window
        self.amplitudeScale = 1.0  # amplitude scaling factor
        self.lowpassFilter = None  # Hz, None for no filter
        self.highpassFilter = None  # Hz, None for no filter

        # Annotation selection variables
        self.annotationStartTime = None
        self.annotationEndTime = None
        self.isSelectingAnnotation = False
        self.selectionRectangle = None
        self.mousePressed = False

        self.setupUserInterface()

    def setupUserInterface(self):
        # Create main frame
        mainFrame = ttk.Frame(self.rootWindow)
        mainFrame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Control panel
        controlFrame = ttk.Frame(mainFrame)
        controlFrame.pack(fill=tk.X, pady=(0, 10))

        # File loading buttons
        ttk.Button(controlFrame, text="Load EEG File (EDF/BDF)",
                   command=self.loadEdfFile).pack(side=tk.LEFT, padx=(0, 10))

        # Settings button for channel selection
        ttk.Button(controlFrame, text="Channel Settings",
                   command=self.openChannelSettings).pack(side=tk.LEFT, padx=(0, 10))

        # Scale and resolution controls
        scaleFrame = ttk.LabelFrame(controlFrame, text="Display Settings")
        scaleFrame.pack(side=tk.LEFT, padx=(0, 10), pady=2)

        # Time scale
        ttk.Label(scaleFrame, text="Time Scale (s):").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.timeScaleVar = tk.StringVar(value="20")
        timeScaleCombo = ttk.Combobox(scaleFrame, textvariable=self.timeScaleVar,
                                      values=["5", "10", "20", "30", "60"], width=8)
        timeScaleCombo.grid(row=0, column=1, padx=2)
        timeScaleCombo.bind('<<ComboboxSelected>>', self.onTimeScaleChange)

        # Amplitude scale
        ttk.Label(scaleFrame, text="Amplitude:").grid(row=0, column=2, sticky=tk.W, padx=(10, 2))
        self.amplitudeScaleVar = tk.StringVar(value="1.0")
        amplitudeScaleCombo = ttk.Combobox(scaleFrame, textvariable=self.amplitudeScaleVar,
                                           values=["0.1", "0.2", "0.5", "1.0", "2.0", "5.0", "10.0", "20.0", "50.0"],
                                           width=8)
        amplitudeScaleCombo.grid(row=0, column=3, padx=2)
        amplitudeScaleCombo.bind('<<ComboboxSelected>>', self.onAmplitudeScaleChange)

        # Filter controls
        ttk.Label(scaleFrame, text="LP Filter (Hz):").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.lowpassVar = tk.StringVar(value="None")
        lowpassCombo = ttk.Combobox(scaleFrame, textvariable=self.lowpassVar,
                                    values=["None", "30", "50", "70", "100"], width=8)
        lowpassCombo.grid(row=1, column=1, padx=2)
        lowpassCombo.bind('<<ComboboxSelected>>', self.onFilterChange)

        ttk.Label(scaleFrame, text="HP Filter (Hz):").grid(row=1, column=2, sticky=tk.W, padx=(10, 2))
        self.highpassVar = tk.StringVar(value="None")
        highpassCombo = ttk.Combobox(scaleFrame, textvariable=self.highpassVar,
                                     values=["None", "0.1", "0.5", "1.0", "5.0"], width=8)
        highpassCombo.grid(row=1, column=3, padx=2)
        highpassCombo.bind('<<ComboboxSelected>>', self.onFilterChange)

        # Navigation buttons
        navFrame = ttk.Frame(controlFrame)
        navFrame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(navFrame, text="<<", command=self.jumpBackward, width=4).pack(side=tk.LEFT, padx=1)
        ttk.Button(navFrame, text="<", command=self.previousWindow, width=4).pack(side=tk.LEFT, padx=1)
        ttk.Button(navFrame, text=">", command=self.nextWindow, width=4).pack(side=tk.LEFT, padx=1)
        ttk.Button(navFrame, text=">>", command=self.jumpForward, width=4).pack(side=tk.LEFT, padx=1)

        # Window position label
        self.windowInfoLabel = ttk.Label(controlFrame, text="No file loaded")
        self.windowInfoLabel.pack(side=tk.LEFT, padx=(0, 10))

        # Annotation controls
        annotationFrame = ttk.Frame(mainFrame)
        annotationFrame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(annotationFrame, text="Annotation Mode:").pack(side=tk.LEFT, padx=(0, 5))
        self.annotationModeVar = tk.BooleanVar()
        self.annotationModeCheckbox = ttk.Checkbutton(annotationFrame, text="Enable Click & Drag",
                                                      variable=self.annotationModeVar)
        self.annotationModeCheckbox.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(annotationFrame, text="Annotation:").pack(side=tk.LEFT, padx=(0, 5))
        self.annotationEntry = ttk.Entry(annotationFrame, width=30)
        self.annotationEntry.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(annotationFrame, text="Add Selected Annotation",
                   command=self.addSelectedAnnotation).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(annotationFrame, text="Clear Selection",
                   command=self.clearSelection).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(annotationFrame, text="Save Annotations",
                   command=self.saveAnnotations).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(annotationFrame, text="Load Annotations",
                   command=self.loadAnnotations).pack(side=tk.LEFT)

        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, mainFrame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Connect mouse events
        self.canvas.mpl_connect('button_press_event', self.onMousePress)
        self.canvas.mpl_connect('button_release_event', self.onMouseRelease)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMove)

        # Selection info display
        selectionFrame = ttk.Frame(mainFrame)
        selectionFrame.pack(fill=tk.X, pady=(5, 0))
        self.selectionInfoLabel = ttk.Label(selectionFrame, text="Selection: None")
        self.selectionInfoLabel.pack(anchor=tk.W)

        # Current annotations display
        annotationDisplayFrame = ttk.Frame(mainFrame)
        annotationDisplayFrame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(annotationDisplayFrame, text="Current Window Annotations:").pack(anchor=tk.W)
        self.currentAnnotationsText = tk.Text(annotationDisplayFrame, height=4)
        self.currentAnnotationsText.pack(fill=tk.X)

    def openChannelSettings(self):
        """Open channel selection window"""
        if not self.channelNames:
            messagebox.showwarning("Warning", "Please load an EEG file first")
            return

        # Create channel selection window
        channelWindow = tk.Toplevel(self.rootWindow)
        channelWindow.title("Channel Selection Settings")
        channelWindow.geometry("400x500")
        channelWindow.resizable(True, True)

        # Make window modal
        channelWindow.transient(self.rootWindow)
        channelWindow.grab_set()

        # Create main frame with scrollbar
        mainFrame = ttk.Frame(channelWindow)
        mainFrame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Info label
        infoLabel = ttk.Label(mainFrame, text=f"Select channels to display ({len(self.channelNames)} total channels):")
        infoLabel.pack(anchor=tk.W, pady=(0, 10))

        # Button frame
        buttonFrame = ttk.Frame(mainFrame)
        buttonFrame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(buttonFrame, text="Select All",
                   command=lambda: self.selectAllChannels(channelVars)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttonFrame, text="Deselect All",
                   command=lambda: self.deselectAllChannels(channelVars)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttonFrame, text="Select Standard EEG",
                   command=lambda: self.selectStandardEegChannels(channelVars)).pack(side=tk.LEFT)

        # Create scrollable frame for channel checkboxes
        channelFrame = ttk.Frame(mainFrame)
        channelFrame.pack(fill=tk.BOTH, expand=True)

        # Create canvas and scrollbar for scrollable area
        canvas = tk.Canvas(channelFrame, height=300)
        scrollbar = ttk.Scrollbar(channelFrame, orient="vertical", command=canvas.yview)
        scrollableFrame = ttk.Frame(canvas)

        scrollableFrame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollableFrame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create channel variables and checkboxes
        channelVars = []
        for i, channelName in enumerate(self.channelNames):
            var = tk.BooleanVar()
            # Set initial state based on current selection
            var.set(i in self.selectedChannels if self.selectedChannels else True)
            channelVars.append(var)

            checkFrame = ttk.Frame(scrollableFrame)
            checkFrame.pack(fill=tk.X, pady=1)

            checkbox = ttk.Checkbutton(checkFrame, text=f"{i + 1:2d}. {channelName}",
                                       variable=var, width=40)
            checkbox.pack(anchor=tk.W)

        # Enable mouse wheel scrolling
        def onMouseWheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", onMouseWheel)

        # OK and Cancel buttons
        buttonFrame2 = ttk.Frame(mainFrame)
        buttonFrame2.pack(fill=tk.X, pady=(10, 0))

        def applyChannelSelection():
            """Apply the selected channels"""
            newSelectedChannels = []
            for i, var in enumerate(channelVars):
                if var.get():
                    newSelectedChannels.append(i)

            if not newSelectedChannels:
                messagebox.showwarning("Warning", "Please select at least one channel")
                return

            self.selectedChannels = newSelectedChannels
            self.updatePlot()
            channelWindow.destroy()

        def cancelChannelSelection():
            """Cancel channel selection"""
            channelWindow.destroy()

        ttk.Button(buttonFrame2, text="Apply", command=applyChannelSelection).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttonFrame2, text="Cancel", command=cancelChannelSelection).pack(side=tk.RIGHT)

        # Center the window
        channelWindow.update_idletasks()
        x = (channelWindow.winfo_screenwidth() // 2) - (channelWindow.winfo_width() // 2)
        y = (channelWindow.winfo_screenheight() // 2) - (channelWindow.winfo_height() // 2)
        channelWindow.geometry(f"+{x}+{y}")

    def selectAllChannels(self, channelVars):
        """Select all channels"""
        for var in channelVars:
            var.set(True)

    def deselectAllChannels(self, channelVars):
        """Deselect all channels"""
        for var in channelVars:
            var.set(False)

    def selectStandardEegChannels(self, channelVars):
        """Select standard EEG channels (10-20 system)"""
        standardChannels = [
            'FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2',
            'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ',
            'T7', 'T8', 'P7', 'P8', 'FC1', 'FC2', 'CP1', 'CP2'
        ]

        # First deselect all
        self.deselectAllChannels(channelVars)

        # Then select standard channels if they exist
        for i, channelName in enumerate(self.channelNames):
            if channelName.upper() in [ch.upper() for ch in standardChannels]:
                channelVars[i].set(True)

    def getSelectedChannelData(self, data):
        """Get data for selected channels only"""
        if not self.selectedChannels:
            return data, self.channelNames

        selectedData = data[self.selectedChannels, :]
        selectedNames = [self.channelNames[i] for i in self.selectedChannels]
        return selectedData, selectedNames

    def onTimeScaleChange(self, event=None):
        """Handle time scale change"""
        try:
            newTimeScale = float(self.timeScaleVar.get())
            self.timeScale = newTimeScale
            self.windowSizeSeconds = newTimeScale  # Update for compatibility
            if self.eegData is not None:
                self.updatePlot()
                self.updateWindowInfo()
        except ValueError:
            pass

    def onAmplitudeScaleChange(self, event=None):
        """Handle amplitude scale change"""
        try:
            newAmplitudeScale = float(self.amplitudeScaleVar.get())
            self.amplitudeScale = newAmplitudeScale
            if self.eegData is not None:
                self.updatePlot()
        except ValueError:
            pass

    def onFilterChange(self, event=None):
        """Handle filter setting changes"""
        try:
            # Update lowpass filter
            lpValue = self.lowpassVar.get()
            self.lowpassFilter = None if lpValue == "None" else float(lpValue)

            # Update highpass filter
            hpValue = self.highpassVar.get()
            self.highpassFilter = None if hpValue == "None" else float(hpValue)

            if self.eegData is not None:
                self.updatePlot()
        except ValueError:
            pass

    def loadEdfFile(self):
        """Load EDF/BDF file using MNE"""
        filePath = filedialog.askopenfilename(
            title="Select EDF or BDF file",
            filetypes=[("EEG files", "*.edf *.bdf"), ("EDF files", "*.edf"), ("BDF files", "*.bdf"),
                       ("All files", "*.*")]
        )

        if filePath:
            try:
                # Detect file type and load accordingly
                fileExtension = os.path.splitext(filePath)[1].lower()

                if fileExtension == '.edf':
                    rawData = mne.io.read_raw_edf(filePath, preload=True, verbose=False)
                elif fileExtension == '.bdf':
                    rawData = mne.io.read_raw_bdf(filePath, preload=True, verbose=False)
                else:
                    # Try to auto-detect based on file content
                    try:
                        rawData = mne.io.read_raw_edf(filePath, preload=True, verbose=False)
                    except:
                        rawData = mne.io.read_raw_bdf(filePath, preload=True, verbose=False)

                # Store data
                self.eegData = rawData.get_data()  # Shape: (n_channels, n_samples)
                self.samplingFreq = rawData.info['sfreq']
                self.channelNames = rawData.ch_names
                self.edfFilePath = filePath

                # Initialize selected channels (all channels by default)
                self.selectedChannels = list(range(len(self.channelNames)))

                # Reset window position
                self.currentWindowStart = 0
                self.windowSizeSeconds = self.timeScale

                # Create annotation file path
                baseFileName = os.path.splitext(os.path.basename(filePath))[0]
                self.annotationFilePath = os.path.join(
                    os.path.dirname(filePath), f"{baseFileName}_annotations.json"
                )

                # Update display
                self.updatePlot()
                self.updateWindowInfo()

                fileType = "EDF" if fileExtension == '.edf' else "BDF" if fileExtension == '.bdf' else "EEG"
                messagebox.showinfo("Success",
                                    f"Loaded {fileType} file with {len(self.channelNames)} channels\n"
                                    f"Sampling frequency: {self.samplingFreq} Hz\n"
                                    f"Duration: {self.eegData.shape[1] / self.samplingFreq:.1f} seconds")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load EEG file: {str(e)}\n\nSupported formats: EDF, BDF")

    def getFilteredData(self):
        """Apply filters to EEG data if specified"""
        if self.eegData is None:
            return None

        # Start with original data
        filteredData = self.eegData.copy()

        # Apply filters if specified
        try:
            if self.lowpassFilter is not None or self.highpassFilter is not None:
                # Create a temporary raw object for filtering
                info = mne.create_info(ch_names=self.channelNames,
                                       sfreq=self.samplingFreq, ch_types='eeg')
                rawTemp = mne.io.RawArray(filteredData, info, verbose=False)

                # Apply lowpass filter
                if self.lowpassFilter is not None:
                    rawTemp.filter(None, self.lowpassFilter, verbose=False)

                # Apply highpass filter
                if self.highpassFilter is not None:
                    rawTemp.filter(self.highpassFilter, None, verbose=False)

                filteredData = rawTemp.get_data()
        except Exception as e:
            print(f"Filter error: {e}")
            # Return original data if filtering fails
            pass

        return filteredData

    def updatePlot(self):
        """Update the EEG plot for current window"""
        if self.eegData is None:
            return

        self.figure.clear()

        # Get filtered data
        displayData = self.getFilteredData()
        if displayData is None:
            displayData = self.eegData

        # Get selected channel data
        selectedData, selectedNames = self.getSelectedChannelData(displayData)

        # Use current time scale for window size
        currentWindowSize = self.timeScale

        # Calculate sample indices for current window
        samplesPerWindow = int(currentWindowSize * self.samplingFreq)
        startSample = int(self.currentWindowStart * self.samplingFreq)
        endSample = min(startSample + samplesPerWindow, selectedData.shape[1])

        # Time axis
        timeAxis = np.linspace(self.currentWindowStart,
                               self.currentWindowStart + currentWindowSize,
                               endSample - startSample)

        # Get data for current window
        windowData = selectedData[:, startSample:endSample]

        # Calculate base channel spacing based on raw data statistics (without amplitude scaling)
        channelStds = np.std(windowData, axis=1)
        medianStd = np.median(channelStds)
        baseChannelSpacing = medianStd * 6  # Base spacing without amplitude scaling

        # Apply amplitude scaling to both data and spacing
        scaledChannelSpacing = baseChannelSpacing / self.amplitudeScale  # Inverse for spacing

        # Minimum spacing to ensure visibility
        if scaledChannelSpacing < 1e-6:
            scaledChannelSpacing = 1e-5

        ax = self.figure.add_subplot(111)

        # Plot channels from top to bottom (reverse order)
        numChannels = len(selectedNames)
        for channelIdx in range(numChannels):
            channelName = selectedNames[channelIdx]
            # Apply amplitude scaling directly to the raw channel data
            channelData = windowData[channelIdx, :] * self.amplitudeScale

            # Calculate baseline position (top channel has highest y-value)
            yBaseline = (numChannels - channelIdx - 1) * scaledChannelSpacing

            # Plot the scaled EEG signal
            plotData = channelData + yBaseline
            ax.plot(timeAxis, plotData, 'b-', linewidth=0.7, alpha=0.9)

            # Add channel label
            ax.text(timeAxis[0] - (timeAxis[-1] - timeAxis[0]) * 0.02, yBaseline,
                    channelName, ha='right', va='center', fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.8))

        # Customize plot appearance
        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Channels', fontsize=12)
        channelInfo = f" ({numChannels}/{len(self.channelNames)} channels)" if numChannels != len(
            self.channelNames) else ""
        ax.set_title(
            f'EEG Data{channelInfo} - Window {self.currentWindowStart:.1f}-{self.currentWindowStart + currentWindowSize:.1f}s | '
            f'Scale: {currentWindowSize}s/{self.amplitudeScale}x | '
            f'Filters: LP={self.lowpassVar.get()}, HP={self.highpassVar.get()}',
            fontsize=12, pad=15)

        # Add time grid lines every second for better readability
        timeGridLines = np.arange(np.ceil(timeAxis[0]), np.floor(timeAxis[-1]) + 1)
        for gridTime in timeGridLines:
            ax.axvline(x=gridTime, color='gray', alpha=0.3, linestyle='--', linewidth=0.5)

        # Add subtle horizontal grid
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)

        # Set axis limits
        timeMargin = (timeAxis[-1] - timeAxis[0]) * 0.05
        ax.set_xlim(timeAxis[0] - timeMargin, timeAxis[-1] + timeMargin)

        yMargin = scaledChannelSpacing * 0.5
        ax.set_ylim(-yMargin, numChannels * scaledChannelSpacing + yMargin)

        # Remove y-axis ticks (channel names are shown as text labels)
        ax.set_yticks([])

        # Style the plot to look more like medical EEG software
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)

        # Highlight existing annotations
        self.drawExistingAnnotations(ax)

        # Draw current selection if active
        if self.annotationStartTime is not None and self.annotationEndTime is not None:
            selectionStart = max(self.annotationStartTime, self.currentWindowStart)
            selectionEnd = min(self.annotationEndTime, self.currentWindowStart + currentWindowSize)
            if selectionStart < selectionEnd:
                ax.axvspan(selectionStart, selectionEnd, alpha=0.3, color='yellow',
                           label='Current Selection', zorder=10)

        self.canvas.draw()
        self.updateCurrentAnnotationsDisplay()
        self.updateSelectionInfo()

    def drawExistingAnnotations(self, ax):
        """Draw existing annotations on the plot"""
        for annotationKey, annotationList in self.annotations.items():
            for annotation in annotationList:
                startTime = annotation.get('startTime', 0)
                endTime = annotation.get('endTime', 0)

                # Check if annotation overlaps with current window
                windowStart = self.currentWindowStart
                windowEnd = self.currentWindowStart + self.windowSizeSeconds

                if startTime < windowEnd and endTime > windowStart:
                    # Calculate visible portion
                    visibleStart = max(startTime, windowStart)
                    visibleEnd = min(endTime, windowEnd)

                    ax.axvspan(visibleStart, visibleEnd, alpha=0.2, color='red',
                               label='Annotation' if not ax.get_legend_handles_labels()[1] else "")

    def onMousePress(self, event):
        """Handle mouse press event for annotation selection"""
        if not self.annotationModeVar.get() or self.eegData is None:
            return

        if event.inaxes and event.button == 1:  # Left mouse button
            self.mousePressed = True
            self.annotationStartTime = event.xdata
            self.annotationEndTime = event.xdata
            self.isSelectingAnnotation = True
            self.updateSelectionInfo()

    def onMouseMove(self, event):
        """Handle mouse move event for annotation selection"""
        if not self.annotationModeVar.get() or not self.mousePressed or not self.isSelectingAnnotation:
            return

        if event.inaxes and event.xdata is not None:
            self.annotationEndTime = event.xdata
            # Ensure start time is always less than end time
            if self.annotationEndTime < self.annotationStartTime:
                self.annotationStartTime, self.annotationEndTime = self.annotationEndTime, self.annotationStartTime
            self.updatePlot()

    def onMouseRelease(self, event):
        """Handle mouse release event for annotation selection"""
        if not self.annotationModeVar.get() or not self.mousePressed:
            return

        self.mousePressed = False
        if self.isSelectingAnnotation and event.inaxes and event.xdata is not None:
            self.annotationEndTime = event.xdata
            # Ensure start time is always less than end time
            if self.annotationEndTime < self.annotationStartTime:
                self.annotationStartTime, self.annotationEndTime = self.annotationEndTime, self.annotationStartTime

            # Minimum selection duration (0.1 seconds)
            if abs(self.annotationEndTime - self.annotationStartTime) < 0.1:
                self.clearSelection()
            else:
                self.updateSelectionInfo()
                self.updatePlot()

    def updateSelectionInfo(self):
        """Update the selection information label"""
        if self.annotationStartTime is not None and self.annotationEndTime is not None:
            duration = abs(self.annotationEndTime - self.annotationStartTime)
            self.selectionInfoLabel.config(
                text=f"Selection: {self.annotationStartTime:.2f}s - {self.annotationEndTime:.2f}s (Duration: {duration:.2f}s)"
            )
        else:
            self.selectionInfoLabel.config(text="Selection: None")

    def clearSelection(self):
        """Clear current annotation selection"""
        self.annotationStartTime = None
        self.annotationEndTime = None
        self.isSelectingAnnotation = False
        self.updateSelectionInfo()
        if self.eegData is not None:
            self.updatePlot()

    def addSelectedAnnotation(self):
        """Add annotation for selected time range"""
        if self.eegData is None:
            messagebox.showwarning("Warning", "Please load an EDF file first")
            return

        if self.annotationStartTime is None or self.annotationEndTime is None:
            messagebox.showwarning("Warning", "Please select a time range first by clicking and dragging on the plot")
            return

        annotationText = self.annotationEntry.get().strip()
        if not annotationText:
            messagebox.showwarning("Warning", "Please enter annotation text")
            return

        # Create unique key based on start time
        annotationKey = f"annotation_{len(self.annotations)}"

        # Add annotation with precise timing
        annotationData = {
            "text": annotationText,
            "timestamp": datetime.now().isoformat(),
            "startTime": round(self.annotationStartTime, 3),
            "endTime": round(self.annotationEndTime, 3),
            "duration": round(abs(self.annotationEndTime - self.annotationStartTime), 3)
        }

        self.annotations[annotationKey] = [annotationData]

        # Clear entry and selection
        self.annotationEntry.delete(0, tk.END)
        self.clearSelection()

        messagebox.showinfo("Success",
                            f"Annotation added: {annotationData['startTime']:.2f}s - {annotationData['endTime']:.2f}s")
        self.updatePlot()

    def updateWindowInfo(self):
        """Update window information label"""
        if self.eegData is None:
            return

        totalDuration = self.eegData.shape[1] / self.samplingFreq
        currentWindow = int(self.currentWindowStart / self.timeScale) + 1
        totalWindows = int(np.ceil(totalDuration / self.timeScale))

        self.windowInfoLabel.config(
            text=f"Window {currentWindow}/{totalWindows} "
                 f"({self.currentWindowStart:.1f}-{self.currentWindowStart + self.timeScale:.1f}s)"
        )

    def nextWindow(self):
        """Navigate to next window"""
        if self.eegData is None:
            return

        totalDuration = self.eegData.shape[1] / self.samplingFreq
        if self.currentWindowStart + self.timeScale < totalDuration:
            self.currentWindowStart += self.timeScale
            self.updatePlot()
            self.updateWindowInfo()

    def previousWindow(self):
        """Navigate to previous window"""
        if self.eegData is None:
            return

        if self.currentWindowStart > 0:
            self.currentWindowStart = max(0, self.currentWindowStart - self.timeScale)
            self.updatePlot()
            self.updateWindowInfo()

    def jumpForward(self):
        """Jump forward by 5 windows"""
        if self.eegData is None:
            return

        totalDuration = self.eegData.shape[1] / self.samplingFreq
        jumpDistance = self.timeScale * 5
        if self.currentWindowStart + jumpDistance < totalDuration:
            self.currentWindowStart += jumpDistance
        else:
            self.currentWindowStart = max(0, totalDuration - self.timeScale)
        self.updatePlot()
        self.updateWindowInfo()

    def jumpBackward(self):
        """Jump backward by 5 windows"""
        if self.eegData is None:
            return

        jumpDistance = self.timeScale * 5
        self.currentWindowStart = max(0, self.currentWindowStart - jumpDistance)
        self.updatePlot()
        self.updateWindowInfo()

    def addAnnotation(self):
        """Add annotation for current window (legacy method)"""
        if self.eegData is None:
            messagebox.showwarning("Warning", "Please load an EDF file first")
            return

        annotationText = self.annotationEntry.get().strip()
        if not annotationText:
            messagebox.showwarning("Warning", "Please enter annotation text")
            return

        # Create window key
        windowKey = f"{self.currentWindowStart}-{self.currentWindowStart + self.windowSizeSeconds}"

        # Add annotation
        if windowKey not in self.annotations:
            self.annotations[windowKey] = []

        annotationData = {
            "text": annotationText,
            "timestamp": datetime.now().isoformat(),
            "startTime": self.currentWindowStart,
            "endTime": self.currentWindowStart + self.windowSizeSeconds,
            "duration": self.windowSizeSeconds
        }

        self.annotations[windowKey].append(annotationData)

        # Clear entry and update display
        self.annotationEntry.delete(0, tk.END)
        self.updatePlot()  # Refresh to show annotation highlight
        messagebox.showinfo("Success", "Annotation added successfully")

    def updateCurrentAnnotationsDisplay(self):
        """Update the display of annotations for current window"""
        self.currentAnnotationsText.delete(1.0, tk.END)

        windowStart = self.currentWindowStart
        windowEnd = self.currentWindowStart + self.windowSizeSeconds

        annotationCount = 0
        for annotationKey, annotationList in self.annotations.items():
            for annotation in annotationList:
                startTime = annotation.get('startTime', 0)
                endTime = annotation.get('endTime', 0)

                # Check if annotation overlaps with current window
                if startTime < windowEnd and endTime > windowStart:
                    annotationCount += 1
                    overlapStart = max(startTime, windowStart)
                    overlapEnd = min(endTime, windowEnd)

                    self.currentAnnotationsText.insert(tk.END,
                                                       f"{annotationCount}. {annotation['text']} "
                                                       f"({overlapStart:.2f}s - {overlapEnd:.2f}s) "
                                                       f"[{annotation['timestamp'][:19]}]\n")

    def saveAnnotations(self):
        """Save annotations to JSON file"""
        if not self.annotations:
            messagebox.showwarning("Warning", "No annotations to save")
            return

        filePath = filedialog.asksaveasfilename(
            title="Save annotations",
            defaultextension=".json",
            initialfile=os.path.basename(self.annotationFilePath) if self.annotationFilePath else "annotations.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filePath:
            try:
                annotationData = {
                    "edfFile": os.path.basename(self.edfFilePath) if self.edfFilePath else "unknown",
                    "windowSize": self.windowSizeSeconds,
                    "samplingFreq": self.samplingFreq,
                    "annotations": self.annotations,
                    "exportTimestamp": datetime.now().isoformat()
                }

                with open(filePath, 'w') as f:
                    json.dump(annotationData, f, indent=2)

                messagebox.showinfo("Success", f"Annotations saved to {filePath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save annotations: {str(e)}")

    def loadAnnotations(self):
        """Load annotations from JSON file"""
        filePath = filedialog.askopenfilename(
            title="Load annotations",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filePath:
            try:
                with open(filePath, 'r') as f:
                    annotationData = json.load(f)

                self.annotations = annotationData.get("annotations", {})
                self.updatePlot()
                messagebox.showinfo("Success",
                                    f"Loaded {len(self.annotations)} annotated windows")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load annotations: {str(e)}")


def main():
    """Main function to run the EEG dashboard"""
    rootWindow = tk.Tk()
    app = eegDashboard(rootWindow)
    rootWindow.mainloop()


if __name__ == "__main__":
    main()