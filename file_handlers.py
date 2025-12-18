"""
File handling module for EDF/BDF loading and annotation I/O operations, refactored for PyQt6.
"""

import os
import json
from typing import Optional, Tuple, List
import mne
import numpy as np
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from EEG_Annotation_Desktop__Application.models import EEGData, AnnotationCollection, Annotation


class EEGFileHandler:
    """Handles loading and processing of EEG files."""
    
    @staticmethod
    def load_eeg_file(file_path: str) -> Optional[EEGData]:
        """
        Load an EDF or BDF file and return EEGData object.
        
        Args:
            file_path: Path to the EEG file
            
        Returns:
            EEGData object if successful, None otherwise
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.edf':
                raw_data = mne.io.read_raw_edf(file_path, preload=True, verbose=False)
            elif file_extension == '.bdf':
                raw_data = mne.io.read_raw_bdf(file_path, preload=True, verbose=False)
            else:
                try:
                    raw_data = mne.io.read_raw_edf(file_path, preload=True, verbose=False)
                except:
                    raw_data = mne.io.read_raw_bdf(file_path, preload=True, verbose=False)
            
            data = raw_data.get_data()
            sampling_freq = raw_data.info['sfreq']
            channel_names = raw_data.ch_names
            duration = data.shape[1] / sampling_freq
            
            return EEGData(
                data=data,
                sampling_freq=sampling_freq,
                channel_names=channel_names,
                file_path=file_path,
                duration=duration
            )
            
        except Exception as e:
            print(f"Error loading EEG file: {e}")
            return None
    
    @staticmethod
    def get_file_dialog_path(parent: QWidget) -> Optional[str]:
        """
        Open file dialog to select EEG file.
        
        Returns:
            Selected file path or None if cancelled
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select EDF or BDF file",
            "",
            "EEG files (*.edf *.bdf);;EDF files (*.edf);;BDF files (*.bdf);;All files (*.*)"
        )
        return file_path


class AnnotationFileHandler:
    """Handles saving and loading of annotation files."""
    
    @staticmethod
    def save_annotations(parent: QWidget, annotation_collection: AnnotationCollection, 
                        file_path: Optional[str] = None) -> bool:
        """
        Save annotations to JSON file.
        
        Args:
            parent: Parent widget for dialogs
            annotation_collection: Collection of annotations to save
            file_path: Path to save file (if None, will open file dialog)
            
        Returns:
            True if successful, False otherwise
        """
        if not annotation_collection.annotations:
            QMessageBox.warning(parent, "Warning", "No annotations to save")
            return False
        
        if file_path is None:
            initial_path = f"{os.path.splitext(annotation_collection.edf_file)[0]}_annotations.json"
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Save annotations",
                initial_path,
                "JSON files (*.json);;All files (*.*)"
            )
        
        if not file_path:
            return False
        
        try:
            with open(file_path, 'w') as f:
                json.dump(annotation_collection.to_dict(), f, indent=2)
            
            QMessageBox.information(parent, "Success", f"Annotations saved to {file_path}")
            return True
            
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to save annotations: {str(e)}")
            return False
    
    @staticmethod
    def load_annotations(parent: QWidget, file_path: Optional[str] = None) -> Optional[AnnotationCollection]:
        """
        Load annotations from JSON file.
        
        Args:
            parent: Parent widget for dialogs
            file_path: Path to annotation file (if None, will open file dialog)
            
        Returns:
            AnnotationCollection if successful, None otherwise
        """
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                parent,
                "Load annotations",
                "",
                "JSON files (*.json);;All files (*.*)"
            )
        
        if not file_path:
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            annotations = {}
            for key, ann_list in data.get("annotations", {}).items():
                annotations[key] = [
                    Annotation.create(
                        text=ann['text'],
                        start_time=ann['startTime'],
                        end_time=ann['endTime'],
                        color=ann['color'],
                        channels=ann.get('channels', [])
                    )
                    for ann in ann_list
                ]
            
            collection = AnnotationCollection(
                annotations=annotations,
                edf_file=data.get("edfFile", "unknown"),
                window_size=data.get("windowSize", 20.0),
                sampling_freq=data.get("samplingFreq", 250.0),
                export_timestamp=data.get("exportTimestamp", "")
            )
            
            QMessageBox.information(parent, "Success", f"Loaded {len(annotations)} annotated windows")
            return collection
            
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to load annotations: {str(e)}")
            return None
    
    @staticmethod
    def get_annotation_file_path(eeg_file_path: str) -> str:
        """
        Generate annotation file path based on EEG file path.
        """
        base_name = os.path.splitext(os.path.basename(eeg_file_path))[0]
        directory = os.path.dirname(eeg_file_path)
        return os.path.join(directory, f"{base_name}_annotations.json")


class FilterHandler:
    """Handles filtering operations on EEG data."""
    
    @staticmethod
    def apply_filters_array(data: np.ndarray,
                            channel_names: List[str],
                            sampling_freq: float,
                            lowpass: Optional[float] = None,
                            highpass: Optional[float] = None) -> np.ndarray:
        """
        Apply filters to a small 2D window array.
        """
        if lowpass is None and highpass is None:
            return data
        try:
            info = mne.create_info(ch_names=channel_names, sfreq=sampling_freq, ch_types='eeg')
            raw_temp = mne.io.RawArray(data.copy(), info, verbose=False)
            if lowpass is not None:
                raw_temp.filter(None, lowpass, verbose=False)
            if highpass is not None:
                raw_temp.filter(highpass, None, verbose=False)
            return raw_temp.get_data()
        except Exception as e:
            print(f"Filter window error: {e}")
            return data
