from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt  
from bson.objectid import ObjectId 
import os
from app.database import get_database

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
        #Cancel
        self.btn_cancel.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_clients))
        #Save
        self.btn_save.clicked.connect(self.save_client)
        #Delete
        self.btn_delete.clicked.connect(self.delete_client)
        #Edit
        self.btn_edit.clicked.connect(self.prepare_edit_mode)

        
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

        if not full_name:
            QMessageBox.warning(self, "Warning", "Name cannot be empty!")
            return

        if self.db is not None:
            try:
                client_data = {"full_name": full_name, "phone": phone, "notes": notes}

                # --- DECISION TIME ---
                if self.current_client_id is None:
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