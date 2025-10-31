"""
Data models and configuration classes for the EEG Dashboard application.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EEGData:
    """Container for EEG data and metadata."""
    data: Any  # numpy array with shape (n_channels, n_samples)
    sampling_freq: float
    channel_names: List[str]
    file_path: str
    duration: float
    
    @property
    def n_channels(self) -> int:
        return self.data.shape[0]
    
    @property
    def n_samples(self) -> int:
        return self.data.shape[1]
    
    @property
    def total_duration(self) -> float:
        return self.n_samples / self.sampling_freq


@dataclass
class Annotation:
    """Single annotation entry."""
    text: str
    start_time: float
    end_time: float
    timestamp: str
    duration: float
    color: str

    @classmethod
    def create(cls, text: str, start_time: float, end_time: float, color: str) -> 'Annotation':
        """Create a new annotation with current timestamp."""
        duration = abs(end_time - start_time)
        return cls(
            text=text,
            start_time=round(start_time, 3),
            end_time=round(end_time, 3),
            timestamp=datetime.now().isoformat(),
            duration=round(duration, 3),
            color=color
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'text': self.text,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'timestamp': self.timestamp,
            'duration': self.duration,
            'color': self.color
        }


@dataclass
class AnnotationCollection:
    """Collection of annotations with metadata."""
    annotations: Dict[str, List[Annotation]]
    edf_file: str
    window_size: float
    sampling_freq: float
    export_timestamp: str
    
    @classmethod
    def create_empty(cls, edf_file: str, window_size: float, sampling_freq: float) -> 'AnnotationCollection':
        """Create an empty annotation collection."""
        return cls(
            annotations={},
            edf_file=edf_file,
            window_size=window_size,
            sampling_freq=sampling_freq,
            export_timestamp=datetime.now().isoformat()
        )
    
    def add_annotation(self, annotation: Annotation) -> str:
        """Add an annotation and return its key."""
        key = f"annotation_{len(self.annotations)}"
        self.annotations[key] = [annotation]
        return key
    
    def get_annotations_in_range(self, start_time: float, end_time: float) -> List[Annotation]:
        """Get all annotations that overlap with the given time range."""
        overlapping = []
        for annotation_list in self.annotations.values():
            for annotation in annotation_list:
                if (annotation.start_time < end_time and 
                    annotation.end_time > start_time):
                    overlapping.append(annotation)
        return overlapping
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'edfFile': self.edf_file,
            'windowSize': self.window_size,
            'samplingFreq': self.sampling_freq,
            'annotations': {
                key: [ann.to_dict() for ann in ann_list]
                for key, ann_list in self.annotations.items()
            },
            'exportTimestamp': self.export_timestamp
        }


@dataclass
class DisplaySettings:
    """Display and visualization settings."""
    time_scale: float = 20.0
    amplitude_scale: float = 1.0
    lowpass_filter: Optional[float] = None
    highpass_filter: Optional[float] = None
    selected_channels: List[int] = None
    
    def __post_init__(self):
        if self.selected_channels is None:
            self.selected_channels = []


@dataclass
class SelectionState:
    """State for annotation selection."""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    is_selecting: bool = False
    mouse_pressed: bool = False
    
    def clear(self):
        """Clear the current selection."""
        self.start_time = None
        self.end_time = None
        self.is_selecting = False
        self.mouse_pressed = False
    
    @property
    def has_selection(self) -> bool:
        """Check if there's a valid selection."""
        return (self.start_time is not None and 
                self.end_time is not None and 
                abs(self.end_time - self.start_time) >= 0.1)
    
    @property
    def duration(self) -> float:
        """Get selection duration."""
        if self.has_selection:
            return abs(self.end_time - self.start_time)
        return 0.0
