from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, 
                             QLabel, QDoubleSpinBox, QDateEdit, QTextEdit)
from PyQt5.QtCore import Qt, QDate

class MeasurementDialog(QDialog):
    """
    A pop-up dialog window for adding new body measurements.
    
    Features:
    - Captures comprehensive body metrics (Weight, Fat, Muscle, BMR, etc.)
    - Captures circumference measurements (Waist, Hip, Chest, Arm, Thigh).
    - Returns a dictionary ready for MongoDB insertion.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Measurement")
        self.resize(450, 700) # Slightly taller to fit all fields

        # --- MAIN LAYOUT ---
        self.layout = QVBoxLayout(self)

        # --- FORM LAYOUT ---
        # Aligns labels and input fields automatically
        form_layout = QFormLayout()

        # 1. DATE FIELD
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate()) # Defaults to today
        self.input_date.setCalendarPopup(True)       # Shows a calendar dropdown
        form_layout.addRow("Date:", self.input_date)

        # --- CATEGORY 1: BASIC METRICS ---
        
        # Weight (kg)
        self.input_weight = QDoubleSpinBox()
        self.input_weight.setRange(0, 300)
        self.input_weight.setSuffix(" kg")
        form_layout.addRow("Weight:", self.input_weight)

        # Height (cm)
        self.input_height = QDoubleSpinBox()
        self.input_height.setRange(0, 250)
        self.input_height.setSuffix(" cm")
        form_layout.addRow("Height:", self.input_height)

        # --- CATEGORY 2: BODY COMPOSITION ---
        
        # Body Fat Ratio (%)
        self.input_fat = QDoubleSpinBox()
        self.input_fat.setRange(0, 100)
        self.input_fat.setSuffix(" %")
        form_layout.addRow("Body Fat Ratio:", self.input_fat)

        # Muscle Mass (kg)
        self.input_muscle = QDoubleSpinBox()
        self.input_muscle.setRange(0, 200)
        self.input_muscle.setSuffix(" kg")
        form_layout.addRow("Muscle Mass:", self.input_muscle)
        
        # Metabolic Age (Years)
        self.input_metabolic_age = QDoubleSpinBox()
        self.input_metabolic_age.setRange(0, 150)
        self.input_metabolic_age.setDecimals(0) # Integer only
        form_layout.addRow("Metabolic Age:", self.input_metabolic_age)

        # BMR (Basal Metabolic Rate) - [NEW]
        self.input_bmr = QDoubleSpinBox()
        self.input_bmr.setRange(0, 5000) 
        self.input_bmr.setDecimals(0)    
        self.input_bmr.setSuffix(" kcal")
        form_layout.addRow("BMR (Basal Met. Rate):", self.input_bmr)

        # Visceral Fat Rating (1-59)
        self.input_visceral = QDoubleSpinBox()
        self.input_visceral.setRange(0, 59)
        form_layout.addRow("Visceral Fat Rating:", self.input_visceral)

        # Water Ratio (%)
        self.input_water = QDoubleSpinBox()
        self.input_water.setRange(0, 100)
        self.input_water.setSuffix(" %")
        form_layout.addRow("Water Ratio:", self.input_water)

        # --- CATEGORY 3: CIRCUMFERENCE MEASUREMENTS ---
        # These are all saved to DB, even if not shown in the main table.
        
        # Waist
        self.input_waist = QDoubleSpinBox()
        self.input_waist.setRange(0, 300)
        self.input_waist.setSuffix(" cm")
        form_layout.addRow("Waist Circumference:", self.input_waist)

        # Hip
        self.input_hip = QDoubleSpinBox()
        self.input_hip.setRange(0, 300)
        self.input_hip.setSuffix(" cm")
        form_layout.addRow("Hip Circumference:", self.input_hip)
        
        # Chest
        self.input_chest = QDoubleSpinBox()
        self.input_chest.setRange(0, 300)
        self.input_chest.setSuffix(" cm")
        form_layout.addRow("Chest Circumference:", self.input_chest)

        # Arm
        self.input_arm = QDoubleSpinBox()
        self.input_arm.setRange(0, 100)
        self.input_arm.setSuffix(" cm")
        form_layout.addRow("Arm Circumference:", self.input_arm)

        # Thigh
        self.input_thigh = QDoubleSpinBox()
        self.input_thigh.setRange(0, 150)
        self.input_thigh.setSuffix(" cm")
        form_layout.addRow("Thigh Circumference:", self.input_thigh)

        # --- NOTES ---
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Enter extra notes here...")
        self.input_notes.setMaximumHeight(60)
        form_layout.addRow("Notes:", self.input_notes)

        # Add form to main layout
        self.layout.addLayout(form_layout)

        # --- ACTION BUTTONS ---
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

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
