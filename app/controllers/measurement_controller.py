"""
MeasurementController - Manages all measurement operations.
Responsible for: Adding, editing, deleting measurements and calculating stats.
"""

from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
from app.services.validation_service import ValidationService
from app.services.calculation_service import CalculationService
from app.i18n.translations import TranslationService
from app.views.stats_card_widget import StatsCardContainer
from app.views.chart_widget import TrendChart


class MeasurementController:
    """
    Handles all measurement management operations.
    Works in conjunction with MainController for UI coordination.
    """

    def __init__(self, main_controller):
        """
        Initialize MeasurementController with reference to main controller.
        
        Args:
            main_controller: Reference to MainController instance for UI access
        """
        self.main = main_controller

    def load_client_measurements(self):
        """
        Load and display all measurements for current client.
        """
        if not self.main.current_client_id or self.main.db is None:
            self.main.show_measurements_empty_state()
            return

        try:
            measurements = self.get_client_history(self.main.current_client_id)
            
            if not measurements:
                self.main.show_measurements_empty_state()
                return

            self.main.hide_measurements_empty_state()
            self.main.table_measurements.setRowCount(len(measurements))

            for row_index, measurement in enumerate(measurements):
                # Date - Format properly
                date_val = measurement.get('date', '-')
                if isinstance(date_val, str):
                    # If it's already a string, try to extract just the date part
                    date_str = date_val.split('T')[0] if 'T' in date_val else date_val
                else:
                    # If it's a datetime object, format it
                    date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
                
                date_item = QTableWidgetItem(date_str)
                self.main.table_measurements.setItem(row_index, 0, date_item)

                # Weight
                weight_item = QTableWidgetItem(str(measurement.get('weight', '-')))
                self.main.table_measurements.setItem(row_index, 1, weight_item)

                # Waist
                waist_item = QTableWidgetItem(str(measurement.get('waist', '-')))
                self.main.table_measurements.setItem(row_index, 2, waist_item)

                # Body Fat
                fat_item = QTableWidgetItem(str(measurement.get('body_fat_ratio', '-')))
                self.main.table_measurements.setItem(row_index, 3, fat_item)

                # Muscle Mass
                muscle_item = QTableWidgetItem(str(measurement.get('muscle_mass', '-')))
                self.main.table_measurements.setItem(row_index, 4, muscle_item)

                # Metabolic Age
                metabolic_item = QTableWidgetItem(str(measurement.get('metabolic_age', '-')))
                self.main.table_measurements.setItem(row_index, 5, metabolic_item)

                # BMR
                bmr_item = QTableWidgetItem(str(measurement.get('bmr', '-')))
                self.main.table_measurements.setItem(row_index, 6, bmr_item)

        except Exception as e:
            print(f"Error loading measurements: {e}")
            self.main.show_measurements_empty_state()

    def add_measurement_entry(self, client_id, data):
        """
        Add a new measurement entry to database.
        
        Args:
            client_id: Client ObjectId
            data: Measurement data dictionary
        """
        if self.main.db is None:
            return False

        try:
            measurement_data = {
                "client_id": client_id,
                "date": data.get('date', ''),
                "weight": data.get('weight', 0),
                "height": data.get('height', 0),
                "body_fat_ratio": data.get('body_fat_ratio', 0),
                "muscle_mass": data.get('muscle_mass', 0),
                "circumferences": data.get('circumferences', {}),
                "dietician_username": self.main.current_user.get("username") if self.main.current_user else None
            }

            self.main.db['measurements'].insert_one(measurement_data)
            return True

        except Exception as e:
            print(f"Error adding measurement: {e}")
            return False

    def get_client_history(self, client_id):
        """
        Fetch all measurements for a client, sorted by date (newest first).
        
        Args:
            client_id: Client ObjectId
            
        Returns:
            List of measurement dictionaries
        """
        if self.main.db is None:
            return []

        try:
            measurements = list(self.main.db['measurements'].find(
                {"client_id": client_id}
            ).sort("_id", -1))
            return measurements
        except Exception:
            return []

    def delete_measurement(self):
        """
        Delete selected measurement.
        """
        selected_rows = self.main.table_measurements.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self.main, "Warning", "Please select a measurement to delete!")
            return

        reply = QMessageBox.question(self.main, 'Confirm Delete', 'Delete this measurement?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.No:
            return

        try:
            measurements = self.get_client_history(self.main.current_client_id)
            row = selected_rows[0].row()
            
            if 0 <= row < len(measurements):
                measurement_id = measurements[row]['_id']
                self.main.db['measurements'].delete_one({'_id': measurement_id})
                QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("measurements.measurement_deleted", "Measurement deleted successfully!"))
                self.load_client_measurements()
                self.refresh_stats_and_chart()

        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Could not delete measurement: {e}")

    def refresh_stats_and_chart(self):
        """
        Refresh stats cards and trend chart with latest measurements.
        """
        measurements = self.get_client_history(self.main.current_client_id)
        tab_overview = self.main.tabWidget.widget(0)
        
        # Remove old stats container
        if self.main.stats_container is not None:
            tab_overview.layout().removeWidget(self.main.stats_container)
            self.main.stats_container.deleteLater()
            self.main.stats_container = None
            tab_overview.layout().update()
        
        # Recreate stats if we have enough data
        if len(measurements) >= 2:
            self.main.stats_container = StatsCardContainer()
            
            # Set translation function for stat card titles
            def translate_stat_title(title):
                translation_keys = {
                    "Weight": "weight",
                    "Body Fat": "body_fat",
                    "Muscle": "muscle"
                }
                if title in translation_keys:
                    full_text = TranslationService.get(f"measurements.{translation_keys[title]}")
                    result = full_text.split(" (")[0]
                    return result
                return title
            
            self.main.stats_container.set_title_translator(translate_stat_title)
            tab_overview.layout().insertWidget(0, self.main.stats_container)
            
            latest = measurements[0]
            previous = measurements[1]
            
            # Use CalculationService for stats
            stats = CalculationService.calculate_all_stats(latest, previous)
            weight_change = stats['weight_change']
            fat_change = stats['fat_change']
            muscle_change = stats['muscle_change']
            
            self.main.stats_container.add_stats_card("Weight", f"{latest.get('weight', 0)}", weight_change, " kg")
            self.main.stats_container.add_stats_card("Body Fat", f"{latest.get('body_fat_ratio', 0)}", fat_change, "%")
            self.main.stats_container.add_stats_card("Muscle", f"{latest.get('muscle_mass', 0)}", muscle_change, " kg")
            
            self.main.stats_container.update()
            tab_overview.update()
        
        # Remove old chart and recreate
        if self.main.trend_chart is not None:
            tab_overview.layout().removeWidget(self.main.trend_chart)
            # Properly clean up matplotlib resources before deletion
            try:
                self.main.trend_chart.show_empty_state()  # Clear the chart first
                self.main.trend_chart.close()  # Trigger closeEvent cleanup
            except:
                pass
            self.main.trend_chart.deleteLater()
            self.main.trend_chart = None
            tab_overview.layout().update()
        
        self.main.trend_chart = TrendChart()
        self.main.trend_chart.apply_theme(self.main.current_theme)
        tab_overview.layout().insertWidget(1, self.main.trend_chart)
        self.main.trend_chart.plot_trends(measurements)
        tab_overview.update()

    def open_add_measurement_dialog(self):
        """
        Open dialog to add new measurement.
        """
        if not self.main.current_client_id:
            QMessageBox.warning(self.main, "Warning", "Please select a client first!")
            return

        from app.views.measurement_dialog import MeasurementDialog
        dialog = MeasurementDialog(self.main)
        
        if dialog.exec_():
            data = dialog.get_data()
            if self.add_measurement_entry(self.main.current_client_id, data):
                QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("measurements.measurement_added", "Measurement added successfully!"))
                self.load_client_measurements()
                self.refresh_stats_and_chart()
            else:
                QMessageBox.critical(self.main, "Error", "Could not add measurement!")

    def open_edit_measurement_dialog(self, row, column):
        """
        Open dialog to edit existing measurement.
        """
        measurements = self.get_client_history(self.main.current_client_id)
        
        if 0 <= row < len(measurements):
            measurement = measurements[row]
            
            from app.views.measurement_dialog import MeasurementDialog
            dialog = MeasurementDialog(self.main, measurement_data=measurement)
            
            if dialog.exec_():
                data = dialog.get_data()
                try:
                    self.main.db['measurements'].update_one(
                        {'_id': measurement['_id']},
                        {'$set': data}
                    )
                    QMessageBox.information(self.main, TranslationService.get("dialogs.success", "Success"), TranslationService.get("measurements.measurement_updated", "Measurement updated successfully!"))
                    self.load_client_measurements()
                    self.refresh_stats_and_chart()
                except Exception as e:
                    QMessageBox.critical(self.main, "Error", f"Could not update measurement: {e}")

    def show_context_menu(self, position):
        """
        Show context menu for measurement table.
        """
        index = self.main.table_measurements.indexAt(position)

        if index.isValid():
            self.main.table_measurements.setCurrentCell(index.row(), index.column())
        
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("Delete Measurement")
        action = menu.exec_(self.main.table_measurements.mapToGlobal(position))
        
        if action == delete_action:
            self.delete_measurement()
