from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QDialog, QMenu, QLabel, QFileDialog
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from bson.objectid import ObjectId
from datetime import datetime
from app.database import get_database
from app.views.measurement_dialog import MeasurementDialog
from app.views.stats_card_widget import StatsCard, StatsCardContainer
from app.views.chart_widget import TrendChart
from app.views.edit_profile_dialog import EditProfileDialog
from app.views.change_password_dialog import ChangePasswordDialog
from app.services.validation_service import ValidationService
from app.services.calculation_service import CalculationService
from app.services.export_service import ExportService
from app.controllers.client_controller import ClientController
from app.controllers.diet_controller import DietController
from app.controllers.measurement_controller import MeasurementController
from app.i18n.translations import TranslationService
import os
import sys
import pymongo

class MainController(QMainWindow):
    # Signal emitted when user logs out
    logout_signal = pyqtSignal()
    
    def __init__(self, current_user=None):
        """
        Main Application Logic.
        Initializes the UI, database connection, and event handlers.
        
        Args:
            current_user: Dictionary with user data {"username": "...", "fullname": "...", ...}
        """
        super(MainController, self).__init__()
        
        # Store current user data
        self.current_user = current_user
        
        # 1. Load UI File
        # We load the .ui file dynamically relative to this script's location.
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'views', 'main_window.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "UI Loading Error", 
                            f"Could not load UI file: {e}\n\nPath: {ui_path}")
            sys.exit(1)  

        # 2. Database Connection & State
        # Establish connection to MongoDB Atlas.
        self.db = get_database()
        
        # Check if database connection failed
        if self.db is None:
            QMessageBox.critical(self, "Connection Error", 
                                "Could not connect to MongoDB. Please check your internet connection and .env file.")
            sys.exit(1)  
        
        self.current_client_id = None
        
        self.current_diet_id = None  # For tracking which diet is being edited
        self.stats_container = None  # Will hold the Stats container
        self.trend_chart = None  # Will hold the chart widget
        
        # Initialize controllers
        self.client_controller = ClientController(self)
        self.diet_controller = DietController(self)
        self.measurement_controller = MeasurementController(self)
        self.current_theme = "Light"  # Track current theme for new charts
        self.empty_state_diet = None  # Will hold the empty state widget
        self.empty_state_measurements = None  # Will hold the empty state widget for measurements
        
        # 3. Initial Setup
        # Show the dashboard page by default on startup.
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        
        # Set greeting with user's full name
        user_fullname = self.current_user.get("fullname", "User") if self.current_user else "User"
        self.label_greeting.setText(f"Hi, {user_fullname}!")
        
        # Set settings page - current user label
        self.label_current_user.setText(f"Logged in as: {user_fullname}")
        
        # Show placeholder "Loading..." immediately - don't block UI
        self.label_total_clients.setText("Loading...")
        self.label_total_measurements.setText("Loading...")
        self.label_active_diets.setText("Loading...")
        
        # Reset clients table completely (clear any pre-loaded columns from UI)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        
        # Load dashboard and clients table asynchronously (100ms delay)
        # This ensures MainWindow opens immediately without freezing
        QTimer.singleShot(100, self.load_dashboard)
        QTimer.singleShot(150, self.client_controller.load_clients_table)
        
        # --- 4. NAVIGATION BUTTONS (Menu Connections) ---
        self.btn_dashboard.clicked.connect(self.show_dashboard)
        self.btn_clients.clicked.connect(self.show_clients_page)
        self.btn_diet_plans.clicked.connect(self.switch_to_diet_page)
        self.btn_settings.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_settings))
        
        # Logout button handler
        self.btn_logout.clicked.connect(self.handle_logout)
        
        # Settings buttons handlers
        self.btn_edit_profile.clicked.connect(self.open_edit_profile_dialog)
        self.btn_change_password.clicked.connect(self.open_change_password_dialog)
        
        # Double click the list
        self.tableWidget.cellDoubleClicked.connect(self.client_controller.open_client_detail)
        # Back to list
        self.btn_back_to_list.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        # Search bar connection
        self.search_clients.textChanged.connect(self.client_controller.filter_clients_by_search)
        # --- 5. CLIENT OPERATIONS (Add/Delete/Cancel/Save/Edit) ---
        #Add
        self.btn_add_new.clicked.connect(self.client_controller.prepare_add_mode)
        #Cancel(Smart Navigation)
        self.btn_cancel.clicked.connect(self.client_controller.handle_cancel)
        #Save
        self.btn_save.clicked.connect(self.client_controller.save_client)
        #Delete
        self.btn_delete.clicked.connect(self.client_controller.delete_client)
        #Edit
        self.btn_edit.clicked.connect(self.client_controller.prepare_edit_mode)

        # --- MEASUREMENT BUTTONS ---
        self.btn_add_measurement.clicked.connect(self.measurement_controller.open_add_measurement_dialog)
        # Enable custom right-click menu
        self.table_measurements.setContextMenuPolicy(Qt.CustomContextMenu)
        # Connect the signal to our function
        self.table_measurements.customContextMenuRequested.connect(self.measurement_controller.show_context_menu)
        # Double-click to edit measurement
        self.table_measurements.cellDoubleClicked.connect(self.measurement_controller.open_edit_measurement_dialog)
        
        
        # DIET PAGE CONNECTIONS 
        
        # 1. Dropdown Setup
        self.diet_controller.load_client_dropdown()
        self.cmb_client_select.currentIndexChanged.connect(self.update_selected_client_from_dropdown)

        # 2. Navigation Buttons
        
        self.btn_new_diet.clicked.connect(self.diet_controller.prepare_add_diet_mode)
        self.table_diet_history.cellDoubleClicked.connect(self.open_diet_detail)
        self.btn_back_to_diet_list.clicked.connect(lambda: self.stack_diet_sub.setCurrentIndex(0))

        # Save button - handles both NEW and UPDATE based on current_diet_id
        self.btn_save_diet.clicked.connect(self.handle_diet_save)

        # Delete button for diet
        if hasattr(self, 'btn_delete_diet'):
            self.btn_delete_diet.clicked.connect(self.diet_controller.delete_diet_plan)
        
        # --- THEME SWITCHER ---
        # Load theme preference FIRST, then connect signal
        self.load_theme_preference()
        self.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        
        # --- LANGUAGE SWITCHER ---
        # Load language preference FIRST, then connect signal
        self.load_language_preference()
        # Refresh UI labels immediately after loading language preference
        self.refresh_ui_labels()
        self.combo_language.currentIndexChanged.connect(self.on_language_changed)
        
        # --- EXPORT & BACKUP BUTTONS ---
        if hasattr(self, 'btn_export_pdf'):
            self.btn_export_pdf.clicked.connect(self.handle_export_pdf)
        if hasattr(self, 'btn_backup'):
            self.btn_backup.clicked.connect(self.handle_backup)
        
        # --- Default View Settings ---
        self.stack_diet_sub.setCurrentIndex(0)

        self.init_ui_logic()
        
    def load_dashboard(self):
        """
        Loads dashboard statistics and recent activity.
        Called when dashboard page is displayed.
        
        Data displayed:
        - Total Clients count (for current user only)
        - Total Measurements count (for current user only)
        - Active Diets count (for current user only)
        - Recent Activity list (last 10 actions)
        """
        if self.db is None:
            return

        try:
            # ===== 1. STATS CARDS =====
            
            # Build query filter for current user
            user_filter = {}
            if self.current_user:
                user_filter = {"dietician_username": self.current_user.get("username")}
            
            # Total Clients (only for current user)
            total_clients = self.db['clients'].count_documents(user_filter)
            self.label_total_clients.setText(str(total_clients))
            
            # Update settings page labels too - emoji comes from JSON now
            self.label_total_clients_2.setText(f"{TranslationService.get('dashboard.total_clients', 'Total Clients')}: {total_clients}")
            
            # Total Measurements (only for current user's clients)
            total_measurements = self.db['measurements'].count_documents(user_filter)
            self.label_total_measurements.setText(str(total_measurements))
            
            # Update settings page labels too - emoji comes from JSON now
            self.label_total_measurements_2.setText(f"{TranslationService.get('dashboard.total_measurements', 'Total Measurements')}: {total_measurements}")
            
            # Active Diets (status = 'active' AND for current user only)
            diet_filter = {"status": "active"}
            if self.current_user:
                diet_filter["dietician_username"] = self.current_user.get("username")
            active_diets = self.db['diet_plans'].count_documents(diet_filter)
            self.label_active_diets.setText(str(active_diets))
            
            # ===== 2. RECENT ACTIVITY =====
            
            self.list_recent_activity.clear()
            
            # Get recent clients (latest 5 for current user)
            recent_clients = list(self.db['clients'].find(user_filter).sort("_id", -1).limit(5))
            for client in recent_clients:
                activity_text = f"✓ {client.get('full_name', 'Unknown')} - {TranslationService.get('clients.title', 'Client')} {TranslationService.get('messages.added', 'added')}"
                self.list_recent_activity.addItem(activity_text)
            
            # Get recent measurements (latest 3 for current user)
            measurement_filter = user_filter.copy()
            recent_measurements = list(self.db['measurements'].find(measurement_filter).sort("_id", -1).limit(3))
            for measurement in recent_measurements:
                # Find client name for this measurement
                client = self.db['clients'].find_one({"_id": measurement.get('client_id')})
                client_name = client.get('full_name', 'Unknown') if client else 'Unknown'
                activity_text = f"✓ {client_name} - {TranslationService.get('measurements.title', 'Measurement')} {TranslationService.get('messages.added', 'added')}"
                self.list_recent_activity.addItem(activity_text)
            
            # Get recent diet plans (latest 2 for current user)
            diet_activity_filter = user_filter.copy()
            recent_diets = list(self.db['diet_plans'].find(diet_activity_filter).sort("_id", -1).limit(2))
            
            for diet in recent_diets:
                client_id = diet.get('client_id')
                
                # Convert string client_id to ObjectId if needed
                from bson.objectid import ObjectId
                if isinstance(client_id, str):
                    try:
                        client_id = ObjectId(client_id)
                    except Exception:
                        pass
                
                # Find client name for this diet
                client = self.db['clients'].find_one({"_id": client_id})
                client_name = client.get('full_name', 'Unknown') if client else 'Unknown'
                diet_name = diet.get('title', 'Unknown')
                activity_text = f"✓ {client_name} - {diet_name} ({TranslationService.get('diet_plans.title', 'Diet Plan')} {TranslationService.get('messages.created', 'created')})"
                self.list_recent_activity.addItem(activity_text)
            
            # If no activity, show message
            if self.list_recent_activity.count() == 0:
                self.list_recent_activity.addItem(TranslationService.get("messages.no_activity", "No recent activity yet"))
                
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            self.list_recent_activity.addItem(f"Error loading activity: {str(e)}")

    def show_dashboard(self):
        """
        Show dashboard page and load fresh data.
        Called when Dashboard button is clicked.
        """
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        self.refresh_ui_labels()
        
        # Show loading state
        self.label_total_clients.setText("Loading...")
        self.label_total_measurements.setText("Loading...")
        self.label_active_diets.setText("Loading...")
        
        # Load data asynchronously to prevent UI freeze
        QTimer.singleShot(50, self.load_dashboard)
    
    def show_clients_page(self):
        """
        Show clients page.
        Called when Clients button is clicked.
        """
        self.stackedWidget.setCurrentWidget(self.page_clients)
        self.refresh_ui_labels()

    def calculate_age(self, birth_date_str):
        """
        Calculate age from birth date string (format: yyyy-MM-dd).
        
        Args:
            birth_date_str (str): Birth date in yyyy-MM-dd format
            
        Returns:
            int: Age in years, or None if calculation fails
        """
        # Delegated to CalculationService (REFACTORED)
        return CalculationService.calculate_age(birth_date_str)    

    def show_diet_empty_state(self):
        """
        Shows a centered empty state message in the diet list area.
        """
        # Clear the table first
        self.table_diet_history.setRowCount(0)
        
        # Create empty state widget if it doesn't exist
        if self.empty_state_diet is None:
            self.empty_state_diet = QLabel("👤 Select a client to view diet plans")
            self.empty_state_diet.setAlignment(Qt.AlignCenter)
            self.empty_state_diet.setObjectName("empty_state_diet")
            # Get the parent layout and insert before table
            layout = self.table_diet_history.parent().layout()
            table_index = layout.indexOf(self.table_diet_history)
            layout.insertWidget(table_index, self.empty_state_diet)
            
        self.table_diet_history.hide()
        self.empty_state_diet.show()

    def hide_diet_empty_state(self):
        """
        Hides the empty state widget and shows the table.
        """
        if self.empty_state_diet is not None:
            self.empty_state_diet.hide()
        # Always show the table
        self.table_diet_history.show()

    def show_measurements_empty_state(self):
        """Show empty state for measurements, hide table"""
        if self.empty_state_measurements is None:
            empty_text = TranslationService.get("measurements.no_measurements", "📊 No measurements recorded. Add your first measurement to get started.")
            self.empty_state_measurements = QLabel(empty_text)
            self.empty_state_measurements.setAlignment(Qt.AlignCenter)
            self.empty_state_measurements.setObjectName("empty_state_measurements")
            # Get the parent layout and insert before table
            layout = self.table_measurements.parent().layout()
            table_index = layout.indexOf(self.table_measurements)
            layout.insertWidget(table_index, self.empty_state_measurements)
    
        self.table_measurements.hide()
        self.empty_state_measurements.show()

    def hide_measurements_empty_state(self):
        """Hide empty state for measurements, show table"""
        if self.empty_state_measurements is not None:
            self.empty_state_measurements.hide()
        # Always show the table
        self.table_measurements.show()
    
    def update_selected_client_from_dropdown(self, index):
        """
        Triggered when the user selects a name from the dropdown.
        Updates the global 'current_client_id' variable used for saving.
        """
        # Retrieve the hidden ID from the selected item (comes as string from combobox)
        client_id_str = self.cmb_client_select.currentData()
        
        if client_id_str:
            # Convert string to ObjectId for database queries
            try:
                self.current_client_id = ObjectId(client_id_str)
                self.hide_diet_empty_state()  # Hide the empty state first
                self.diet_controller.load_client_diet_plans() # Then load table data
            except Exception as e:
                print(f"ERROR: Invalid client ID format: {e}")
                self.current_client_id = None
                self.show_diet_empty_state()
        else:
            # If "Select Client..." is chosen, reset the ID
            self.current_client_id = None
            self.show_diet_empty_state()  # Show placeholder


    def switch_to_diet_page(self):
        """
        Switches the main view to the Diet Plans page and resets the 
        internal sub-stack to the 'Table View' (Index 0).
        Ensures the user always sees the list first, not the form.
        """
        # 1. Switch the Main Stacked Widget to the Diet Page
        self.stackedWidget.setCurrentWidget(self.page_diet_plans) 
        
        self.refresh_ui_labels()  # Refresh UI labels when switching to diet page
        
        # 2. Refresh diet plans and dropdown with current language
        if hasattr(self, 'diet_controller') and self.diet_controller:
            if hasattr(self.diet_controller, 'load_client_dropdown'):
                self.diet_controller.load_client_dropdown()
            if self.current_client_id and hasattr(self.diet_controller, 'load_client_diet_plans'):
                self.diet_controller.load_client_diet_plans()
            else:
                # Show empty state only if no client is selected
                self.show_diet_empty_state()
        
        # 3. Reset the Sub-Stacked Widget to the List/Table View (Page 0)
        # This fixes the issue of getting stuck on the 'Add Diet' form 
        # when navigating back to this page.
        try:
            self.stack_diet_sub.setCurrentIndex(0)
        except Exception as e:
            print(f"Error resetting diet sub-stack: {e}")    


    def init_ui_logic(self):
        """
        Initializes static UI configuration.
        This method is called ONCE when the application starts.

        Purpose:
        - Apply visual and layout-related settings
        - Keep UI styling separate from data-loading logic
        - Prevent UI from resetting on every data refresh
        """

        # --- Birth Date Picker: Enable Calendar Popup ---
        # Why? QDateEdit down button styling is problematic
        # Solution: setCalendarPopup(True) = opens calendar on click
        # Result: User can type date OR select from calendar
        self.date_birth_add.setCalendarPopup(True)

        # --- Diet History Table: Column Layout ---
        diet_header = self.table_diet_history.horizontalHeader()
        diet_header.setSectionResizeMode(QHeaderView.Stretch)
        diet_header.setStretchLastSection(True)
        self.table_diet_history.verticalHeader().setVisible(False)

        # --- Measurement Table: Column Layout ---
        measurement_header = self.table_measurements.horizontalHeader()
        measurement_header.setSectionResizeMode(QHeaderView.Stretch)
        measurement_header.setStretchLastSection(True)
        self.table_measurements.verticalHeader().setVisible(False)

        # Enable alternating row colors for better readability
        self.table_diet_history.setAlternatingRowColors(True)

        # Show grid lines between cells
        self.table_diet_history.setShowGrid(True)

    def open_diet_detail(self, row, column):
        """
        Triggered when user double-clicks a diet plan in the table.
        Loads the diet data and switches to edit mode.
            """
        # 1. Get the hidden Diet ID
        date_item = self.table_diet_history.item(row, 0)
        if not date_item:
            return
        
        diet_id_str = date_item.data(Qt.UserRole)
        if not diet_id_str:
                return
            
        # 2. Convert to ObjectId and fetch from DB
        try:
            diet_id = ObjectId(diet_id_str)
            diet = self.db['diet_plans'].find_one({'_id': diet_id})
            
            if not diet:
                QMessageBox.warning(self, "Error", "Diet plan not found!")
                return
            
            # 3. Store the diet ID in memory (for updating later)
            self.current_diet_id = diet_id
            
            # 4. Pre-fill the form with existing data
            self.txt_diet_title.setText(diet.get('title', ''))
            self.txt_breakfast.setPlainText(diet.get('content', {}).get('breakfast', ''))
            self.txt_snack_1.setPlainText(diet.get('content', {}).get('morning_snack', ''))
            self.txt_lunch.setPlainText(diet.get('content', {}).get('lunch', ''))
            self.txt_snack_2.setPlainText(diet.get('content', {}).get('afternoon_snack', ''))
            self.txt_dinner.setPlainText(diet.get('content', {}).get('dinner', ''))
            self.txt_snack_3.setPlainText(diet.get('content', {}).get('evening_snack', ''))
            
            # 5. Switch to edit page 
            self.stack_diet_sub.setCurrentIndex(1)
             # 6. Enable delete button (we're editing, not creating)
            if hasattr(self, 'btn_delete_diet'):
                self.btn_delete_diet.setEnabled(True)
                self.btn_delete_diet.setObjectName("btn_delete_diet_danger")
                self.btn_delete_diet.setCursor(Qt.PointingHandCursor)
                # Force style refresh to apply QSS rules for new objectName
                self.btn_delete_diet.style().unpolish(self.btn_delete_diet)
                self.btn_delete_diet.style().polish(self.btn_delete_diet)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open diet: {e}")
    
    def _parse_date_value(self, date_value):
        """Convert various date formats to Python date object"""
        from datetime import datetime as dt
        if isinstance(date_value, datetime):
            return date_value.date()
        elif isinstance(date_value, str):
            return dt.strptime(date_value, '%Y-%m-%d').date()
        else:
            return date_value

    def handle_logout(self):
        """
        Logout handler - closes main window and returns to login
        Clears current user data for security (shared device scenarios)
        """
        # Clear current user data
        self.current_user = None
        
        # Emit logout signal so run.py can show login window
        self.logout_signal.emit()
        
        # Close the main window
        self.close()
    
    def open_edit_profile_dialog(self):
        """Open Edit Profile dialog"""
        dialog = EditProfileDialog(parent=self, user_data=self.current_user, db=self.db)
        if dialog.exec_() == QDialog.Accepted:
            # Update greeting and settings label after profile change
            user_fullname = self.current_user.get("fullname", "User")
            self.label_greeting.setText(f"Hi, {user_fullname}!")
            self.label_current_user.setText(f"Logged in as: {user_fullname}")
    
    def open_change_password_dialog(self):
        """Open Change Password dialog"""
        dialog = ChangePasswordDialog(parent=self, user_data=self.current_user, db=self.db)
        dialog.exec_()

    def load_theme_preference(self):
        """Load user's saved theme preference from database, default to Light"""
        try:
            if self.db is None or self.current_user is None:
                self.apply_theme("Light")
                return

            # Get user's theme preference from database
            username = self.current_user.get("username")
            user_doc = self.db['dieticians'].find_one({"username": username})
            
            if user_doc and "theme_preference" in user_doc:
                theme = user_doc["theme_preference"]
            else:
                # Default to Light theme
                theme = "Light"
            
            # Apply theme first
            self.apply_theme(theme)
            
            # THEN set combo_theme to match
            index = self.combo_theme.findText(theme)
            if index >= 0:
                self.combo_theme.setCurrentIndex(index)
                
        except Exception as e:
            print(f"Error loading theme preference: {e}")
            self.apply_theme("Light")

    def on_theme_changed(self, index):
        """Handle theme change from combo_theme dropdown"""
        theme = self.combo_theme.currentText()
        self.apply_theme(theme)
        
        # Save preference to database
        try:
            if self.db is not None and self.current_user is not None:
                username = self.current_user.get("username")
                self.db['dieticians'].update_one(
                    {"username": username},
                    {"$set": {"theme_preference": theme}}
                )
        except Exception as e:
            print(f"Error saving theme preference: {e}")

    def apply_theme(self, theme_name):
        """Apply selected theme by loading QSS file"""
        try:
            qss_file = None
            
            if theme_name == "Dark":
                qss_file = "dark_theme.qss"
            else:
                qss_file = "light_theme.qss"
            
            # Get absolute path to QSS file - go up TWO levels (controllers -> app -> root)
            styles_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'styles', qss_file)
            styles_dir = os.path.normpath(os.path.abspath(styles_dir))
            
            print(f"Loading theme file: {styles_dir}")
            
            # Read QSS file
            with open(styles_dir, encoding="utf-8") as f:
                qss_content = f.read()
            
            # Apply stylesheet to entire application
            from PyQt5.QtWidgets import QApplication
            QApplication.instance().setStyleSheet(qss_content)
            
            # Store current theme for new chart creation
            self.current_theme = theme_name
            
            # Apply theme to active chart widget
            if self.trend_chart is not None:
                self.trend_chart.apply_theme(theme_name)
            
            print(f" Theme changed to: {theme_name}")
            
        except FileNotFoundError as e:
            print(f" Error: Theme file not found - {e}")
            print(f"  Looked for file at: {styles_dir}")
        except Exception as e:
            print(f" Error applying theme: {e}")

    def load_language_preference(self):
        """Load user's saved language preference from database, default to English"""
        try:
            if self.current_user is None:
                # Set to first item (English)
                self.combo_language.setCurrentIndex(0)
                TranslationService.initialize(language="en", debug=False)
                return

            # Get user's language preference from current_user dict
            language = self.current_user.get("preferred_language", "en")
            
            # Initialize TranslationService with user's language
            TranslationService.initialize(language=language, debug=False)
            
            # Map language code to combo box index
            language_map = {"en": 0, "tr": 1, "ko": 2}
            index = language_map.get(language, 0)
            
            # Set combo_language to match (without triggering signal initially)
            self.combo_language.blockSignals(True)
            self.combo_language.setCurrentIndex(index)
            self.combo_language.blockSignals(False)
            
            # Refresh UI labels with the loaded language
            self.refresh_ui_labels()
            
            print(f" Language preference loaded: {language}")
                
        except Exception as e:
            print(f"Error loading language preference: {e}")
            self.combo_language.setCurrentIndex(0)
            TranslationService.initialize(language="en", debug=False)

    def on_language_changed(self, index):
        """Handle language change from combo_language dropdown"""
        # Map combo box index to language code
        language_map = {0: "en", 1: "tr", 2: "ko"}
        language_code = language_map.get(index, "en")
        
        # Update TranslationService
        TranslationService.initialize(language=language_code, debug=False)
        
        # Save preference to database
        try:
            if self.db is not None and self.current_user is not None:
                username = self.current_user.get("username")
                self.db['dieticians'].update_one(
                    {"username": username},
                    {"$set": {"preferred_language": language_code}}
                )
                # Update current_user dict for consistency
                self.current_user["preferred_language"] = language_code
                print(f" Language changed to: {language_code}")
        except Exception as e:
            print(f"Error saving language preference: {e}")
        
        # Refresh UI labels with new language
        self.refresh_ui_labels()
        
        # Refresh clients table headers
        if hasattr(self, 'client_controller') and self.client_controller:
            if hasattr(self.client_controller, 'load_clients_table'):
                self.client_controller.load_clients_table()
        
        # Refresh diet plans page (table and dropdown)
        if hasattr(self, 'diet_controller') and self.diet_controller:
            if hasattr(self.diet_controller, 'load_client_diet_plans'):
                self.diet_controller.load_client_diet_plans()
            if hasattr(self.diet_controller, 'load_client_dropdown'):
                self.diet_controller.load_client_dropdown()
        
        # Refresh stat cards if currently viewing measurements
        if hasattr(self, 'measurement_controller') and self.measurement_controller:
            self.measurement_controller.refresh_stats_and_chart()


    def refresh_ui_labels(self):
        """Refresh all UI text labels with current language from TranslationService"""
        try:
            # ===== NAVIGATION BUTTONS (LEFT SIDEBAR) =====
            self.btn_dashboard.setText(TranslationService.get("pages.dashboard", "Dashboard"))
            self.btn_clients.setText(TranslationService.get("pages.clients", "Clients"))
            self.btn_diet_plans.setText(TranslationService.get("pages.diet_plans", "Diet Plans"))
            self.btn_settings.setText(TranslationService.get("pages.settings", "Settings"))
            self.btn_logout.setText(TranslationService.get("settings.logout", "Logout"))
            
            # ===== DASHBOARD PAGE =====
            # Greeting label
            if hasattr(self, 'label_greeting'):
                user_fullname = self.current_user.get('fullname', 'User') if self.current_user else 'User'
                greeting_text = TranslationService.get("dashboard.greeting", "Welcome")
                self.label_greeting.setText(f"{greeting_text}, {user_fullname}!")
            
            # Dashboard title
            if hasattr(self, 'TitleLabel'):
                self.TitleLabel.setText(TranslationService.get("pages.dashboard", "Dashboard"))
            
            # Stats labels
            self.label_total_clients.setText(TranslationService.get("dashboard.total_clients", "Total Clients"))
            self.label_total_measurements.setText(TranslationService.get("dashboard.total_measurements", "Total Measurements"))
            self.label_active_diets.setText(TranslationService.get("dashboard.active_diets", "Active Diet Plans"))
            
            # Stats card groupbox titles
            if hasattr(self, 'card_total_clients'):
                self.card_total_clients.setTitle(TranslationService.get("dashboard.total_clients", "Total Clients"))
            if hasattr(self, 'card_total_measurements'):
                self.card_total_measurements.setTitle(TranslationService.get("dashboard.total_measurements", "Total Measurements"))
            if hasattr(self, 'card_active_diets'):
                self.card_active_diets.setTitle(TranslationService.get("dashboard.active_diets", "Active Diet Plans"))
            if hasattr(self, 'groupBox_recent_activity'):
                self.groupBox_recent_activity.setTitle(TranslationService.get("dashboard.recent_activity", "Recent Activity"))
            
            # ===== CLIENTS PAGE =====
            self.btn_add_new.setText(TranslationService.get("clients.add_client", "Add New Client"))
            self.btn_delete.setText(TranslationService.get("buttons.delete", "Delete"))
            self.btn_edit.setText(TranslationService.get("buttons.edit", "Edit"))
            self.btn_save.setText(TranslationService.get("buttons.save", "Save"))
            self.btn_cancel.setText(TranslationService.get("buttons.cancel", "Cancel"))
            self.search_clients.setPlaceholderText(TranslationService.get("placeholders.search_clients", "Search by name..."))
            
            # ===== ADD/EDIT CLIENT PAGE =====
            # Client Info GroupBox
            if hasattr(self, 'groupBox_11'):
                self.groupBox_11.setTitle(TranslationService.get("clients.title", "Client Info"))
            
            # Client Notes GroupBox
            if hasattr(self, 'groupBox_8'):
                self.groupBox_8.setTitle(TranslationService.get("measurements.notes", "Client Notes"))
            
            # Form labels
            if hasattr(self, 'label_name'):
                self.label_name.setText(TranslationService.get("clients.full_name", "Full Name") + ":")
            if hasattr(self, 'label_phone'):
                self.label_phone.setText(TranslationService.get("clients.phone", "Phone") + ":")
            if hasattr(self, 'label_birth_date'):
                self.label_birth_date.setText(TranslationService.get("clients.birth_date", "Birth Date") + ":")
            
            # Placeholders
            if hasattr(self, 'txt_name'):
                self.txt_name.setPlaceholderText(TranslationService.get("placeholders.full_name", "Enter full name"))
            if hasattr(self, 'txt_phone'):
                self.txt_phone.setPlaceholderText(TranslationService.get("placeholders.phone", "Enter phone number"))
            if hasattr(self, 'txt_notes'):
                self.txt_notes.setPlaceholderText(TranslationService.get("placeholders.notes", "Enter notes..."))
            
            # ===== CLIENT DETAIL PAGE =====
            # Tab titles
            if hasattr(self, 'tabWidget'):
                if self.tabWidget.count() >= 1:
                    self.tabWidget.setTabText(0, TranslationService.get("measurements.overview", "Overview"))
                if self.tabWidget.count() >= 2:
                    self.tabWidget.setTabText(1, TranslationService.get("measurements.title", "Measurements"))
                if self.tabWidget.count() >= 3:
                    self.tabWidget.setTabText(2, TranslationService.get("measurements.notes", "Notes"))
            
            # Age label
            if hasattr(self, 'lbl_age'):
                current_age = self.lbl_age.text().replace('...age', '').strip()
                if current_age and current_age != '...age':
                    self.lbl_age.setText(f"{TranslationService.get('clients.age', 'Age')}: {current_age}")
            
            # Client notes GroupBox in detail
            if hasattr(self, 'groupBox_7'):
                self.groupBox_7.setTitle(TranslationService.get("clients.notes", "Notes"))
            
            # Refresh clients table headers (columns)
            if hasattr(self, 'tableWidget'):
                headers = [
                    TranslationService.get("clients.full_name", "Full Name"),
                    TranslationService.get("clients.phone", "Phone"),
                    TranslationService.get("clients.notes", "Notes")
                ]
                self.tableWidget.setHorizontalHeaderLabels(headers)
            
            self.btn_back_to_list.setText(TranslationService.get("buttons.back", "Back"))
            self.btn_add_measurement.setText(TranslationService.get("measurements.add_measurement", "Add Measurement"))
            
            # ===== DIET PLANS PAGE =====
            # Dropdown placeholder
            if hasattr(self, 'cmb_client_select'):
                self.cmb_client_select.setPlaceholderText(TranslationService.get("diet_plans.select_client_first", "Select a client..."))
            
            self.btn_new_diet.setText(TranslationService.get("diet_plans.add_diet", "Add New Diet"))
            self.btn_save_diet.setText(TranslationService.get("buttons.save", "Save"))
            if hasattr(self, 'btn_delete_diet'):
                self.btn_delete_diet.setText(TranslationService.get("buttons.delete", "Delete"))
            self.btn_back_to_diet_list.setText(TranslationService.get("buttons.back", "Back"))
            
            # Diet plan form GroupBox titles
            if hasattr(self, 'groupBox'):  # Breakfast
                self.groupBox.setTitle(TranslationService.get("diet_plans.breakfast", "Breakfast"))
            if hasattr(self, 'groupBox_2'):  # Morning Snack
                self.groupBox_2.setTitle(TranslationService.get("diet_plans.morning_snack", "Morning Snack"))
            if hasattr(self, 'groupBox_3'):  # Lunch
                self.groupBox_3.setTitle(TranslationService.get("diet_plans.lunch", "Lunch"))
            if hasattr(self, 'groupBox_4'):  # Afternoon Snack
                self.groupBox_4.setTitle(TranslationService.get("diet_plans.afternoon_snack", "Afternoon Snack"))
            if hasattr(self, 'groupBox_5'):  # Dinner
                self.groupBox_5.setTitle(TranslationService.get("diet_plans.dinner", "Dinner"))
            if hasattr(self, 'groupBox_6'):  # Evening Snack
                self.groupBox_6.setTitle(TranslationService.get("diet_plans.evening_snack", "Evening Snack"))
            
            # Diet title placeholder
            if hasattr(self, 'txt_diet_title'):
                self.txt_diet_title.setPlaceholderText(TranslationService.get("placeholders.diet_title", "Diet Plan Title"))
            
            # Empty states for diet
            if self.empty_state_diet:
                self.empty_state_diet.setText(TranslationService.get("empty_states.select_client_diet", "Select a client to view diet plans"))
            
            # Active/Passive status in tables - update when data is reloaded
            # (These are populated dynamically, so we'll update them when table is refreshed)
            
            # ===== MEASUREMENTS PAGE =====
            if self.empty_state_measurements:
                self.empty_state_measurements.setText(TranslationService.get("empty_states.select_client_measurements", "Select a client to view measurements"))
            
            # ===== SETTINGS PAGE =====
            if hasattr(self, 'group_profile'):
                self.group_profile.setTitle(TranslationService.get("settings.account", "Account"))
            
            self.label_current_user.setText(f"{TranslationService.get('settings.current_user', 'Logged in as:')} {self.current_user.get('fullname', 'User')}")
            self.btn_edit_profile.setText(TranslationService.get("settings.edit_profile", "Edit Profile"))
            self.btn_change_password.setText(TranslationService.get("settings.change_password", "Change Password"))
            
            # Settings page GroupBox titles
            if hasattr(self, 'groupBox_9'):  # PREFERENCES
                self.groupBox_9.setTitle(TranslationService.get("settings.preferences", "Preferences"))
            if hasattr(self, 'groupBox_10'):  # DATA & EXPORT
                self.groupBox_10.setTitle(TranslationService.get("settings.data_export", "Data & Export"))
            
            # Theme and language labels
            if hasattr(self, 'label'):
                self.label.setText(TranslationService.get("settings.language", "Language") + ":")
            if hasattr(self, 'label_2'):
                self.label_2.setText(TranslationService.get("settings.theme", "Theme") + ":")
            
            # Export and Backup buttons
            if hasattr(self, 'btn_export_pdf'):
                self.btn_export_pdf.setText(TranslationService.get("buttons.export_pdf", "Export as PDF"))
            if hasattr(self, 'btn_backup'):
                self.btn_backup.setText(TranslationService.get("buttons.backup", "Backup"))
            
            # ===== TABLE HEADERS =====
            # Clients table headers - updated to match client_controller.load_clients_table()
            if self.tableWidget.columnCount() > 0:
                headers = [
                    TranslationService.get("clients.full_name", "Full Name"),
                    TranslationService.get("clients.phone", "Phone"),
                    TranslationService.get("clients.notes", "Notes")
                ]
                self.tableWidget.setHorizontalHeaderLabels(headers)
            
            # Diet history table headers
            if self.table_diet_history.columnCount() > 0:
                headers = [
                    TranslationService.get("tables.date", "Date"),
                    TranslationService.get("diet_plans.diet_name", "Diet Name"),
                    TranslationService.get("diet_plans.status", "Status")
                ]
                self.table_diet_history.setHorizontalHeaderLabels(headers)
            
            # Measurements table headers
            if self.table_measurements.columnCount() > 0:
                headers = [
                    TranslationService.get("tables.date", "Date"),
                    TranslationService.get("measurements.weight", "Weight (kg)"),
                    TranslationService.get("measurements.waist", "Waist (cm)"),
                    TranslationService.get("measurements.body_fat", "Body Fat (%)"),
                    TranslationService.get("measurements.muscle_mass", "Muscle (kg)"),
                    TranslationService.get("measurements.metabolic_age", "Metabolic Age"),
                    TranslationService.get("measurements.bmr", "BMR (kcal)")
                ]
                self.table_measurements.setHorizontalHeaderLabels(headers)
            
            print(" UI labels refreshed with new language")
            
        except Exception as e:
            print(f"Error refreshing UI labels: {e}")

    def handle_diet_save(self):
        """
        Smart save handler - decides whether to INSERT or UPDATE based on current_diet_id.
        Delegates to DietController methods.
        """
        if hasattr(self, 'current_diet_id') and self.current_diet_id:
            # Editing mode - update existing diet
            self.diet_controller.update_diet_plan()
        else:
            # New diet mode - create new diet
            self.diet_controller.save_diet_plan()

    def handle_export_pdf(self):
        """
        Handle PDF export button click.
        Opens file dialog and exports clients list to PDF.
        """
        try:
            # Get clients from database
            user_filter = {}
            if self.current_user:
                user_filter = {"dietician_username": self.current_user.get("username")}
            
            clients = list(self.db['clients'].find(user_filter).sort("fullname", 1))
            
            if not clients:
                QMessageBox.warning(
                    self,
                    TranslationService.get("dialogs.warning", "Warning"),
                    TranslationService.get("clients.no_clients", "No clients found to export!")
                )
                return
            
            # Open file dialog to choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                TranslationService.get("dialogs.export_pdf", "Export Clients to PDF"),
                f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not file_path:
                return
            
            # Export to PDF
            success, message = ExportService.export_clients_to_pdf(clients, file_path)
            
            if success:
                QMessageBox.information(
                    self,
                    TranslationService.get("dialogs.success", "Success"),
                    message
                )
            else:
                QMessageBox.critical(
                    self,
                    TranslationService.get("dialogs.error", "Error"),
                    message
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                TranslationService.get("dialogs.error", "Error"),
                TranslationService.get("messages.export_error", "Error exporting PDF: ") + str(e)
            )
    
    def handle_backup(self):
        """
        Handle backup button click.
        Opens file dialog and creates JSON backup of all data.
        """
        try:
            # Open file dialog to choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                TranslationService.get("dialogs.backup", "Create Backup"),
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json)"
            )
            
            if not file_path:
                return
            
            # Create backup
            success, message = ExportService.backup_to_json(self.db, file_path)
            
            if success:
                QMessageBox.information(
                    self,
                    TranslationService.get("dialogs.success", "Success"),
                    message
                )
            else:
                QMessageBox.critical(
                    self,
                    TranslationService.get("dialogs.error", "Error"),
                    message
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                TranslationService.get("dialogs.error", "Error"),
                TranslationService.get("messages.backup_error", "Error creating backup: ") + str(e)
            )
