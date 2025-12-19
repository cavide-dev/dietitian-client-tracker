import sys
from PyQt5.QtWidgets import QApplication
from app.controllers.main_controller import MainController

def main():
    """
    Application Entry Point
    -----------------------
    Initializes the QApplication, creates the main controller,
    and starts the event loop.
    """
    # 1. Create the Application instance (The Core Motor)
    app = QApplication(sys.argv)
    
    # 2. Initialize the Main Controller (The Window)
    main_window = MainController()
    
    # 3. Show the Window
    # Without this call, the application would run in the background invisible
    main_window.resize(1400, 850)
    main_window.show()
    
    # 4. Start the Event Loop
    # Ensures the application stays open until the user closes it
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()