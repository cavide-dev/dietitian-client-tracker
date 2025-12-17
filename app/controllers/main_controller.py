from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QDialog, QMenu
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt  
from bson.objectid import ObjectId
from datetime import datetime
from app.database import get_database
from app.views.measurement_dialog import MeasurementDialog
import os

class MainController(QMainWindow):
    def __init__(self):
        """
        Main Application Logic.
        Initializes the UI, database connection, and event handlers.
        """
        super(MainController, self).__init__()
        
        # 1. Load UI File
        # We load the .ui file dynamically relative to this script's location.
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'views', 'main_window.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            print(f"UI Loading Error: {e}")
            return

        # 2. Database Connection & State
        # Establish connection to MongoDB Atlas.
        self.db = get_database()
        self.current_client_id = None

        # 3. Initial Setup
        # Show the dashboard page by default on startup.
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        # Load the table data
        self.load_clients_table()

        # --- 4. NAVIGATION BUTTONS (Menu Connections) ---
        self.btn_dashboard.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_dashboard))
        self.btn_clients.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        self.btn_diet_plans.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_diet_plans))
        self.btn_settings.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_settings))
        # Double click the list
        self.tableWidget.cellDoubleClicked.connect(self.open_client_detail)
        # Back to list
        self.btn_back_to_list.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))

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
        
        # Diet Plan Button Connection
        self.btn_save_diet.clicked.connect(self.save_diet_plan)

        # --- Diet Plan Dropdown Connections ---
        
        # 1. Fill the dropdown when the app starts
        self.load_client_dropdown()
        
        # 2. Update the target client when the user changes the selection
        self.cmb_client_select.currentIndexChanged.connect(self.update_selected_client_from_dropdown)

        self.btn_new_diet.clicked.connect(lambda: self.stack_diet_sub.setCurrentIndex(1))

        self.btn_back_to_diet_list.clicked.connect(lambda: self.stack_diet_sub.setCurrentIndex(0))


    def load_clients_table(self):
        """
        Fetches client data from MongoDB and configures the table 
        for multi-selection and optimal layout.
        """
        if self.db is None:
            return

        # 1. Fetch Data
        clients_collection = self.db['clients']
        all_clients = list(clients_collection.find())
        
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
            # Olur da bir hata olursa bugünün tarihini atayalım (Çökmemesi için)
            from PyQt5.QtCore import QDate
            birth_date = QDate.currentDate().toString("yyyy-MM-dd")

        if not full_name:
            QMessageBox.warning(self, "Warning", "Name cannot be empty!")
            return

        if self.db is not None:
            try:
                client_data = {
                    "full_name": full_name, 
                    "phone": phone, 
                    "notes": notes,
                    "birth_date": birth_date  
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
                ids_to_delete.append(ObjectId(client_id_str))

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
        name_item = self.tableWidget.item(row, 0)
        client_id_str = name_item.data(Qt.UserRole)
        
        # Safety Check: If there's no ID, stop.
        if not client_id_str:
            return
        
        self.current_client_id = ObjectId(client_id_str)

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
                
                # 4. Switch the View
                # Change the visible page to the Detail Page.
                self.stackedWidget.setCurrentWidget(self.page_client_detail)
                # Refresh the measurements list
                self.load_client_measurements()
                
            else:
                QMessageBox.warning(self, "Error", "Client not found in database!")    

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
                # Refresh the measurements list
                self.load_client_measurements()
            else:
                print("Failed to save measurement.")

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
        # 1. Validation: Ensure a client is selected
        if not self.current_client_id:
            return

        # 2. Fetch history from database (Assuming get_client_history is defined)
        history = self.get_client_history(self.current_client_id)
        
        # 3. Clear existing rows in the table to prevent duplication
        self.table_measurements.setRowCount(0)
        
        # 4. Loop through the history and populate rows
        for row_index, data in enumerate(history):
            self.table_measurements.insertRow(row_index)
            
            # --- COLUMN 0: DATE (With Hidden ID) ---
            date_val = data.get("date", "-")
            date_item = QTableWidgetItem(str(date_val))
            
            # [CRITICAL] Store the MongoDB '_id' as hidden data for Deletion/Editing logic
            measurement_id = str(data.get('_id'))
            date_item.setData(Qt.UserRole, measurement_id) 
            
            self.table_measurements.setItem(row_index, 0, date_item)
            
            # --- COLUMN 1: WEIGHT (kg) ---
            weight_val = str(data.get("weight", "-"))
            self.table_measurements.setItem(row_index, 1, QTableWidgetItem(weight_val))
            
            # --- COLUMN 2: WAIST (cm) [NEW] ---
            # Using .get() ensures it defaults to "-" if 'waist' data doesn't exist yet
            waist_val = str(data.get("waist", "-"))
            self.table_measurements.setItem(row_index, 2, QTableWidgetItem(waist_val))
            
            # --- COLUMN 3: BODY FAT (%) ---
            fat_val = str(data.get("body_fat_ratio", "-"))
            self.table_measurements.setItem(row_index, 3, QTableWidgetItem(fat_val))
            
            # --- COLUMN 4: MUSCLE MASS (kg) ---
            muscle_val = str(data.get("muscle_mass", "-"))
            self.table_measurements.setItem(row_index, 4, QTableWidgetItem(muscle_val))

            # --- COLUMN 5: METABOLIC AGE ---
            metabolic_val = str(data.get("metabolic_age", "-"))
            self.table_measurements.setItem(row_index, 5, QTableWidgetItem(metabolic_val))

            # --- COLUMN 6: BMR (kcal) [NEW] ---
            bmr_val = str(data.get("bmr", "-"))
            self.table_measurements.setItem(row_index, 6, QTableWidgetItem(bmr_val))

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


    def delete_measurement(self):
        """
        Deletes the selected measurement from the database after confirmation.
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
            result = self.db['measurements'].delete_one({'_id': ObjectId(measurement_id)})
            
            if result.deleted_count > 0:
                print(f"Deleted measurement ID: {measurement_id}")
                # 4. Refresh the table to show changes
                self.load_client_measurements()
            else:
                print("Error: Could not find document to delete.")
                
        except Exception as e:
            print(f"Error deleting measurement: {e}")

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
        Connected to the 'Save Diet Plan' button.
        """
        # 1. Validation: Check if a client is selected
        if not self.current_client_id:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Warning", "Please select a client first!")
            return

        # 2. Collect Data: Get text from the input fields
        # .strip() removes accidental spaces at the beginning or end
        title = self.txt_diet_title.text().strip()
        breakfast = self.txt_breakfast.toPlainText().strip()
        snack_1 = self.txt_snack_1.toPlainText().strip() # Morning Snack
        lunch = self.txt_lunch.toPlainText().strip()
        snack_2 = self.txt_snack_2.toPlainText().strip() # Afternoon Snack
        dinner = self.txt_dinner.toPlainText().strip()
        snack_3 = self.txt_snack_3.toPlainText().strip() # Evening Snack

        # 3. Validation: Check if the Title is empty (Title is mandatory)
        if not title:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Warning", "Please enter a title for the diet plan!")
            return

        # 4. Prepare Data Package: Create the dictionary for MongoDB
        from datetime import datetime
        diet_data = {
            "client_id": self.current_client_id,   # Links this plan to the selected client
            "created_at": datetime.now(),          # Timestamp for sorting later
            "title": title,                        # The name of the list (e.g., "Detox Week 1")
            "content": {                           # Nested dictionary for meal details
                "breakfast": breakfast,
                "morning_snack": snack_1,
                "lunch": lunch,
                "afternoon_snack": snack_2,
                "dinner": dinner,
                "evening_snack": snack_3
            },
            "status": "active"                     # Default status
        }

        # 5. Database Operation: Insert the data
        try:
            self.db['diet_plans'].insert_one(diet_data)
            
            # Show success message
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(None, "Success", "Diet Plan saved successfully!")
            
            # Clear the inputs after saving (to be ready for a new one)
            self.clear_diet_inputs()
            
        except Exception as e:
            print(f"Error saving diet plan: {e}")
            from PyQt5.QtWidgets import QMessageBox
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
        else:
            # If "Select Client..." is chosen, reset the ID
            self.current_client_id = None
