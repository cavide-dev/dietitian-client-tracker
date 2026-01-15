"""
DietController - Manages all diet plan operations.
Responsible for: CRUD operations, listing, and management of diet plans.
"""

from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QLabel
from PyQt5.QtCore import Qt
from datetime import datetime
from app.services.validation_service import ValidationService
from app.i18n.translations import TranslationService


class DietController:
    """
    Handles all diet plan management operations.
    Works in conjunction with MainController for UI coordination.
    """

    def __init__(self, main_controller):
        """
        Initialize DietController with reference to main controller.
        
        Args:
            main_controller: Reference to MainController instance for UI access
        """
        self.main = main_controller

    def save_diet_plan(self):
        """
        Save new diet plan. Auto-archives old active plans for the client.
        """
        if not self.main.current_client_id:
            QMessageBox.warning(
                self.main, 
                TranslationService.get("common.warning", "Warning"),
                TranslationService.get("diet_plans.select_client", "Please select a client first!")
            )
            return

        # Collect data
        title = self.main.txt_diet_title.text().strip()
        breakfast = self.main.txt_breakfast.toPlainText().strip()
        snack_1 = self.main.txt_snack_1.toPlainText().strip()
        lunch = self.main.txt_lunch.toPlainText().strip()
        snack_2 = self.main.txt_snack_2.toPlainText().strip()
        dinner = self.main.txt_dinner.toPlainText().strip()
        snack_3 = self.main.txt_snack_3.toPlainText().strip()

        # Validate using ValidationService
        is_valid_title, title_error = ValidationService.validate_diet_plan(title)
        if not is_valid_title:
            QMessageBox.warning(self.main, "Validation Error", title_error)
            return

        is_valid_breakfast, breakfast_error = ValidationService.validate_meals(breakfast, min_length=5)
        if not is_valid_breakfast:
            QMessageBox.warning(self.main, "Validation Error", f"Breakfast: {breakfast_error}")
            return
        
        is_valid_lunch, lunch_error = ValidationService.validate_meals(lunch, min_length=5)
        if not is_valid_lunch:
            QMessageBox.warning(self.main, "Validation Error", f"Lunch: {lunch_error}")
            return

        is_valid_dinner, dinner_error = ValidationService.validate_meals(dinner, min_length=5)
        if not is_valid_dinner:
            QMessageBox.warning(self.main, "Validation Error", f"Dinner: {dinner_error}")
            return

        # Prepare data
        diet_data = {
            "client_id": self.main.current_client_id,
            "dietician_username": self.main.current_user.get("username") if self.main.current_user else None,
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
            "status": "active"
        }

        try:
            # Auto-archive old active plans
            self.main.db['diet_plans'].update_many(
                {"client_id": self.main.current_client_id, "status": "active"},
                {"$set": {"status": "passive"}}
            )
            
            # Insert new plan
            self.main.db['diet_plans'].insert_one(diet_data)
            QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("diet_plans.diet_added", "Diet plan saved successfully!"))
            
            # Clear and refresh
            self.clear_diet_inputs()
            self.load_client_diet_plans()
            self.main.stack_diet_sub.setCurrentIndex(0)
            
        except Exception as e:
            print(f"Error saving diet plan: {e}")
            QMessageBox.critical(self.main, "Error", f"Could not save diet plan: {e}")

    def update_diet_plan(self):
        """
        Update an existing diet plan.
        """
        if not self.main.current_diet_id:
            QMessageBox.warning(
                self.main, 
                TranslationService.get("common.warning", "Warning"),
                TranslationService.get("diet_plans.select_diet_update", "Please select a diet plan to update!")
            )
            return

        title = self.main.txt_diet_title.text().strip()
        breakfast = self.main.txt_breakfast.toPlainText().strip()
        snack_1 = self.main.txt_snack_1.toPlainText().strip()
        lunch = self.main.txt_lunch.toPlainText().strip()
        snack_2 = self.main.txt_snack_2.toPlainText().strip()
        dinner = self.main.txt_dinner.toPlainText().strip()
        snack_3 = self.main.txt_snack_3.toPlainText().strip()

        try:
            diet_data = {
                "title": title,
                "content": {
                    "breakfast": breakfast,
                    "morning_snack": snack_1,
                    "lunch": lunch,
                    "afternoon_snack": snack_2,
                    "dinner": dinner,
                    "evening_snack": snack_3
                }
            }

            self.main.db['diet_plans'].update_one(
                {'_id': self.main.current_diet_id},
                {'$set': diet_data}
            )
            QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("diet_plans.diet_updated", "Diet plan updated successfully!"))
            self.load_client_diet_plans()
            self.main.stack_diet_sub.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Could not update diet plan: {e}")

    def delete_diet_plan(self):
        """
        Delete a diet plan.
        """
        if not self.main.current_diet_id:
            QMessageBox.warning(
                self.main, 
                TranslationService.get("common.warning", "Warning"),
                TranslationService.get("diet_plans.select_diet_delete", "Please select a diet plan to delete!")
            )
            return

        reply = QMessageBox.question(self.main, 'Confirm Delete', 'Delete this diet plan?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        try:
            self.main.db['diet_plans'].delete_one({'_id': self.main.current_diet_id})
            QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("diet_plans.diet_deleted", "Diet plan deleted successfully!"))
            self.load_client_diet_plans()
            self.main.stack_diet_sub.setCurrentIndex(0)
            
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Could not delete diet plan: {e}")

    def load_client_diet_plans(self):
        """
        Fetch and display diet plans for selected client.
        Sorted by creation date (newest first).
        (Status handling is automatic: newest diet is "active", older ones are "passive")
        """
        if not self.main.current_client_id or self.main.db is None:
            self.main.show_diet_empty_state()
            return

        try:
            # Sort by creation date - newest first
            diets = list(self.main.db['diet_plans'].find(
                {"client_id": self.main.current_client_id}
            ).sort("created_at", -1))
            
            if not diets:
                self.main.show_diet_empty_state()
                return

            self.main.hide_diet_empty_state()
            
            # Ensure table has correct number of columns
            self.main.table_diet_history.setColumnCount(3)
            self.main.table_diet_history.setRowCount(len(diets))

            for row_index, diet in enumerate(diets):
                # Date - Format properly
                date_val = diet.get('created_at', '-')
                if isinstance(date_val, str):
                    # If it's already a string, try to extract just the date part
                    date_str = date_val.split('T')[0] if 'T' in date_val else date_val
                else:
                    # If it's a datetime object, format it
                    date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
                
                date_item = QTableWidgetItem(date_str)
                # Store diet ID in UserRole for double-click handling
                date_item.setData(Qt.UserRole, str(diet.get('_id')))
                self.main.table_diet_history.setItem(row_index, 0, date_item)

                # Diet Name / Title
                title_item = QTableWidgetItem(diet.get('title', '-'))
                self.main.table_diet_history.setItem(row_index, 1, title_item)

                # Status with QLabel for QSS styling
                status = diet.get('status', 'active').lower()
                
                # Translate status
                status_key = f"diet_plans.{status}" if status in ['active', 'passive'] else "diet_plans.active"
                status_text = TranslationService.get(status_key, status.capitalize())
                
                status_label = QLabel(status_text)
                status_label.setProperty("status_type", status)
                status_label.setAlignment(Qt.AlignCenter)
                self.main.table_diet_history.setCellWidget(row_index, 2, status_label)

        except Exception as e:
            print(f"Error loading diet plans: {e}")
            import traceback
            traceback.print_exc()
            self.main.show_diet_empty_state()

    def clear_diet_inputs(self):
        """Clear all diet plan input fields."""
        self.main.txt_diet_title.clear()
        self.main.txt_breakfast.clear()
        self.main.txt_snack_1.clear()
        self.main.txt_lunch.clear()
        self.main.txt_snack_2.clear()
        self.main.txt_dinner.clear()
        self.main.txt_snack_3.clear()
        # Reset current_diet_id when clearing form
        self.main.current_diet_id = None

    def prepare_add_diet_mode(self):
        """Prepare form for adding new diet plan."""
        self.clear_diet_inputs()
        self.main.stack_diet_sub.setCurrentIndex(1)
        
        # Disable delete button when adding new diet
        if hasattr(self.main, 'btn_delete_diet'):
            self.main.btn_delete_diet.setEnabled(False)
            self.main.btn_delete_diet.setObjectName("btn_delete_diet_inactive")
            # Force style refresh
            self.main.btn_delete_diet.style().unpolish(self.main.btn_delete_diet)
            self.main.btn_delete_diet.style().polish(self.main.btn_delete_diet)

    def load_client_dropdown(self):
        """Load clients into dropdown for diet plans page."""
        self.main.cmb_client_select.clear()
        select_client_text = TranslationService.get("diet_plans.select_client_first", "Select a client...")
        self.main.cmb_client_select.addItem(select_client_text, None)

        try:
            query = {}
            if self.main.current_user:
                query = {"dietician_username": self.main.current_user.get("username")}
            
            clients = list(self.main.db['clients'].find(query))
            for client in clients:
                self.main.cmb_client_select.addItem(
                    client.get('full_name', 'Unknown'),
                    str(client.get('_id'))
                )
            
            # Reset to placeholder
            self.main.cmb_client_select.setCurrentIndex(0)

        except Exception as e:
            print(f"Error loading clients dropdown: {e}")
