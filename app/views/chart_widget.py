from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from datetime import datetime

class TrendChart(QWidget):
    """
    Displays a trend chart for client measurements over time.
    Shows Weight, Muscle on left Y-axis and Body Fat on right Y-axis.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the UI layout for the chart"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        
        # Will add canvas here later
        self.canvas = None

    def plot_trends(self, measurements):
        """
        Plot measurement trends.
        
        Args:
            measurements (list): List of measurement documents from MongoDB
        """
        
        # ===== PROBLEM 1: Check if we have enough data =====
        if not measurements or len(measurements) < 2:
            self.show_empty_state()
            return
        
        # ===== PROBLEM 3: Sort by date (ascending - oldest first) =====
        measurements = sorted(measurements, key=lambda x: x.get('date', ''))
        
        # ===== ADIM 2: Extract Data =====
        dates = []
        weights = []
        body_fats = []
        muscles = []
        
        for measurement in measurements:
            dates.append(measurement.get('date', 'Unknown'))
            weights.append(measurement.get('weight', 0))
            body_fats.append(measurement.get('body_fat_ratio', 0))
            muscles.append(measurement.get('muscle_mass', 0))
        
        # ===== ADIM 3: Create Figure =====
        if self.canvas is not None:
            self.layout().removeWidget(self.canvas)
            self.canvas.deleteLater()
        
        figure = Figure(figsize=(8, 5), dpi=100)
        
        # ===== PROBLEM 2: Two Y-axes =====
        ax1 = figure.add_subplot(111)
        ax2 = ax1.twinx()  # Right Y-axis
        
        # ===== Plot on Left Y-axis (Weight + Muscle) =====
        ax1.plot(dates, weights, 'b-o', linewidth=2, markersize=6, label='Weight (kg)')
        ax1.plot(dates, muscles, 'g-s', linewidth=2, markersize=6, label='Muscle (kg)')
        ax1.set_ylabel('Weight & Muscle (kg)', color='b', fontsize=10, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='b')
        ax1.grid(True, alpha=0.3)
        
        # ===== Plot on Right Y-axis (Body Fat) =====
        ax2.plot(dates, body_fats, 'r-^', linewidth=2, markersize=6, label='Body Fat (%)')
        ax2.set_ylabel('Body Fat (%)', color='r', fontsize=10, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor='r')
        
        # ===== Labels & Title =====
        ax1.set_xlabel('Date', fontsize=10, fontweight='bold')
        ax1.set_title('Measurement Trends', fontsize=12, fontweight='bold')
        
        # ===== Rotate X-axis labels =====
        figure.autofmt_xdate(rotation=45, ha='right')
        
        # ===== Combine legends =====
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # ===== Embed in PyQt5 =====
        self.canvas = FigureCanvas(figure)
        self.layout().insertWidget(0, self.canvas)

    def show_empty_state(self):
        """Display message when not enough data for chart"""
        # Clear previous canvas
        if self.canvas is not None:
            self.layout().removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        
        # Show message
        empty_label = QLabel("Need at least 2 measurements to display chart")
        empty_label.setStyleSheet("color: #999; font-style: italic;")
        self.layout().insertWidget(0, empty_label)