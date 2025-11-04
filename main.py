"""
Main entry point for the EEG Dashboard application.
"""

import tkinter as tk
from EEG_Annotation_Desktop__Application.main_dashboard import EEGDashboard


def main():
    """Main function to run the EEG dashboard."""
    root = tk.Tk()
    app = EEGDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
