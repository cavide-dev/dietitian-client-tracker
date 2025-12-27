from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, 
                             QLabel, QDoubleSpinBox, QDateEdit, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QDate
from app.services.validation_service import ValidationService
from app.i18n.translations import TranslationService

class MeasurementDialog(QDialog):
    """
    A pop-up dialog window for adding new body measurements.
    
    Features:
    - Captures comprehensive body metrics (Weight, Fat, Muscle, BMR, etc.)
    - Captures circumference measurements (Waist, Hip, Chest, Arm, Thigh).
    - Returns a dictionary ready for MongoDB insertion.
    """
    def __init__(self, parent=None, measurement_data=None):
        super().__init__(parent)
        
        # If editing, set title to "Edit Measurement", else "Add New Measurement"
        if measurement_data:
            self.setWindowTitle(TranslationService.get("measurements.edit_title", "Edit Measurement"))
            self.is_edit_mode = True
        else:
            self.setWindowTitle(TranslationService.get("measurements.add_title", "Add New Measurement"))
            self.is_edit_mode = False
        
        self.measurement_data = measurement_data
        self.resize(550, 900)  # Larger dialog for better UX


        # --- MAIN LAYOUT ---
        self.layout = QVBoxLayout(self)

        # --- FORM LAYOUT ---
        # Aligns labels and input fields automatically
        form_layout = QFormLayout()

        # 1. DATE FIELD
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate()) # Defaults to today
        self.input_date.setCalendarPopup(True)       # Shows a calendar dropdown
        form_layout.addRow(TranslationService.get("measurements.date", "Date") + ":", self.input_date)

        # --- CATEGORY 1: BASIC METRICS ---
        
        # Weight (kg)
        self.input_weight = QDoubleSpinBox()
        self.input_weight.setRange(0, 600)
        form_layout.addRow(TranslationService.get("measurements.weight", "Weight (kg)") + ":", self.input_weight)

        # Height (cm)
        self.input_height = QDoubleSpinBox()
        self.input_height.setRange(0, 250)
        form_layout.addRow(TranslationService.get("measurements.height", "Height (cm)") + ":", self.input_height)

        # --- CATEGORY 2: BODY COMPOSITION ---
        
        # Body Fat Ratio (%)
        self.input_fat = QDoubleSpinBox()
        self.input_fat.setRange(0, 150)
        form_layout.addRow(TranslationService.get("measurements.body_fat_ratio", "Body Fat Ratio (%)") + ":", self.input_fat)

        # Muscle Mass (kg)
        self.input_muscle = QDoubleSpinBox()
        self.input_muscle.setRange(0, 200)
        form_layout.addRow(TranslationService.get("measurements.muscle_mass", "Muscle Mass (kg)") + ":", self.input_muscle)
        
        # Metabolic Age (Years)
        self.input_metabolic_age = QDoubleSpinBox()
        self.input_metabolic_age.setRange(0, 150)
        self.input_metabolic_age.setDecimals(0) # Integer only
        form_layout.addRow(TranslationService.get("measurements.metabolic_age", "Metabolic Age (years)") + ":", self.input_metabolic_age)

        # BMR (Basal Metabolic Rate) - [NEW]
        self.input_bmr = QDoubleSpinBox()
        self.input_bmr.setRange(0, 5000) 
        self.input_bmr.setDecimals(0)    
        form_layout.addRow(TranslationService.get("measurements.bmr", "BMR (kcal)") + ":", self.input_bmr)

        # Visceral Fat Rating (1-59)
        self.input_visceral = QDoubleSpinBox()
        self.input_visceral.setRange(0, 59)
        form_layout.addRow(TranslationService.get("measurements.visceral_fat", "Visceral Fat Rating") + ":", self.input_visceral)

        # Water Ratio (%)
        self.input_water = QDoubleSpinBox()
        self.input_water.setRange(0, 100)
        form_layout.addRow(TranslationService.get("measurements.water_ratio", "Water Ratio (%)") + ":", self.input_water)

        # --- CATEGORY 3: CIRCUMFERENCE MEASUREMENTS ---
        # These are all saved to DB, even if not shown in the main table.
        
        # Waist
        self.input_waist = QDoubleSpinBox()
        self.input_waist.setRange(0, 300)
        form_layout.addRow(TranslationService.get("measurements.waist", "Waist (cm)") + ":", self.input_waist)

        # Hip
        self.input_hip = QDoubleSpinBox()
        self.input_hip.setRange(0, 300)
        form_layout.addRow(TranslationService.get("measurements.hip", "Hip (cm)") + ":", self.input_hip)
        
        # Chest
        self.input_chest = QDoubleSpinBox()
        self.input_chest.setRange(0, 300)
        form_layout.addRow(TranslationService.get("measurements.chest", "Chest (cm)") + ":", self.input_chest)

        # Arm
        self.input_arm = QDoubleSpinBox()
        self.input_arm.setRange(0, 100)
        form_layout.addRow(TranslationService.get("measurements.arm", "Arm (cm)") + ":", self.input_arm)

        # Thigh
        self.input_thigh = QDoubleSpinBox()
        self.input_thigh.setRange(0, 150)
        form_layout.addRow(TranslationService.get("measurements.thigh", "Thigh (cm)") + ":", self.input_thigh)

        # --- NOTES ---
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText(TranslationService.get("measurements.notes_placeholder", "Enter extra notes here..."))
        self.input_notes.setMaximumHeight(60)
        form_layout.addRow("Notes:", self.input_notes)

        # Add form to main layout
        self.layout.addLayout(form_layout)

        # --- ACTION BUTTONS ---
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        # Style cancel button as gray
        cancel_btn = self.buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setObjectName("btn_cancel_dialog")
        
        self.layout.addWidget(self.buttons)
        # If editing, populate form fields with existing measurement data
        if self.measurement_data:
            # Parse date if it's a string
            date_val = self.measurement_data.get('date', QDate.currentDate())
            if isinstance(date_val, str):
                date_obj = QDate.fromString(date_val, "yyyy-MM-dd")
                if date_obj.isValid():
                    self.input_date.setDate(date_obj)
            elif isinstance(date_val, QDate):
                self.input_date.setDate(date_val)
            
            self.input_weight.setValue(self.measurement_data.get('weight', 0))
            self.input_height.setValue(self.measurement_data.get('height', 0))
            self.input_fat.setValue(self.measurement_data.get('body_fat', 0))
            self.input_muscle.setValue(self.measurement_data.get('muscle', 0))
            self.input_metabolic_age.setValue(self.measurement_data.get('metabolic_age', 0))
            self.input_bmr.setValue(self.measurement_data.get('bmr', 0))
            self.input_visceral.setValue(self.measurement_data.get('visceral_fat', 0))
            self.input_water.setValue(self.measurement_data.get('water_ratio', 0))
            self.input_waist.setValue(self.measurement_data.get('waist', 0))
            self.input_hip.setValue(self.measurement_data.get('hip', 0))
            self.input_chest.setValue(self.measurement_data.get('chest', 0))
            self.input_arm.setValue(self.measurement_data.get('arm', 0))
            self.input_thigh.setValue(self.measurement_data.get('thigh', 0))
            self.input_notes.setPlainText(self.measurement_data.get('notes', ''))

    def validate_measurements(self):
        """
        Validate measurement values for sensible ranges.
        Uses ValidationService for centralized validation.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        height = self.input_height.value()
        weight = self.input_weight.value()
        body_fat = self.input_fat.value()
        
        # Use ValidationService for main measurements
        is_valid, error_msg = ValidationService.validate_measurement_values(height, weight, body_fat)
        if not is_valid:
            return False, error_msg
        
        # Circumferences validation (5-150 cm) - specific to this dialog
        circumferences = {
            "Waist": self.input_waist.value(),
            "Hip": self.input_hip.value(),
            "Chest": self.input_chest.value(),
            "Arm": self.input_arm.value(),
            "Thigh": self.input_thigh.value()
        }
        
        for name, value in circumferences.items():
            if value < 5 or value > 150:
                return False, f"{name} circumference must be between 5-150 cm"
        
        return True, ""

    def get_data(self):
        """
        Collects ALL data from input fields and returns a dictionary.
        This dictionary matches the MongoDB document structure.
        """
        return {
            "date": self.input_date.date().toPyDate().strftime("%Y-%m-%d"),
            
            # Basic & Composition
            "weight": self.input_weight.value(),
            "height": self.input_height.value(),
            "body_fat_ratio": self.input_fat.value(),
            "muscle_mass": self.input_muscle.value(),
            "visceral_fat": self.input_visceral.value(),
            "metabolic_age": self.input_metabolic_age.value(),
            "bmr": self.input_bmr.value(),         
            "water_ratio": self.input_water.value(),

            # Circumferences (Saved to DB for future charts/details)
            "waist": self.input_waist.value(),     
            "hip": self.input_hip.value(),
            "chest": self.input_chest.value(),     
            "arm": self.input_arm.value(),         
            "thigh": self.input_thigh.value(),    

            "notes": self.input_notes.toPlainText()
        }
