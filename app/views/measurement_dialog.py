from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, 
                             QLabel, QDoubleSpinBox, QDateEdit, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt, QDate

class MeasurementDialog(QDialog):
    """
    A pop-up dialog window for adding new body measurements.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Measurement")
        self.resize(400, 600) 

        # --- MAIN LAYOUT ---
        # Stacks elements vertically (Top to Bottom)
        self.layout = QVBoxLayout(self)

        # --- FORM LAYOUT ---
        # Automatically arranges widgets in a "Label: Input" format.
        # This is perfect for data entry forms without manual positioning.
        form_layout = QFormLayout()

        # 1. DATE FIELD
        self.input_date = QDateEdit()
        self.input_date.setDate(QDate.currentDate()) # Default to today
        self.input_date.setCalendarPopup(True)       # Enable calendar dropdown
        form_layout.addRow("Date:", self.input_date)

        # --- CATEGORY 1: BASIC METRICS ---
        
        # Weight (Using QDoubleSpinBox for numeric safety)
        self.input_weight = QDoubleSpinBox()
        self.input_weight.setRange(0, 300)   # Min 0kg, Max 300kg
        self.input_weight.setSuffix(" kg")   # Adds unit text automatically
        form_layout.addRow("Weight:", self.input_weight)

        # Height
        self.input_height = QDoubleSpinBox()
        self.input_height.setRange(0, 250)
        self.input_height.setSuffix(" cm")
        form_layout.addRow("Height:", self.input_height)

        # --- CATEGORY 2: BODY ANALYSIS ---
        
        # Body Fat Ratio
        self.input_fat = QDoubleSpinBox()
        self.input_fat.setRange(0, 100)
        self.input_fat.setSuffix(" %")
        form_layout.addRow("Body Fat Ratio:", self.input_fat)

        # Muscle Mass
        self.input_muscle = QDoubleSpinBox()
        self.input_muscle.setRange(0, 200)
        self.input_muscle.setSuffix(" kg")
        form_layout.addRow("Muscle Mass:", self.input_muscle)
        
        # Visceral Fat Rating (1-59 level)
        self.input_visceral = QDoubleSpinBox()
        self.input_visceral.setRange(0, 59)
        form_layout.addRow("Visceral Fat Rating:", self.input_visceral)

        # Metabolic Age
        self.input_metabolic_age = QDoubleSpinBox()
        self.input_metabolic_age.setRange(0, 150)
        self.input_metabolic_age.setDecimals(0) # Integers only (No decimals)
        form_layout.addRow("Metabolic Age:", self.input_metabolic_age)

        # Water Ratio
        self.input_water = QDoubleSpinBox()
        self.input_water.setRange(0, 100)
        self.input_water.setSuffix(" %")
        form_layout.addRow("Water Ratio:", self.input_water)

        # --- CATEGORY 3: CIRCUMFERENCE MEASUREMENTS ---
        
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
        
        # Chest (Optional)
        self.input_chest = QDoubleSpinBox()
        self.input_chest.setRange(0, 300)
        self.input_chest.setSuffix(" cm")
        form_layout.addRow("Chest (Optional):", self.input_chest)

        # Arm (Optional)
        self.input_arm = QDoubleSpinBox()
        self.input_arm.setRange(0, 100)
        self.input_arm.setSuffix(" cm")
        form_layout.addRow("Arm (Optional):", self.input_arm)

        # Thigh (Optional)
        self.input_thigh = QDoubleSpinBox()
        self.input_thigh.setRange(0, 150)
        self.input_thigh.setSuffix(" cm")
        form_layout.addRow("Thigh (Optional):", self.input_thigh)

        # --- NOTES ---
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Enter notes here...")
        self.input_notes.setMaximumHeight(60) # Limit height to save space
        form_layout.addRow("Notes:", self.input_notes)

        # Add the form layout to the main vertical layout
        self.layout.addLayout(form_layout)

        # --- ACTION BUTTONS (Save & Cancel) ---
        # PyQt5 Syntax: Direct access to button types (e.g., QDialogButtonBox.Save)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept) # Triggers standard "OK" behavior
        self.buttons.rejected.connect(self.reject) # Triggers standard "Cancel" behavior
        self.layout.addWidget(self.buttons)

    def get_data(self):
        """
        Collects all data from the input fields and returns a dictionary.
        This is called by the main controller after the user clicks 'Save'.
        """
        return {
            # Convert QDate to Python Date String (YYYY-MM-DD)
            "date": self.input_date.date().toPyDate().strftime("%Y-%m-%d"),
            
            # .value() returns the float number from the SpinBox
            "weight": self.input_weight.value(),
            "height": self.input_height.value(),
            "body_fat_ratio": self.input_fat.value(),
            "muscle_mass": self.input_muscle.value(),
            "visceral_fat": self.input_visceral.value(),
            "metabolic_age": self.input_metabolic_age.value(),
            "water_ratio": self.input_water.value(),
            "waist": self.input_waist.value(),
            "hip": self.input_hip.value(),
            "chest": self.input_chest.value(),
            "arm": self.input_arm.value(),
            "thigh": self.input_thigh.value(),
            "notes": self.input_notes.toPlainText()
        }