"""
ClientController - Manages all client-related operations.
Responsible for: CRUD operations, listing, searching, and detail views for clients.
"""

from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QAbstractItemView
from PyQt5.QtCore import Qt, QDate
from bson.objectid import ObjectId
from datetime import datetime
from app.services.validation_service import ValidationService
from app.services.calculation_service import CalculationService
from app.i18n.translations import TranslationService


class ClientController:
    """
    Handles all client management operations.
    Works in conjunction with MainController for UI coordination.
    """

    def __init__(self, main_controller):
        """
        Initialize ClientController with reference to main controller.
        
        Args:
            main_controller: Reference to MainController instance for UI access
        """
        self.main = main_controller

    def load_clients_table(self):
        """
        Fetch and display all clients for the current user in the clients table.
        Configures multi-selection and optimal layout.
        """
        if self.main.db is None:
            return

        # Fetch data (only for current user)
        clients_collection = self.main.db['clients']
        query = {}
        if self.main.current_user:
            query = {"dietician_username": self.main.current_user.get("username")}
        all_clients = list(clients_collection.find(query))
        
        # Configure table - Complete reset
        self.main.tableWidget.setColumnCount(0)
        self.main.tableWidget.setRowCount(0)
        
        # Now set new columns
        self.main.tableWidget.setColumnCount(3)
        
        # Use TranslationService for headers
        headers = [
            TranslationService.get("clients.full_name", "Full Name"),
            TranslationService.get("clients.phone", "Phone"),
            TranslationService.get("clients.notes", "Notes")
        ]
        self.main.tableWidget.setHorizontalHeaderLabels(headers)
        self.main.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main.tableWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Now set row count
        self.main.tableWidget.setRowCount(len(all_clients))

        # Populate table
        for row_index, client in enumerate(all_clients):
            name_value = client.get("full_name", "-")
            name_item = QTableWidgetItem(name_value)
            client_id = str(client.get("_id"))
            name_item.setData(Qt.UserRole, client_id)
            self.main.tableWidget.setItem(row_index, 0, name_item)
            
            phone_value = client.get("phone", "-")
            phone_item = QTableWidgetItem(phone_value)
            self.main.tableWidget.setItem(row_index, 1, phone_item)
            
            note_value = client.get("notes", "")
            note_item = QTableWidgetItem(note_value)
            self.main.tableWidget.setItem(row_index, 2, note_item)

    def save_client(self):
        """
        Save client data. Handles both INSERT (new) and UPDATE (existing).
        """
        full_name = self.main.txt_name.text().strip()
        phone = self.main.txt_phone.text().strip()
        notes = self.main.txt_notes.toPlainText().strip()

        try:
            birth_date = self.main.date_birth_add.date().toString("yyyy-MM-dd")
        except Exception:
            birth_date = QDate.currentDate().toString("yyyy-MM-dd")
        if not full_name:
            QMessageBox.warning(self.main, TranslationService.get("common.warning", "Warning"), TranslationService.get("validation.name_empty", "Name cannot be empty!"))
            return
        
        if not phone:
            QMessageBox.warning(self.main, TranslationService.get("common.error", "Validation Error"), TranslationService.get("validation.phone_empty", "Phone number cannot be empty!"))
            return
        
        # Validate using ValidationService
        is_valid_phone, phone_error = ValidationService.validate_phone(phone)
        if not is_valid_phone:
            QMessageBox.warning(self.main, TranslationService.get("common.error", "Validation Error"), f"{TranslationService.get('validation.invalid_phone', 'Invalid phone number:')} {phone_error}")
            return
        
        is_valid_birth_date, birth_date_error = ValidationService.validate_birth_date(birth_date)
        if not is_valid_birth_date:
            QMessageBox.warning(self.main, TranslationService.get("common.error", "Validation Error"), birth_date_error)
            return

        if self.main.db is not None:
            try:
                client_data = {
                    "full_name": full_name, 
                    "phone": phone, 
                    "notes": notes,
                    "birth_date": birth_date,
                    "dietician_username": self.main.current_user.get("username") if self.main.current_user else None
                }

                if self.main.current_client_id is None:
                    # INSERT new client
                    client_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.main.db['clients'].insert_one(client_data)
                    QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("clients.client_added", "Client added successfully!"))
                    self.prepare_add_mode()
                    self.load_clients_table()
                    self.main.stackedWidget.setCurrentWidget(self.main.page_clients)
                else:
                    # UPDATE existing client
                    self.main.db['clients'].update_one(
                        {'_id': self.main.current_client_id},
                        {'$set': client_data}
                    )
                    QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("clients.client_updated", "Client updated successfully!"))
                    self.main.lbl_client_name.setText(full_name)
                    self.main.lbl_client_phone.setText(phone)
                    self.main.lbl_client_notes.setText(notes)
                    self.load_clients_table()
                    self.main.stackedWidget.setCurrentWidget(self.main.page_client_detail)

            except Exception as e:
                QMessageBox.critical(self.main, "Error", f"Could not save: {e}")

    def delete_client(self):
        """
        Delete selected client(s). Supports bulk delete with confirmation.
        """
        selected_rows = self.main.tableWidget.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self.main, "Warning", "Please select at least one client to delete!")
            return

        count = len(selected_rows)
        message = f"Are you sure you want to delete {count} client(s)?"
        reply = QMessageBox.question(self.main, 'Confirm Delete', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        ids_to_delete = []
        for row_obj in selected_rows:
            row_index = row_obj.row()
            name_item = self.main.tableWidget.item(row_index, 0)
            client_id_str = name_item.data(Qt.UserRole)
            
            if client_id_str:
                try:
                    ids_to_delete.append(ObjectId(client_id_str))
                except Exception as e:
                    print(f"Warning: Could not convert ID '{client_id_str}': {e}")
                    continue

        if self.main.db is not None and ids_to_delete:
            try:
                result = self.main.db['clients'].delete_many({'_id': {'$in': ids_to_delete}})
                QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("clients.client_deleted", "Client deleted successfully!"))
                self.load_clients_table()
            except Exception as e:
                QMessageBox.critical(self.main, "Error", f"Could not delete: {e}")

    def open_client_detail(self, row, column):
        """
        Open client detail page when a row is double-clicked.
        """
        self.main.hide_measurements_empty_state()
        name_item = self.main.tableWidget.item(row, 0)
        client_id_str = name_item.data(Qt.UserRole)
        
        if not client_id_str:
            return
    
        try:
            self.main.current_client_id = ObjectId(client_id_str)
        except Exception as e:
            QMessageBox.warning(self.main, "Error", f"Invalid client ID format: {e}")
            return

        if self.main.db is not None:
            client = self.main.db['clients'].find_one({'_id': ObjectId(client_id_str)})
            
            if client:
                # Populate labels
                full_name = client.get('full_name', 'Unknown')
                self.main.lbl_client_name.setText(full_name)
                self.main.lbl_client_phone.setText(client.get('phone', '-'))
                self.main.lbl_client_notes.setText(client.get('notes', 'No notes.'))

                birth_date = client.get('birth_date', '')
                if birth_date:
                    age = CalculationService.calculate_age(birth_date)
                    if age is not None:
                        age_label = TranslationService.get("clients.age", "Age")
                        self.main.lbl_age.setText(f"{age_label}: {age}")
                    else:
                        age_label = TranslationService.get("clients.age", "Age")
                        self.main.lbl_age.setText(f"{age_label}: -")
                else:
                    age_label = TranslationService.get("clients.age", "Age")
                    self.main.lbl_age.setText(f"{age_label}: -")
                
                self.main.stackedWidget.setCurrentWidget(self.main.page_client_detail)
                
                # Clear old stats
                tab_overview = self.main.tabWidget.widget(0)
                if self.main.stats_container is not None:
                    self.main.stats_container.clear_cards()
                    tab_overview.layout().removeWidget(self.main.stats_container)
                    self.main.stats_container.deleteLater()
                    self.main.stats_container = None
                
                # Load measurements
                self.main.measurement_controller.load_client_measurements()
                self.main.measurement_controller.refresh_stats_and_chart()
                
            else:
                QMessageBox.warning(self.main, "Error", "Client not found in database!")

    def prepare_add_mode(self):
        """Prepare form for adding a new client."""
        self.main.current_client_id = None
        self.main.txt_name.clear()
        self.main.txt_phone.clear()
        self.main.txt_notes.clear()
        self.main.stackedWidget.setCurrentWidget(self.main.page_add_client)

    def prepare_edit_mode(self):
        """Prepare form for editing an existing client."""
        if not self.main.current_client_id:
            return

        if self.main.db is not None:
            client = self.main.db['clients'].find_one({'_id': self.main.current_client_id})
            
            if client:
                self.main.txt_name.setText(client.get("full_name", ""))
                self.main.txt_phone.setText(client.get("phone", ""))
                self.main.txt_notes.setPlainText(client.get("notes", ""))
                
                birth_date_str = client.get("birth_date", "")
                if birth_date_str:
                    try:
                        birth_date_obj = datetime.strptime(birth_date_str, "%Y-%m-%d")
                        self.main.date_birth_add.setDate(birth_date_obj.date())
                    except Exception as e:
                        print(f"Error parsing birth date: {e}")
                
                self.main.stackedWidget.setCurrentWidget(self.main.page_add_client)

    def handle_cancel(self):
        """Handle cancel button - return to appropriate previous page."""
        if self.main.current_client_id is not None:
            self.main.stackedWidget.setCurrentWidget(self.main.page_client_detail)
        else:
            self.main.stackedWidget.setCurrentWidget(self.main.page_clients)

    def filter_clients_by_search(self, search_text):
        """Filter clients table by search text in real-time."""
        search_text = search_text.lower().strip()
        
        for row in range(self.main.tableWidget.rowCount()):
            name_item = self.main.tableWidget.item(row, 0)
            if name_item:
                client_name = name_item.text().lower()
                self.main.tableWidget.setRowHidden(row, search_text not in client_name)
            else:
                self.main.tableWidget.setRowHidden(row, True)
