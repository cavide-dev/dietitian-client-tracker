from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QDialog, QMenu, QLabel
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QDate, QTimer
from bson.objectid import ObjectId
from datetime import datetime
from app.database import get_database
from app.views.measurement_dialog import MeasurementDialog
from app.views.stats_card_widget import StatsCard, StatsCardContainer
from app.views.chart_widget import TrendChart
import os
import sys
import pymongo
class MainController(QMainWindow):
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
        
        # Load dashboard and clients table asynchronously (100ms delay)
        # This ensures MainWindow opens immediately without freezing
        QTimer.singleShot(100, self.load_dashboard)
        QTimer.singleShot(150, self.load_clients_table)
        
        # --- 4. NAVIGATION BUTTONS (Menu Connections) ---
        self.btn_dashboard.clicked.connect(self.show_dashboard)
        self.btn_clients.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        self.btn_diet_plans.clicked.connect(self.switch_to_diet_page)
        self.btn_settings.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_settings))
        
        # Logout button handler
        self.btn_logout.clicked.connect(self.handle_logout)
        
        # Double click the list
        self.tableWidget.cellDoubleClicked.connect(self.open_client_detail)
        # Back to list
        self.btn_back_to_list.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        # Search bar connection
        self.search_clients.textChanged.connect(self.filter_clients_by_search)
        # --- 5. CLIENT OPERATIONS (Add/Delete/Cancel/Save/Edit) ---
        #Add
        self.btn_add_new.clicked.connect(self.prepare_add_mode)
        #Cancel(Smart Navigation)
        self.btn_cancel.clicked.connect(self.handle_cancel)
        #Save
        self.btn_save.clicked.connect(self.save_client)
        #Delete
        self.btn_delete.clicked.connect(self.delete_client)
        #Edit
        self.btn_edit.clicked.connect(self.prepare_edit_mode)

        # --- MEASUREMENT BUTTONS ---
        self.btn_add_measurement.clicked.connect(self.open_add_measurement_dialog)
        # Enable custom right-click menu
        self.table_measurements.setContextMenuPolicy(Qt.CustomContextMenu)
        # Connect the signal to our function
        self.table_measurements.customContextMenuRequested.connect(self.show_context_menu)
        # Double-click to edit measurement
        self.table_measurements.cellDoubleClicked.connect(self.open_edit_measurement_dialog)
        
        
        # DIET PAGE CONNECTIONS 
        
        # 1. Dropdown Setup
        self.load_client_dropdown()
        self.cmb_client_select.currentIndexChanged.connect(self.update_selected_client_from_dropdown)

        # 2. Navigation Buttons
        
        self.btn_new_diet.clicked.connect(self.prepare_add_diet_mode)
        self.table_diet_history.cellDoubleClicked.connect(self.open_diet_detail)
        self.btn_back_to_diet_list.clicked.connect(lambda: self.stack_diet_sub.setCurrentIndex(0))

        # Save button - handles both NEW and UPDATE based on current_diet_id
        self.btn_save_diet.clicked.connect(self.handle_diet_save)

        # Delete button for diet
        if hasattr(self, 'btn_delete_diet'):
            self.btn_delete_diet.clicked.connect(self.delete_diet_plan_from_detail)
        
        # --- Default View Settings ---
        self.stack_diet_sub.setCurrentIndex(0)

        self.init_ui_logic()
        

    def load_clients_table(self):
        """
        Fetches client data from MongoDB and configures the table 
        for multi-selection and optimal layout.
        
        Only shows clients belonging to the current user.
        """
        if self.db is None:
            return

        # 1. Fetch Data (only for current user)
        clients_collection = self.db['clients']
        # Filter clients by current dietician username
        query = {}
        if self.current_user:
            query = {"dietician_username": self.current_user.get("username")}
        all_clients = list(clients_collection.find(query))
        
        # 2. Configure Table Layout
        self.tableWidget.setRowCount(len(all_clients))
        self.tableWidget.setColumnCount(3)
        self.tableWidget.setHorizontalHeaderLabels(["Full Name", "Phone", "Notes"])
        
        # UX: Stretch columns to fill the window
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 3. Configure Selection Mode (New Feature)
        # SelectRows: Clicking a cell selects the entire row.
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # ExtendedSelection: Allows selecting multiple rows using Ctrl or Shift keys.
        self.tableWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # 4. Populate Table
        for row_index, client in enumerate(all_clients):
            # --- Column 0: Name & Hidden ID ---
            name_value = client.get("full_name", "-")
            name_item = QTableWidgetItem(name_value)
            
            # HIDDEN ID STRATEGY:
            # We store the MongoDB '_id' inside the item data (UserRole).
            # It is invisible to the user but accessible via code.
            client_id = str(client.get("_id"))
            name_item.setData(Qt.UserRole, client_id)
            
            self.tableWidget.setItem(row_index, 0, name_item)
            
            # --- Column 1: Phone ---
            phone_value = client.get("phone", "-")
            phone_item = QTableWidgetItem(phone_value)
            self.tableWidget.setItem(row_index, 1, phone_item)
            
            # --- Column 2: Notes ---
            note_value = client.get("notes", "")
            note_item = QTableWidgetItem(note_value)
            self.tableWidget.setItem(row_index, 2, note_item)

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
            
            # Total Measurements (only for current user's clients)
            total_measurements = self.db['measurements'].count_documents(user_filter)
            self.label_total_measurements.setText(str(total_measurements))
            
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
                activity_text = f"✓ {client.get('full_name', 'Unknown')} - Client added"
                self.list_recent_activity.addItem(activity_text)
            
            # Get recent measurements (últimas 3 añadidas)
            recent_measurements = list(self.db['measurements'].find().sort("_id", -1).limit(3))
            for measurement in recent_measurements:
                # Find client name for this measurement
                client = self.db['clients'].find_one({"_id": measurement.get('client_id')})
                client_name = client.get('full_name', 'Unknown') if client else 'Unknown'
                activity_text = f"✓ {client_name} - Measurement added"
                self.list_recent_activity.addItem(activity_text)
            
            # Get recent diet plans (últimos 2 creados)
            recent_diets = list(self.db['diet_plans'].find().sort("_id", -1).limit(2))
            for diet in recent_diets:
                # Find client name for this diet
                client = self.db['clients'].find_one({"_id": diet.get('client_id')})
                client_name = client.get('full_name', 'Unknown') if client else 'Unknown'
                activity_text = f"✓ {client_name} - Diet plan created"
                self.list_recent_activity.addItem(activity_text)
            
            # If no activity, show message
            if self.list_recent_activity.count() == 0:
                self.list_recent_activity.addItem("No recent activity yet")
                
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            self.list_recent_activity.addItem(f"Error loading activity: {str(e)}")

    def show_dashboard(self):
        """
        Show dashboard page and load fresh data.
        Called when Dashboard button is clicked.
        """
        self.load_dashboard()
        self.stackedWidget.setCurrentWidget(self.page_dashboard)

    def filter_clients_by_search(self, search_text):
        """
        Filters the clients table based on search input (real-time).
        Shows/hides rows matching the search term in client names.
        """
        search_text = search_text.lower().strip()
        
        for row in range(self.tableWidget.rowCount()):
            # Get the client name from column 0
            name_item = self.tableWidget.item(row, 0)
            if name_item:
                client_name = name_item.text().lower()
                # Show row if matches search, hide otherwise
                if search_text in client_name:
                    self.tableWidget.setRowHidden(row, False)
                else:
                    self.tableWidget.setRowHidden(row, True)
            else:
                # If no name found, hide the row
                self.tableWidget.setRowHidden(row, True)

    def save_client(self):
        """
        Saves the client. 
        Handles INSERT (New) -> Redirects to List.
        Handles UPDATE (Edit) -> Redirects back to Detail Page.
        """
        # 1. Gather Data
        full_name = self.txt_name.text().strip()
        phone = self.txt_phone.text().strip()
        notes = self.txt_notes.toPlainText().strip()

        try:
            birth_date = self.date_birth_add.date().toString("yyyy-MM-dd")
        except Exception:
            # If error occurs, fallback to today's date (prevent crash)
            birth_date = QDate.currentDate().toString("yyyy-MM-dd")

        if not full_name:
            QMessageBox.warning(self, "Warning", "Name cannot be empty!")
            return
        if not phone:
            QMessageBox.warning(self, "Validation Error", "Phone number cannot be empty!")
            return

        if self.db is not None:
            try:
                client_data = {
                    "full_name": full_name, 
                    "phone": phone, 
                    "notes": notes,
                    "birth_date": birth_date,
                    "dietician_username": self.current_user.get("username") if self.current_user else None
                }

                # --- DECISION TIME ---
                if self.current_client_id is None:

                    client_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # SCENARIO 1: NEW CLIENT (INSERT)
                    self.db['clients'].insert_one(client_data)
                    QMessageBox.information(self, "Success", "Client added successfully!")
                    
                    # Logic: Clear everything and go to LIST
                    self.prepare_add_mode() 
                    self.load_clients_table()
                    self.stackedWidget.setCurrentWidget(self.page_clients)

                else:
                    # SCENARIO 2: EXISTING CLIENT (UPDATE)
                    self.db['clients'].update_one(
                        {'_id': self.current_client_id},
                        {'$set': client_data}
                    )
                    QMessageBox.information(self, "Success", "Client updated successfully!")
                    
                    # Logic: Update Detail View & Go back to DETAIL PAGE
                    
                    # A. Update the labels on the Detail Page immediately
                    # So the user sees the changes right away without re-fetching.
                    self.lbl_client_name.setText(full_name)
                    self.lbl_client_phone.setText(phone)
                    self.lbl_client_notes.setText(notes)
                    
                    # B. Refresh the main table in the background
                    self.load_clients_table()
                    
                    # C. Go back to Detail Page (NOT the List)
                    self.stackedWidget.setCurrentWidget(self.page_client_detail)
                    
                    # Note: We do NOT call prepare_add_mode() here, 
                    # because we want to keep the current_client_id in memory 
                    # while we are looking at the detail page.

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save: {e}")

    def delete_client(self):
        """
        Deletes selected client(s) from the database.
        Supports BULK DELETE (Multiple selections).
        """
        # 1. Get Selected Rows
        # Returns a list of indices for all selected rows.
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select at least one client to delete!")
            return

        # 2. Confirmation Dialog
        count = len(selected_rows)
        message = f"Are you sure you want to delete {count} client(s)?"
        
        # Default button is set to 'No' for safety (Defensive Design).
        reply = QMessageBox.question(self, 'Confirm Delete', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        # 3. Harvest IDs
        # Collects the hidden MongoDB IDs from the selected rows.
        ids_to_delete = []
        
        for row_obj in selected_rows:
            row_index = row_obj.row()
            # Retrieve the item from the first column (where we hid the ID)
            name_item = self.tableWidget.item(row_index, 0)
            client_id_str = name_item.data(Qt.UserRole)
            
            if client_id_str:
            # Convert String ID back to MongoDB ObjectId
                try:
                    ids_to_delete.append(ObjectId(client_id_str))
                except Exception as e:
                    print(f"Warning: Could not convert ID '{client_id_str}': {e}")
                    continue

        # 4. Perform Bulk Delete
        if self.db is not None and ids_to_delete:
            try:
                # Use the '$in' operator to delete multiple documents in one query.
                result = self.db['clients'].delete_many({
                    '_id': {'$in': ids_to_delete}
                })
                
                # 5. Success & Refresh
                QMessageBox.information(self, "Success", f"{result.deleted_count} clients deleted successfully.")
                self.load_clients_table()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete: {e}")

    def open_client_detail(self, row, column):
        """
        Triggered when a cell is double-clicked.
        Fetches the client data using the hidden ID and displays the Detail Page.

        Args:
            row (int): The index of the clicked row.
            column (int): The index of the clicked column (Required by Qt signal, though unused here).
        """
        # 1. Retrieve the Hidden ID
        # We always look at column 0 because that's where we hid the ID.
        # Even if the user clicked on column 2 (Notes), we need the ID from column 0.
        self.hide_measurements_empty_state()  # Show measurements table when opening client detail
        name_item = self.tableWidget.item(row, 0)
        client_id_str = name_item.data(Qt.UserRole)
        
        # Safety Check: If there's no ID, stop.
        if not client_id_str:
            return
    
        try:
            self.current_client_id = ObjectId(client_id_str)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Invalid client ID format: {e}")
            return

        # 2. Fetch Data from Database
        if self.db is not None:
            # Convert string ID to MongoDB ObjectId
            client = self.db['clients'].find_one({'_id': ObjectId(client_id_str)})
            
            if client:
                # 3. Populate the UI Labels
                # We use .get() to avoid errors if a field is missing.
                
                # Header (Big Name)
                full_name = client.get('full_name', 'Unknown')
                self.lbl_client_name.setText(full_name)
                
                # Phone Number
                phone = client.get('phone', '-')
                self.lbl_client_phone.setText(phone)
                
                # Notes (Handles long text automatically thanks to WordWrap)
                notes = client.get('notes', 'No notes.')
                self.lbl_client_notes.setText(notes)

                # Age label (calculated from birth date)
                birth_date = client.get('birth_date', '')
                if birth_date:
                    age = self.calculate_age(birth_date)
                    if age is not None:
                        self.lbl_age.setText(f"Age: {age}")
                    else:
                        self.lbl_age.setText("Age: -")
                else:
                    self.lbl_age.setText("Age: -")
                
                # 4. Switch the View
                # Change the visible page to the Detail Page.
                self.stackedWidget.setCurrentWidget(self.page_client_detail)
                # Clear the old Stats Cards
                tab_overview = self.tabWidget.widget(0)
                if self.stats_container is not None:
                    self.stats_container.clear_cards()
                    tab_overview.layout().removeWidget(self.stats_container)
                    self.stats_container.deleteLater()
                    self.stats_container = None
                                
                # Refresh the measurements list
                self.load_client_measurements()

                # Stats Cards - Compare last 2 measurements
                measurements = self.get_client_history(self.current_client_id)
                # Stats Cards - update or create
                if len(measurements) >= 2:
                    self.stats_container = StatsCardContainer()
                    tab_overview.layout().insertWidget(0, self.stats_container)
                    
                    latest = measurements[0]
                    previous = measurements[1]
                    
                    weight_change = latest.get('weight', 0) - previous.get('weight', 0)
                    fat_change = latest.get('body_fat_ratio', 0) - previous.get('body_fat_ratio', 0)
                    muscle_change = latest.get('muscle_mass', 0) - previous.get('muscle_mass', 0)
                    
                    self.stats_container.add_stats_card("Weight", f"{latest.get('weight', 0)}", weight_change, " kg")
                    self.stats_container.add_stats_card("Body Fat", f"{latest.get('body_fat_ratio', 0)}", fat_change, "%")
                    self.stats_container.add_stats_card("Muscle", f"{latest.get('muscle_mass', 0)}", muscle_change, " kg")
                    
                    self.stats_container.update()
                    tab_overview.update()
                else:
                    if self.stats_container is not None:
                        tab_overview.layout().removeWidget(self.stats_container)
                        self.stats_container.deleteLater()
                        self.stats_container = None
                
                # Trend chart - DELETE OLD, CREATE NEW
                if self.trend_chart is not None:
                    tab_overview.layout().removeWidget(self.trend_chart)
                    self.trend_chart.deleteLater()
                    self.trend_chart = None
                
                self.trend_chart = TrendChart()
                tab_overview.layout().insertWidget(1, self.trend_chart)
                self.trend_chart.plot_trends(measurements)
                
                # Final force update
                tab_overview.update()
            else:
                QMessageBox.warning(self, "Error", "Client not found in database!")

    def calculate_age(self, birth_date_str):
        """
        Calculate age from birth date string (format: yyyy-MM-dd).
        
        Args:
            birth_date_str (str): Birth date in yyyy-MM-dd format
            
        Returns:
            int: Age in years, or None if calculation fails
        """
        from datetime import datetime
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except:
            return None    

    def prepare_add_mode(self):
        """
        Prepares the form for adding a NEW client.
        Clears all input fields and resets the internal state ID.
        """
        # 1. Reset the State (Memory)
        # CRITICAL: We set this to None. This tells the 'save_client' function 
        # that we are performing an INSERT operation, not an UPDATE.
        self.current_client_id = None
        
        # 2. Clear UI Fields (Wipe the slate clean)
        self.txt_name.clear()
        self.txt_phone.clear()
        self.txt_notes.clear()
        
        # 3. Switch View
        # Navigate to the form page so the user can start typing.
        self.stackedWidget.setCurrentWidget(self.page_add_client)

    def prepare_edit_mode(self):
        """
        Prepares the form for EDITING an existing client.
        Fetches the latest data from the database and pre-fills the input fields.
        """
        # Safety Check: Do we have a target ID in memory?
        # This ID is usually set by the 'open_client_detail' function.
        if not self.current_client_id:
            return

        # 1. Fetch Fresh Data
        # We go to the database again to ensure we have the most up-to-date info.
        if self.db is not None:
            client = self.db['clients'].find_one({'_id': self.current_client_id})
            
            if client:
                # 2. Pre-fill the Form (Populate Fields)
                # We use .get("key", "") to safely retrieve values. 
                # If a key is missing, it returns an empty string instead of crashing.
                self.txt_name.setText(client.get("full_name", ""))
                self.txt_phone.setText(client.get("phone", ""))
                self.txt_notes.setPlainText(client.get("notes", ""))
                
                # 3. Switch View
                # Show the form page, now filled with the client's data.
                self.stackedWidget.setCurrentWidget(self.page_add_client)

    def handle_cancel(self):
        """
        Handles the Cancel button click event with context awareness.
        
        Navigation Logic:
        1. If in EDIT Mode (ID exists): Returns to the Client Detail page.
           (User wants to see the client profile again).
        2. If in ADD Mode (No ID): Returns to the Main Client List.
           (User gave up on creating a new client).
        """
        # Context Check: Do we have a client ID in memory?
        if self.current_client_id is not None:
            # SCENARIO: Editing an existing client.
            # Action: Go back to the 'Detail View' of that client.
            self.stackedWidget.setCurrentWidget(self.page_client_detail)

        else:
            # SCENARIO: Adding a new client.
            # Action: Go back to the main 'Clients Table'.
            self.stackedWidget.setCurrentWidget(self.page_clients)

    def get_client_history(self, client_id):
        """
        Fetches all measurement records for a specific client.
        
        Args:
            client_id (ObjectId): The unique ID of the client.

        Returns:
            list: A list of measurement documents sorted by date (newest first).
        """
        if self.db is None:
            return []
        
        # Query the 'measurements' collection for records belonging to this client
        cursor = self.db['measurements'].find({'client_id': client_id})
        
        # Sort the results by 'date' in descending order (-1)
        # This ensures the most recent measurements appear at the top
        measurements = list(cursor.sort('date', -1))
        
        return measurements
    
    def add_measurement_entry(self, client_id, data):
        """
        Inserts a new measurement record into the database.

        Args:
            client_id (ObjectId): The unique ID of the client.
            data (dict): A dictionary containing measurement details 
                         (weight, height, fat ratio, metabolic age, etc.).

        Returns:
        bool: True if the operation was successful, False otherwise.
        Inserts a new measurement record into the database.
        
        Data Structure Strategy:
        - Primary Metrics (Weight, BMR, Waist, Hip): Stored at ROOT level for easy access in tables.
        - Secondary Metrics (Chest, Arm, Thigh): Stored in a NESTED dictionary to keep the document clean.
        """
        if self.db is None or not client_id:
            return False

        try:
            # Prepare the document structure matching the database schema
            measurement_record = {
                "client_id": client_id,
                "dietician_username": self.current_user.get("username") if self.current_user else None,
                "created_at": datetime.now(),     # System timestamp for audit
                "date": data.get("date"),         # User-selected date
                
                # --- 1. BASIC METRICS (Root Level) ---
                "weight": data.get("weight"),
                "height": data.get("height"),
                
                # --- 2. BODY COMPOSITION (Root Level) ---
                "body_fat_ratio": data.get("body_fat_ratio"),
                "muscle_mass": data.get("muscle_mass"),
                "visceral_fat": data.get("visceral_fat"),
                "metabolic_age": data.get("metabolic_age"),
                "water_ratio": data.get("water_ratio"),
                "bmr": data.get("bmr"),           # Important for analysis
                
                # --- 3. PRIMARY CIRCUMFERENCES (Root Level) ---
                # Kept at root because Waist is shown in the main table.
                # Hip is kept here too, as it's often paired with Waist (WHR).
                "waist": data.get("waist"),
                "hip": data.get("hip"),
                
                # --- 4. SECONDARY MEASUREMENTS (Nested Level) ---
                # Stored inside a sub-dictionary to organize detailed data.
                # These are easily accessible for future charts/reports.
                "measurements_extra": {
                    "chest": data.get("chest"),
                    "arm": data.get("arm"),
                    "thigh": data.get("thigh")
                },
                
                # --- 5. NOTES ---
                "notes": data.get("notes")
            }

            # Insert the document into the 'measurements' collection
            self.db['measurements'].insert_one(measurement_record)
            print(f"Measurement added successfully for client: {client_id}")
            return True

        except Exception as e:
            print(f"Error adding measurement: {e}")
            return False
        
    def open_add_measurement_dialog(self):
        """
        Opens the popup window to add a new measurement for the selected client.
        Checks if a client is selected, opens the dialog, and saves the data if confirmed.
        """
        if not self.current_client_id:
            print("Error: No client selected.")
            return

        # Initialize the dialog with the current controller as parent
        dialog = MeasurementDialog(self)
        
        # Execute the dialog and wait for user action (Save or Cancel)
        if dialog.exec_() == QDialog.Accepted:
            # Retrieve data from the dialog form
            data = dialog.get_data()
            
            # Attempt to save the data to the database
            success = self.add_measurement_entry(self.current_client_id, data)
            
            if success:
                print("Measurement saved successfully.")
                # Refresh the measurements list (Tab 2)
                self.load_client_measurements()
                
                # REFRESH TAB 1 - Stats and Chart
                measurements = self.get_client_history(self.current_client_id)
                tab_overview = self.tabWidget.widget(0)
                
                # Remove old Stats container and force layout update
                if self.stats_container is not None:
                    tab_overview.layout().removeWidget(self.stats_container)
                    self.stats_container.deleteLater()
                    self.stats_container = None
                    tab_overview.layout().update()  # Force layout update
                
                # Recreate Stats container if we have enough data
                if len(measurements) >= 2:
                    self.stats_container = StatsCardContainer()
                    tab_overview.layout().insertWidget(0, self.stats_container)
                    
                    latest = measurements[0]
                    previous = measurements[1]
                    
                    weight_change = latest.get('weight', 0) - previous.get('weight', 0)
                    fat_change = latest.get('body_fat_ratio', 0) - previous.get('body_fat_ratio', 0)
                    muscle_change = latest.get('muscle_mass', 0) - previous.get('muscle_mass', 0)
                    
                    self.stats_container.add_stats_card("Weight", f"{latest.get('weight', 0)}", weight_change, " kg")
                    self.stats_container.add_stats_card("Body Fat", f"{latest.get('body_fat_ratio', 0)}", fat_change, "%")
                    self.stats_container.add_stats_card("Muscle", f"{latest.get('muscle_mass', 0)}", muscle_change, " kg")
                    
                    # Force widget repaint
                    self.stats_container.update()
                    tab_overview.update()
                
                # Remove old Chart and recreate
                if self.trend_chart is not None:
                    tab_overview.layout().removeWidget(self.trend_chart)
                    self.trend_chart.deleteLater()
                    self.trend_chart = None
                    tab_overview.layout().update()  # Force layout update
                
                self.trend_chart = TrendChart()
                tab_overview.layout().insertWidget(1, self.trend_chart)
                self.trend_chart.plot_trends(measurements)
                
                # Final force update
                tab_overview.update()
                self.tabWidget.widget(0).update()
            else:
                print("Failed to save measurement.")

    def open_edit_measurement_dialog(self, row, column):
        """
        Opens the measurement dialog in edit mode for the selected row.
        Fetches existing data and allows user to update it.
        """
        if not self.current_client_id:
            return
        
        try:
            # Get measurement ID from hidden UserRole in first column
            id_item = self.table_measurements.item(row, 0)
            if not id_item:
                return
            
            measurement_id_str = id_item.data(Qt.UserRole)
            if not measurement_id_str:
                return
            
            # Fetch measurement from database
            measurement = self.db['measurements'].find_one({"_id": ObjectId(measurement_id_str)})
            
            if not measurement:
                return
            
            # Prepare data for dialog (convert ObjectId and datetime to Python types)
            measurement_data = {
                'date': self._parse_date_value(measurement.get('date', datetime.now())),
                'weight': measurement.get('weight', 0),
                'height': measurement.get('height', 0),
                'body_fat': measurement.get('body_fat', 0),
                'muscle': measurement.get('muscle', 0),
                'metabolic_age': measurement.get('metabolic_age', 0),
                'bmr': measurement.get('bmr', 0),
                'visceral_fat': measurement.get('visceral_fat', 0),
                'water_ratio': measurement.get('water_ratio', 0),
                'waist': measurement.get('waist', 0),
                'hip': measurement.get('hip', 0),
                'chest': measurement.get('chest', 0),
                'arm': measurement.get('arm', 0),
                'thigh': measurement.get('thigh', 0),
                'notes': measurement.get('notes', ''),
                '_id': measurement_id_str  # Store ID for update
            }
            
            # Open dialog in edit mode
            dialog = MeasurementDialog(self, measurement_data)
            
            if dialog.exec_() == QDialog.Accepted:
                # Get updated values from dialog
                updated_data = {
                    'weight': dialog.input_weight.value(),
                    'height': dialog.input_height.value(),
                    'body_fat': dialog.input_fat.value(),
                    'muscle': dialog.input_muscle.value(),
                    'metabolic_age': int(dialog.input_metabolic_age.value()),
                    'bmr': int(dialog.input_bmr.value()),
                    'visceral_fat': dialog.input_visceral.value(),
                    'water_ratio': dialog.input_water.value(),
                    'waist': dialog.input_waist.value(),
                    'hip': dialog.input_hip.value(),
                    'chest': dialog.input_chest.value(),
                    'arm': dialog.input_arm.value(),
                    'thigh': dialog.input_thigh.value(),
                    'notes': dialog.input_notes.toPlainText()
                }
                
                # Update database
                self.db['measurements'].update_one(
                    {"_id": ObjectId(measurement_id_str)},
                    {"$set": updated_data}
                )
                
                # Refresh everything
                self.load_client_measurements()
                self.refresh_stats_and_chart()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not edit measurement: {e}")
            print(f"Error in open_edit_measurement_dialog: {e}")

    def load_client_measurements(self):
        """
        Fetches the measurement history for the selected client and populates the table.
        
        Table Column Mapping (Based on latest design):
        0: Date
        1: Weight (kg)
        2: Waist (cm)       <-- New
        3: Body Fat (%)
        4: Muscle (kg)
        5: Metabolic Age    <-- Restored
        6: BMR (kcal)       <-- New
        """
        self.hide_measurements_empty_state()  # Show the table
        # 1. Validation: Ensure a client is selected
        if not self.current_client_id:
            return

        # 2. Fetch history from database (Assuming get_client_history is defined)
        history = self.get_client_history(self.current_client_id)
        
        # 3. Clear existing rows in the table to prevent duplication
        self.table_measurements.setRowCount(0)
        
        # 4. Loop through the history and populate rows
        # NOTE: history is already sorted by date DESC (newest first) from get_client_history()
        # But we need to insert all rows at index 0 to keep newest at the TOP visually
        # This way each new row pushes older rows down
        for data in reversed(history):  # Reverse to get oldest first, then newest will be inserted at top
            self.table_measurements.insertRow(0)  # Always insert at top
            
            # --- COLUMN 0: DATE (With Hidden ID) ---
            date_val = data.get("date", "-")
            # Format date properly
            if isinstance(date_val, datetime):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)
            date_item = QTableWidgetItem(date_str)

            
            # [CRITICAL] Store the MongoDB '_id' as hidden data for Deletion/Editing logic
            measurement_id = str(data.get('_id'))
            date_item.setData(Qt.UserRole, measurement_id) 
            
            self.table_measurements.setItem(0, 0, date_item)
            
            # --- COLUMN 1: WEIGHT (kg) ---
            weight_val = str(data.get("weight", "-"))
            self.table_measurements.setItem(0, 1, QTableWidgetItem(weight_val))
            
            # --- COLUMN 2: WAIST (cm) [NEW] ---
            # Using .get() ensures it defaults to "-" if 'waist' data doesn't exist yet
            waist_val = str(data.get("waist", "-"))
            self.table_measurements.setItem(0, 2, QTableWidgetItem(waist_val))
            
            # --- COLUMN 3: BODY FAT (%) ---
            fat_val = str(data.get("body_fat_ratio", "-"))
            self.table_measurements.setItem(0, 3, QTableWidgetItem(fat_val))
            
            # --- COLUMN 4: MUSCLE MASS (kg) ---
            muscle_val = str(data.get("muscle_mass", "-"))
            self.table_measurements.setItem(0, 4, QTableWidgetItem(muscle_val))

            # --- COLUMN 5: METABOLIC AGE ---
            metabolic_val = str(data.get("metabolic_age", "-"))
            self.table_measurements.setItem(0, 5, QTableWidgetItem(metabolic_val))

            # --- COLUMN 6: BMR (kcal) [NEW] ---
            bmr_val = str(data.get("bmr", "-"))
            self.table_measurements.setItem(0, 6, QTableWidgetItem(bmr_val))

       # --- TABLE STYLING ---
        header = self.table_measurements.horizontalHeader()

        # 1. ResizeToContents: Automatically adjusts each column width based on the text length.
        # This ensures headers like "Metabolic Age" are fully visible and not cut off.
        header.setSectionResizeMode(QHeaderView.Stretch)
        # header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) 

        # 2. StretchLastSection: Forces the very last column (BMR) to extend 
        header.setStretchLastSection(False)

        # --- ROW / VISUAL IMPROVEMENTS ---
        self.table_measurements.setAlternatingRowColors(True)
        self.table_measurements.verticalHeader().setVisible(False)
        self.table_measurements.setShowGrid(True)

        # If no measurements were loaded, show empty state
        if self.table_measurements.rowCount() == 0:
            self.show_measurements_empty_state()


    def delete_measurement(self):
        """
        Deletes the selected measurement from the database after confirmation.
        After deletion, refreshes Tab 1 (Stats and Chart) and Tab 2 (Measurements table).
        """
        # 1. Check if a row is selected
        current_row = self.table_measurements.currentRow()
        if current_row < 0:
            return

        # 2. Retrieve the hidden ID from the Date column (Column 0)
        date_item = self.table_measurements.item(current_row, 0)
        measurement_id = date_item.data(Qt.UserRole)

        if not measurement_id:
            return

        # 3. Delete from Database
        try:
            try:
                obj_id = ObjectId(measurement_id)
            except Exception as e:
                print(f"Error: Invalid measurement ID format: {e}")
                return
            
            result = self.db['measurements'].delete_one({'_id': obj_id})

            if result.deleted_count > 0:
                print(f"Deleted measurement ID: {measurement_id}")
                
                # 4. Refresh Tab 2 (Measurements table)
                self.load_client_measurements()
                
                # 5. Refresh Tab 1 (Stats and Chart)
                measurements = self.get_client_history(self.current_client_id)
                tab_overview = self.tabWidget.widget(0)
                
                # Remove old Stats container
                if self.stats_container is not None:
                    tab_overview.layout().removeWidget(self.stats_container)
                    self.stats_container.deleteLater()
                    self.stats_container = None
                    tab_overview.layout().update()
                
                # Recreate Stats container if we have enough data
                if len(measurements) >= 2:
                    self.stats_container = StatsCardContainer()
                    tab_overview.layout().insertWidget(0, self.stats_container)
                    
                    latest = measurements[0]
                    previous = measurements[1]
                    
                    weight_change = latest.get('weight', 0) - previous.get('weight', 0)
                    fat_change = latest.get('body_fat_ratio', 0) - previous.get('body_fat_ratio', 0)
                    muscle_change = latest.get('muscle_mass', 0) - previous.get('muscle_mass', 0)
                    
                    self.stats_container.add_stats_card("Weight", f"{latest.get('weight', 0)}", weight_change, " kg")
                    self.stats_container.add_stats_card("Body Fat", f"{latest.get('body_fat_ratio', 0)}", fat_change, "%")
                    self.stats_container.add_stats_card("Muscle", f"{latest.get('muscle_mass', 0)}", muscle_change, " kg")
                    
                    self.stats_container.update()
                    tab_overview.update()
                
                # Remove old Chart and recreate
                if self.trend_chart is not None:
                    tab_overview.layout().removeWidget(self.trend_chart)
                    self.trend_chart.deleteLater()
                    self.trend_chart = None
                    tab_overview.layout().update()
                
                self.trend_chart = TrendChart()
                tab_overview.layout().insertWidget(1, self.trend_chart)
                self.trend_chart.plot_trends(measurements)
                
                # Final force update
                tab_overview.update()
                
            else:
                print("Error: Could not find document to delete.")
                
        except Exception as e:
            print(f"Error deleting measurement: {e}")

    def refresh_stats_and_chart(self):
        """
        Helper function to refresh both Stats Cards and Trend Chart.
        Called after measurement add/edit/delete operations.
        """
        measurements = self.get_client_history(self.current_client_id)
        tab_overview = self.tabWidget.widget(0)
        
        # Remove old Stats container
        if self.stats_container is not None:
            tab_overview.layout().removeWidget(self.stats_container)
            self.stats_container.deleteLater()
            self.stats_container = None
            tab_overview.layout().update()
        
        # Recreate Stats container if we have enough data
        if len(measurements) >= 2:
            self.stats_container = StatsCardContainer()
            tab_overview.layout().insertWidget(0, self.stats_container)
            
            latest = measurements[0]
            previous = measurements[1]
            
            weight_change = latest.get('weight', 0) - previous.get('weight', 0)
            fat_change = latest.get('body_fat_ratio', 0) - previous.get('body_fat_ratio', 0)
            muscle_change = latest.get('muscle_mass', 0) - previous.get('muscle_mass', 0)
            
            self.stats_container.add_stats_card("Weight", f"{latest.get('weight', 0)}", weight_change, " kg")
            self.stats_container.add_stats_card("Body Fat", f"{latest.get('body_fat_ratio', 0)}", fat_change, "%")
            self.stats_container.add_stats_card("Muscle", f"{latest.get('muscle_mass', 0)}", muscle_change, " kg")
            
            self.stats_container.update()
            tab_overview.update()
        
        # Remove old Chart and recreate
        if self.trend_chart is not None:
            tab_overview.layout().removeWidget(self.trend_chart)
            self.trend_chart.deleteLater()
            self.trend_chart = None
            tab_overview.layout().update()
        
        self.trend_chart = TrendChart()
        tab_overview.layout().insertWidget(1, self.trend_chart)
        self.trend_chart.plot_trends(measurements)
        
        # Final force update
        tab_overview.update()

    def show_context_menu(self, position):
        """
        Displays a Right-Click context menu on the table.
        Automatically selects the row under the cursor before showing the menu.
        """
        # 1. Identify which cell is under the mouse cursor
        index = self.table_measurements.indexAt(position)

        # 2. If the click is valid (not on empty space), select that cell
        # This prevents accidental deletion of the wrong row
        if index.isValid():
            self.table_measurements.setCurrentCell(index.row(), index.column())
        
        # 3. Create the Context Menu
        menu = QMenu()
        
        # 4. Add "Delete" action to the menu
        delete_action = menu.addAction("Delete Measurement")
        
        # 5. Show the menu at the global mouse position
        action = menu.exec_(self.table_measurements.mapToGlobal(position))
        
        # 6. If user clicked "Delete", trigger the delete function
        if action == delete_action:
            self.delete_measurement()

    def save_diet_plan(self):
        """
        Collects text from diet plan input fields and saves them to the MongoDB database.
        Includes 'Auto-Archiving' logic: Sets old active plans to 'passive' before saving the new one.
        """
        # 1. Validation: Check if a client is selected
        if not self.current_client_id:
            QMessageBox.warning(None, "Warning", "Please select a client first!")
            return

        # 2. Collect Data: Get text from the input fields
        title = self.txt_diet_title.text().strip()
        breakfast = self.txt_breakfast.toPlainText().strip()
        snack_1 = self.txt_snack_1.toPlainText().strip()
        lunch = self.txt_lunch.toPlainText().strip()
        snack_2 = self.txt_snack_2.toPlainText().strip()
        dinner = self.txt_dinner.toPlainText().strip()
        snack_3 = self.txt_snack_3.toPlainText().strip()

        # 3. Validation: Check if the Title is empty
        if not title:
            QMessageBox.warning(None, "Warning", "Please enter a title for the diet plan!")
            return

        # 4. Validation: Check main meals (Breakfast, Lunch, Dinner)
        if not breakfast:
            QMessageBox.warning(None, "Validation Error", "Breakfast cannot be empty!")
            return

        if not lunch:
            QMessageBox.warning(None, "Validation Error", "Lunch cannot be empty!")
            return

        if not dinner:
            QMessageBox.warning(None, "Validation Error", "Dinner cannot be empty!")
            return


        # 5. Prepare Data Package
        diet_data = {
            "client_id": self.current_client_id,
            "dietician_username": self.current_user.get("username") if self.current_user else None,
            "created_at": datetime.now(),
            "title": title,
            "content": {
                "breakfast": breakfast,
                "morning_snack": snack_1,
                "lunch": lunch,
                "afternoon_snack": snack_2,
                "dinner": dinner,
                "evening_snack": snack_3
            },
            "status": "active" # The new plan is always active initially
        }

        # 5. Database Operation
        try:
            # --- AUTO-ARCHIVING LOGIC ---
            # Before adding the new plan, find all currently 'active' plans for this client
            # and update their status to 'passive'.
            self.db['diet_plans'].update_many(
                {"client_id": self.current_client_id, "status": "active"},
                {"$set": {"status": "passive"}}
            )
            
            # Now insert the new 'active' plan
            self.db['diet_plans'].insert_one(diet_data)
            
            # Show success message
            QMessageBox.information(None, "Success", "Diet Plan saved successfully!")
            
            # Clear inputs
            self.clear_diet_inputs()
            
            # --- AFTER SAVE ACTIONS (NEW) ---
            # 1. Refresh the table to show the new diet (and the passive status of old ones)
            self.load_client_diet_plans()
            
            # 2. Automatically return to the Table View (Page 0)
            self.stack_diet_sub.setCurrentIndex(0)
            
        except Exception as e:
            print(f"Error saving diet plan: {e}")
            QMessageBox.critical(None, "Error", f"Could not save diet plan: {e}")

    def clear_diet_inputs(self):
        """
        Helper function to clear all text fields in the diet plan form.
        Called automatically after a successful save.
        """
        self.txt_diet_title.clear()
        self.txt_breakfast.clear()
        self.txt_snack_1.clear()
        self.txt_lunch.clear()
        self.txt_snack_2.clear()
        self.txt_dinner.clear()
        self.txt_snack_3.clear()


    def load_client_dropdown(self):
        """
        Fetches 'full_name' from the database and populates the client selection dropdown
        on the Diet Plans page.
        """
        # Clear the box first to avoid duplicates
        self.cmb_client_select.clear()
        # Add a default empty option
        self.cmb_client_select.addItem("Select Client...", None) 

        try:
            # Fetch only ID and Full Name from MongoDB
            clients = self.db['clients'].find({}, {"_id": 1, "full_name": 1})
            
            for client in clients:
                full_name = client.get("full_name", "")
                
                # Only add if a name exists
                if full_name:
                    client_id = str(client["_id"])
                    # Add Item: Text shown to user, UserRole data (ID) hidden
                    self.cmb_client_select.addItem(full_name, client_id)
                
        except Exception as e:
            print(f"Error loading client dropdown: {e}")

        # Reset dropdown to "Select Client..." on load
        self.cmb_client_select.setCurrentIndex(0)
    
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
            self.empty_state_diet.setStyleSheet("""
                color: #999999;
                font-size: 14px;
                padding: 50px;
            """)
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
            self.empty_state_measurements = QLabel("📊 No measurements recorded. Add your first measurement to get started.")
            self.empty_state_measurements.setAlignment(Qt.AlignCenter)
            self.empty_state_measurements.setStyleSheet("""
                color: #999999;
                font-size: 16px;
                padding: 100px;
            """)
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
        # Retrieve the hidden ID from the selected item
        client_id = self.cmb_client_select.currentData()
        
        if client_id:
            self.current_client_id = client_id
            print(f"Active Client Changed to: {self.current_client_id}")
            self.hide_diet_empty_state()  # Hide the empty state first
            self.load_client_diet_plans() # Then load table data
        else:
            # If "Select Client..." is chosen, reset the ID
            self.current_client_id = None
            self.show_diet_empty_state()  # Show placeholder
    
    def load_client_diet_plans(self):
        """
        Fetches the selected client's diet plans from the database and populates the TableWidget.
        """
        # 1. Clear the Table: Remove all existing rows to start fresh
        self.table_diet_history.setRowCount(0)

        # If no client is selected, stop here
        if not self.current_client_id:
            return

        try:
            # 2. Database Query: Find diets for this client
            # Sort by 'created_at' descending (-1) so the newest is at the top
            diets = self.db['diet_plans'].find(
                {"client_id": self.current_client_id}
            ).sort("created_at", pymongo.DESCENDING)

            # 3. Loop through results and add rows
            for diet in diets:
                # Get the current row count (e.g., 0, then 1, then 2...)
                row_position = self.table_diet_history.rowCount()
                
                # Create a new empty row at that position
                self.table_diet_history.insertRow(row_position)
                
                # --- Prepare Data ---
                # Title
                title = diet.get("title", "No Title")
                
                # Date (Format: YYYY-MM-DD)
                raw_date = diet.get("created_at")
                if raw_date:
                    date_str = raw_date.strftime("%Y-%m-%d")
                else:
                    date_str = "-"
                
                # Status (Active/Archived)
                status = diet.get("status", "Active")
                
                # --- Create Cells (Items) ---
                
                # Determine row color based on status
                if status.lower() == "active":
                    bg_color = QColor(200, 255, 200)  # Light green
                else:  # Archived/Passive
                    bg_color = QColor(220, 220, 220)  # Light gray

                # Column 0: Date
                date_item = QTableWidgetItem(date_str)
                date_item.setBackground(bg_color)
                self.table_diet_history.setItem(row_position, 0, date_item)
                
                # Column 1: Title
                title_item = QTableWidgetItem(title)
                title_item.setBackground(bg_color)
                self.table_diet_history.setItem(row_position, 1, title_item)
                
                # Column 2: Status
                status_item = QTableWidgetItem(status)
                status_item.setBackground(bg_color)
                self.table_diet_history.setItem(row_position, 2, status_item)
                
                # --- CRITICAL STEP: Hidden ID ---
                # We store the Diet's unique ID in the first cell invisibly.
                # This allows us to know WHICH diet to open/edit later.
                self.table_diet_history.item(row_position, 0).setData(Qt.UserRole, str(diet["_id"]))
                
        except Exception as e:
            print(f"Error loading diet table: {e}")

    def switch_to_diet_page(self):
        """
        Switches the main view to the Diet Plans page and resets the 
        internal sub-stack to the 'Table View' (Index 0).
        Ensures the user always sees the list first, not the form.
        """
        # 1. Switch the Main Stacked Widget to the Diet Page
        self.stackedWidget.setCurrentWidget(self.page_diet_plans) 
        
        # 2. Reset the Sub-Stacked Widget to the List/Table View (Page 0)
        # This fixes the issue of getting stuck on the 'Add Diet' form 
        # when navigating back to this page.
        try:
            self.stack_diet_sub.setCurrentIndex(0)
        except Exception as e:
            print(f"Error resetting diet sub-stack: {e}")
        
        self.show_diet_empty_state()  # Show empty state on page entry

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
        header = self.table_diet_history.horizontalHeader()

        # Make all columns share the available width evenly
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Ensure the last column expands to fill any remaining space
        header.setStretchLastSection(True)

        # --- Table Appearance Improvements ---
        # Hide the row index column (cleaner look)
        self.table_diet_history.verticalHeader().setVisible(False)

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
                self.btn_delete_diet.setStyleSheet("background-color: #ff4444; color: white;")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open diet: {e}")
    
    def update_diet_plan(self):
        """
        Updates an existing diet plan.
        Similar to save_diet_plan() but with UPDATE instead of INSERT.
        """
        # 1. Check if we're editing a diet
        if not hasattr(self, 'current_diet_id') or not self.current_diet_id:
            QMessageBox.warning(None, "Error", "No diet plan selected for editing!")
            return
        
        # 2. Collect data
        title = self.txt_diet_title.text().strip()
        breakfast = self.txt_breakfast.toPlainText().strip()
        snack_1 = self.txt_snack_1.toPlainText().strip()
        lunch = self.txt_lunch.toPlainText().strip()
        snack_2 = self.txt_snack_2.toPlainText().strip()
        dinner = self.txt_dinner.toPlainText().strip()
        snack_3 = self.txt_snack_3.toPlainText().strip()
        
        # 3. Validation
        if not title:
            QMessageBox.warning(None, "Validation Error", "Title cannot be empty!")
            return
        
        if not breakfast:
            QMessageBox.warning(None, "Validation Error", "Breakfast cannot be empty!")
            return
        
        if not lunch:
            QMessageBox.warning(None, "Validation Error", "Lunch cannot be empty!")
            return
        
        if not dinner:
            QMessageBox.warning(None, "Validation Error", "Dinner cannot be empty!")
            return
        
        # 4. Prepare updated data
        updated_data = {
            "title": title,
            "content": {
                "breakfast": breakfast,
                "morning_snack": snack_1,
                "lunch": lunch,
                "afternoon_snack": snack_2,
                "dinner": dinner,
                "evening_snack": snack_3
            },
            "updated_at": datetime.now()  # Update timestamp
        }
        
        # 5. Update in database
        try:
            result = self.db['diet_plans'].update_one(
                {'_id': self.current_diet_id},
                {'$set': updated_data}
            )
            
            if result.modified_count > 0:
                QMessageBox.information(None, "Success", "Diet plan updated successfully!")
                self.clear_diet_inputs()
                self.load_client_diet_plans()
                self.stack_diet_sub.setCurrentIndex(0)
                self.current_diet_id = None
            else:
                QMessageBox.warning(None, "Warning", "No changes were made.")
        
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not update diet plan: {e}")

    def delete_diet_plan_from_detail(self):
        """
        Deletes the currently open diet plan after confirmation.
        """
        # 1. Check if we're editing a diet
        if not hasattr(self, 'current_diet_id') or not self.current_diet_id:
            QMessageBox.warning(None, "Error", "No diet plan selected!")
            return
        
        # 2. Confirmation dialog
        reply = QMessageBox.question(
            None,
            'Confirm Delete',
            'Are you sure you want to delete this diet plan?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # 3. Delete from database
        try:
            result = self.db['diet_plans'].delete_one({'_id': self.current_diet_id})
            
            if result.deleted_count > 0:
                QMessageBox.information(None, "Success", "Diet plan deleted successfully!")
                self.clear_diet_inputs()
                self.load_client_diet_plans()
                self.stack_diet_sub.setCurrentIndex(0)
                self.current_diet_id = None
            else:
                QMessageBox.warning(None, "Error", "Could not find diet plan to delete.")
        
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Could not delete diet plan: {e}")

    def handle_diet_save(self):
        """
        Smart save handler - decides whether to INSERT or UPDATE based on current_diet_id.
        """
        if hasattr(self, 'current_diet_id') and self.current_diet_id:
            # Editing mode
            self.update_diet_plan()
        else:
            # New diet mode
            self.save_diet_plan()

    def prepare_add_diet_mode(self):
        """
        Prepares the form for adding a NEW diet plan.
        Clears all fields and disables delete button.
        """
        self.current_diet_id = None
        self.clear_diet_inputs()
        
        # Disable delete button (no diet to delete)
        if hasattr(self, 'btn_delete_diet'):
            self.btn_delete_diet.setEnabled(False)
            self.btn_delete_diet.setStyleSheet("background-color: #cccccc; color: gray;")
        
        # Go to form page
        self.stack_diet_sub.setCurrentIndex(1)

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
        
        # Close the main window
        self.close()
        
        # The login window will appear automatically (run.py handles this)



