from PyQt5.QtWidgets import QMainWindow
from PyQt5.uic import loadUi
import os

class MainController(QMainWindow):
    """
    Main Controller Class
    ---------------------
    This class is responsible for managing the main window logic
    and loading the user interface created in Qt Designer.
    """
    def __init__(self):
        super(MainController, self).__init__()
        
        # Define the path to the UI file dynamically
        # Uses 'os.path' to ensure compatibility across different operating systems (Windows, macOS, Linux)
        current_dir = os.path.dirname(__file__)
        ui_path = os.path.join(current_dir, '..', 'views', 'main_window.ui')
        
        try:
            # Load the .ui file onto this class instance
            loadUi(ui_path, self)
            print("System Status: UI loaded successfully.")
        except Exception as e:
            # Error handling in case the UI file is missing or corrupted
            print(f"Critical Error: Could not load UI file. Details: {e}")