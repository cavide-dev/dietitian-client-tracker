"""
DietController - Manages all diet plan operations.
Responsible for: CRUD operations, listing, and management of diet plans.
"""

from PyQt5.QtWidgets import QMessageBox
from datetime import datetime
from app.services.validation_service import ValidationService


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
            QMessageBox.warning(self.main, "Warning", "Please select a client first!")
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
            QMessageBox.information(self.main, "Success", "Diet Plan saved successfully!")
            
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
            QMessageBox.warning(self.main, "Warning", "Please select a diet plan to update!")
            return

        title = self.main.txt_diet_title_edit.text().strip()
        breakfast = self.main.txt_breakfast_edit.toPlainText().strip()
        lunch = self.main.txt_lunch_edit.toPlainText().strip()
        dinner = self.main.txt_dinner_edit.toPlainText().strip()

        try:
            diet_data = {
                "title": title,
                "content": {
                    "breakfast": breakfast,
                    "lunch": lunch,
                    "dinner": dinner
                }
            }

            self.main.db['diet_plans'].update_one(
                {'_id': self.main.current_diet_id},
                {'$set': diet_data}
            )
            QMessageBox.information(self.main, "Success", "Diet plan updated successfully!")
            self.load_client_diet_plans()
            self.main.stack_diet_sub.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Could not update diet plan: {e}")

    def delete_diet_plan(self):
        """
        Delete a diet plan.
        """
        if not self.main.current_diet_id:
            QMessageBox.warning(self.main, "Warning", "Please select a diet plan to delete!")
            return

        reply = QMessageBox.question(self.main, 'Confirm Delete', 'Delete this diet plan?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        try:
            self.main.db['diet_plans'].delete_one({'_id': self.main.current_diet_id})
            QMessageBox.information(self.main, "Success", "Diet plan deleted successfully!")
            self.load_client_diet_plans()
            self.main.stack_diet_sub.setCurrentIndex(0)
            
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Could not delete diet plan: {e}")

    def load_client_diet_plans(self):
        """
        Fetch and display diet plans for selected client.
        """
        if not self.main.current_client_id or self.main.db is None:
            self.main.show_diet_empty_state()
            return

        try:
            diets = list(self.main.db['diet_plans'].find({"client_id": self.main.current_client_id}))
            
            if not diets:
                self.main.show_diet_empty_state()
                return

            self.main.hide_diet_empty_state()
            self.main.table_diets.setRowCount(len(diets))

            for row_index, diet in enumerate(diets):
                title_item = self.main.table_diets.item(row_index, 0)
                if not title_item:
                    from PyQt5.QtWidgets import QTableWidgetItem
                    title_item = QTableWidgetItem(diet.get('title', '-'))
                    self.main.table_diets.setItem(row_index, 0, title_item)
                else:
                    title_item.setText(diet.get('title', '-'))

        except Exception as e:
            print(f"Error loading diet plans: {e}")
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

    def prepare_add_diet_mode(self):
        """Prepare form for adding new diet plan."""
        self.clear_diet_inputs()
        self.main.stack_diet_sub.setCurrentIndex(1)

    def load_client_dropdown(self):
        """Load clients into dropdown for diet plans page."""
        self.main.cmb_client_select.clear()
        self.main.cmb_client_select.addItem("Select Client...", None)

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

        except Exception as e:
            print(f"Error loading clients dropdown: {e}")
