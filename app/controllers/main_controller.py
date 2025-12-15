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

        # 2. Database Connection
        # Establish connection to MongoDB Atlas.
        self.db = get_database()

        # 3. Initial Setup
        # Show the dashboard page by default on startup.
        self.stackedWidget.setCurrentWidget(self.page_dashboard)
        
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
        Reads input fields, validates data, inserts into MongoDB,
        and refreshes the client list.
        """
        
        # 1. Get Data from Inputs
        # .strip() removes leading/trailing whitespace
        full_name = self.txt_name.text().strip()
        phone = self.txt_phone.text().strip()
        notes = self.txt_notes.toPlainText().strip()

        # 2. Validation
        # Prevent saving if the name field is empty
        if not full_name:
            QMessageBox.warning(self, "Warning", "Name cannot be empty!")
            return

        # 3. Insert into Database
        if self.db is not None:
            try:
                new_client = {
                    "full_name": full_name,
                    "phone": phone,
                    "notes": notes
                }
                
                # Perform the insertion
                self.db['clients'].insert_one(new_client)
                
                # Show Success Message
                QMessageBox.information(self, "Success", "Client added successfully!")
                
                # 4. Cleanup & Navigation
                # Clear the input fields for the next entry
                self.txt_name.clear()
                self.txt_phone.clear()
                self.txt_notes.clear()
                
                # Refresh the table to show the new client
                self.load_clients_table()
                
                # Navigate back to the client list
                self.stackedWidget.setCurrentWidget(self.page_clients)
                
            except Exception as e:
                # Handle database errors gracefully
                QMessageBox.critical(self, "Error", f"Could not save client: {e}")

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