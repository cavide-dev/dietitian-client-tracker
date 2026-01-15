import sys
from PyQt5.QtWidgets import QApplication
from app.controllers.login_controller import LoginController
from app.controllers.main_controller import MainController

def main():
    """
    Application Entry Point
    -----------------------
    1. Load stylesheet
    2. Show LoginController (ask user to login)
    3. After successful login, show MainController (main app)
    """
    # 1. Create the Application instance (The Core Motor)
    app = QApplication(sys.argv)
    
    # 2. Load the Light Theme Stylesheet
    # ====================================================
    # This stylesheet is used by ALL windows:
    # - LoginController (login window)
    # - MainController (main application)
    # ====================================================
    try:
        with open("assets/styles/light_theme.qss", "r", encoding="utf-8") as qss_file:
            qss = qss_file.read()
        app.setStyleSheet(qss)
    except FileNotFoundError:
        print("Tema dosyası bulunamadı, varsayılan tema ile devam ediliyor.")
    
    # 3. Create and Show LoginController
    # ====================================================
    # User must login first before seeing the main app
    # ====================================================
    login_window = LoginController()
    login_window.resize(500, 600)
    login_window.show()
    
    # 4. Setup: When login is successful, show main app
    # ====================================================
    # LoginController emits 'login_successful' signal when user logs in
    # We connect that signal to a function that creates MainController
    # ====================================================
    def on_login_success(user_data):
        """
        Called when user successfully logs in
        user_data = {"username": "admin", "email": "...", ...}
        """
        try:
            # Create main window and pass user data
            main_window = MainController(user_data)
            main_window.resize(1200, 700)
            main_window.show()
            
            # Hide login window after successful login
            login_window.hide()
            
            # When logout happens, show login window again
            def on_logout():
                login_window.show()
                login_window.input_username.setText("")
                login_window.input_password.setText("")
            
            main_window.logout_signal.connect(on_logout)
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to open main window:\n{e}")
    
    # Connect the signal
    login_window.login_successful.connect(on_login_success)
    
    # 5. Start the Event Loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()