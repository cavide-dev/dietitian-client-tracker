from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from app.i18n.translations import TranslationService

# Set font for Unicode support (Korean, Turkish, etc.)
# Arial and DejaVu support Turkish + Latin, then fallback to CJK fonts
matplotlib.rcParams['font.sans-serif'] = [
    'Arial',           # Supports Turkish + Latin + many Unicode
    'Verdana',         # Alternative with good Turkish support
    'DejaVu Sans',     # Unicode support
    'SimSun',          # CJK support
    'NotoSansCJK'      # CJK support
]
matplotlib.rcParams['font.weight'] = 'bold'
matplotlib.rcParams['axes.labelweight'] = 'bold'
matplotlib.rcParams['axes.titleweight'] = 'bold'

class TrendChart(QWidget):
    """
    Displays a trend chart for client measurements over time.
    Shows Weight, Muscle on left Y-axis and Body Fat on right Y-axis.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "Light"
        self.last_measurements = []  # Store for replot on theme change
        self.figure = None  # Keep reference to figure
        self.canvas = None  # Keep reference to canvas
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize the UI layout for the chart"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setMaximumHeight(400)
        self.setLayout(layout)
        
        # Canvas will be added when data arrives
        self.canvas = None
    def plot_trends(self, measurements):
        """
        Plot measurement trends.
        
        Args:
            measurements (list): List of measurement documents from MongoDB
        """
        
        # Store measurements for replot on theme change
        self.last_measurements = measurements
        
        # ===== PROBLEM 1: Check if we have enough data =====
        if not measurements or len(measurements) < 2:
            self.show_empty_state()
            return
        
        # ===== PROBLEM 3: Sort by date (ascending - oldest first) =====
        # Normalize dates for sorting
        def normalize_date(date_val):
            if isinstance(date_val, datetime):
                return date_val
            elif isinstance(date_val, str):
                return datetime.strptime(date_val, '%Y-%m-%d')
            else:
                return date_val

        measurements = sorted(measurements, key=lambda x: normalize_date(x.get('date', '')))
        
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
        
        # ===== Clear previous widgets =====
        while self.layout().count():
            widget = self.layout().takeAt(0).widget()
            if widget:
                widget.deleteLater()
        
        # ===== Clean up old canvas/figure to prevent "wrapped object deleted" errors =====
        if self.canvas is not None:
            try:
                self.canvas.figure.clear()
                plt.close(self.figure)
            except:
                pass
            self.canvas = None
        if self.figure is not None:
            try:
                self.figure.clear()
                plt.close(self.figure)
            except:
                pass
            self.figure = None
        
        figure = Figure(figsize=(8, 4), dpi=100)
        self.figure = figure  # Keep reference to figure
        
        # Set colors based on current theme
        if self.current_theme == "Dark":
            bg_color = '#2A2A2A'
            text_color = '#E5E5E5'
            grid_color = '#444444'
            blue_color = '#7EB3FF'  # Lighter blue for dark theme
            red_color = '#FF6B6B'   # Lighter red for dark theme
        else:
            bg_color = '#FFFFFF'
            text_color = '#1D1D1D'
            grid_color = '#CCCCCC'
            blue_color = '#0052CC'  # Standard blue for light theme
            red_color = '#CC0000'   # Standard red for light theme
        
        figure.patch.set_facecolor(bg_color)
        
        # ===== PROBLEM 2: Two Y-axes =====
        ax1 = figure.add_subplot(111)
        ax1.set_facecolor(bg_color)
        ax2 = ax1.twinx()  # Right Y-axis
        
        # ===== Plot on Left Y-axis (Weight + Muscle) =====
        weight_label = TranslationService.get("measurements.weight", "Weight (kg)")
        muscle_label = TranslationService.get("measurements.muscle", "Muscle (kg)")
        body_fat_label = TranslationService.get("measurements.body_fat", "Body Fat (%)")
        
        ax1.plot(dates, weights, color=blue_color, marker='o', linewidth=2, markersize=6, label=weight_label)
        ax1.plot(dates, muscles, 'g-s', linewidth=2, markersize=6, label=muscle_label)
        weight_muscle_axis_label = TranslationService.get("measurements.weight_muscle_axis", "Weight & Muscle (kg)")
        ax1.set_ylabel(weight_muscle_axis_label, color=blue_color, fontsize=11, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor=blue_color)
        ax1.tick_params(axis='x', colors=text_color)
        ax1.xaxis.label.set_color(text_color)
        ax1.yaxis.label.set_color(blue_color)
        ax1.spines['bottom'].set_color(text_color)
        ax1.spines['left'].set_color(blue_color)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.grid(True, alpha=0.3, color=grid_color)
        
        # ===== Plot on Right Y-axis (Body Fat) =====
        body_fat_axis_label = TranslationService.get("measurements.body_fat_axis", "Body Fat (%)")
        ax2.plot(dates, body_fats, color=red_color, marker='^', linewidth=2, markersize=6, label=body_fat_label)
        ax2.set_ylabel(body_fat_axis_label, color=red_color, fontsize=11, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor=red_color)
        ax2.spines['right'].set_color(red_color)
        
        # ===== Labels & Title =====
        ax1.set_xlabel('', fontsize=11, fontweight='bold')
        chart_title = TranslationService.get("measurements.trends", "Measurement Trends")
        ax1.set_title(chart_title, fontsize=13, fontweight='bold', color=text_color)
        
        # ===== Rotate X-axis labels =====
        figure.autofmt_xdate(rotation=30, ha='right')
        
        # ===== Combine legends =====
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        # ===== Embed in PyQt5 =====
        self.canvas = FigureCanvas(figure)
        self.layout().insertWidget(0, self.canvas)

    def show_empty_state(self):
        """Display message when not enough data for chart"""
        # Clear all widgets from layout
        while self.layout().count():
            widget = self.layout().takeAt(0).widget()
            if widget:
                widget.deleteLater()
        
        # Clean up canvas/figure
        if self.canvas is not None:
            try:
                self.canvas.figure.clear()
                plt.close(self.figure)
            except:
                pass
            self.canvas = None
        if self.figure is not None:
            try:
                self.figure.clear()
                plt.close(self.figure)
            except:
                pass
            self.figure = None
        
        # Show message
        empty_label = QLabel("Need at least 2 measurements to display chart")
        empty_label.setObjectName("chart_empty_message")
        self.layout().addWidget(empty_label)

    def apply_theme(self, theme_name):
        """Apply theme to chart and refresh"""
        self.current_theme = theme_name
        # Redraw chart with new theme
        if self.last_measurements:
            self.plot_trends(self.last_measurements)
    
    def closeEvent(self, event):
        """Clean up matplotlib resources when widget is closed"""
        if self.canvas is not None:
            try:
                self.canvas.figure.clear()
                plt.close(self.figure)
            except:
                pass
        if self.figure is not None:
            try:
                plt.close(self.figure)
            except:
                pass
        super().closeEvent(event)