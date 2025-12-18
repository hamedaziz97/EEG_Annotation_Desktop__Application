"""
Main entry point for the EEG Dashboard application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from EEG_Annotation_Desktop__Application.main_dashboard import EEGDashboard


def main():
    """Main function to run the EEG dashboard."""
    app = QApplication(sys.argv)
    window = EEGDashboard()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
# tested 16/12/2025