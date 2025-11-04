"""
Parses voice commands to create annotations.
"""

import re
from typing import Optional, Dict, Any

class VoiceAnnotationParser:
    """Parses a string of text to extract annotation details."""

    def __init__(self, text: str):
        self.text = text.lower()
        self.label: Optional[str] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def parse(self) -> Optional[Dict[str, Any]]:
        """
        Parses the text and returns a dictionary of annotation details.

        Returns:
            A dictionary with 'label', 'start_time', and 'end_time', or None if parsing fails.
        """
        # Regex to capture "<label> from <start> to <end>"
        match = re.search(r'(.+?)\s+from\s+([\d\.]+)\s+to\s+([\d\.]+)', self.text)

        if match:
            self.label = match.group(1).strip()
            try:
                self.start_time = float(match.group(2))
                self.end_time = float(match.group(3))
            except ValueError:
                return None

            return {
                "label": self.label,
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        
        return None
