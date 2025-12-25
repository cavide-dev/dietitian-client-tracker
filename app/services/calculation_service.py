"""
CalculationService - Centralized calculations for statistics and metrics.
This service consolidates calculation logic for age, weight changes, body composition
changes, and trend percentages into a single, testable, and maintainable class.
"""

from datetime import datetime
from typing import Optional, Tuple, List, Dict


class CalculationService:
    """Handles all application-wide calculations for statistics and metrics."""

    @staticmethod
    def calculate_age(birth_date_str: str) -> Optional[int]:
        """
        Calculate age from birth date string.
        
        Args:
            birth_date_str: Birth date in yyyy-MM-dd format
            
        Returns:
            Age in years, or None if calculation fails
        """
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
            today = datetime.today()
            
            # Account for whether birthday has occurred this year
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            
            return age
        except (ValueError, TypeError):
            return None

    @staticmethod
    def calculate_weight_change(
        latest_weight: float, 
        previous_weight: float
    ) -> float:
        """
        Calculate weight change in kilograms.
        
        Args:
            latest_weight: Most recent weight value
            previous_weight: Previous weight value
            
        Returns:
            Change amount (positive = gain, negative = loss)
        """
        return round(latest_weight - previous_weight, 2)

    @staticmethod
    def calculate_fat_change(
        latest_fat: float, 
        previous_fat: float
    ) -> float:
        """
        Calculate body fat ratio change in percentages.
        
        Args:
            latest_fat: Most recent body fat ratio (%)
            previous_fat: Previous body fat ratio (%)
            
        Returns:
            Change amount (positive = gain, negative = loss)
        """
        return round(latest_fat - previous_fat, 2)

    @staticmethod
    def calculate_muscle_change(
        latest_muscle: float, 
        previous_muscle: float
    ) -> float:
        """
        Calculate muscle mass change in kilograms.
        
        Args:
            latest_muscle: Most recent muscle mass value
            previous_muscle: Previous muscle mass value
            
        Returns:
            Change amount (positive = gain, negative = loss)
        """
        return round(latest_muscle - previous_muscle, 2)

    @staticmethod
    def calculate_all_stats(
        latest_measurement: Dict,
        previous_measurement: Dict
    ) -> Dict[str, float]:
        """
        Calculate all stat changes between two measurements.
        
        Args:
            latest_measurement: Most recent measurement data
            previous_measurement: Previous measurement data
            
        Returns:
            Dictionary with all changes:
            {
                'weight_change': float,
                'fat_change': float,
                'muscle_change': float
            }
        """
        return {
            'weight_change': CalculationService.calculate_weight_change(
                latest_measurement.get('weight', 0),
                previous_measurement.get('weight', 0)
            ),
            'fat_change': CalculationService.calculate_fat_change(
                latest_measurement.get('body_fat_ratio', 0),
                previous_measurement.get('body_fat_ratio', 0)
            ),
            'muscle_change': CalculationService.calculate_muscle_change(
                latest_measurement.get('muscle_mass', 0),
                previous_measurement.get('muscle_mass', 0)
            ),
        }

    @staticmethod
    def calculate_trend_percentage(
        latest_value: float, 
        previous_value: float,
        decimal_places: int = 2
    ) -> float:
        """
        Calculate trend percentage change between two values.
        
        Args:
            latest_value: Current value
            previous_value: Previous value
            decimal_places: Number of decimal places (default: 2)
            
        Returns:
            Trend percentage (positive = increase, negative = decrease)
        """
        if previous_value == 0:
            return 0.0
        
        percentage = ((latest_value - previous_value) / abs(previous_value)) * 100
        return round(percentage, decimal_places)

    @staticmethod
    def get_change_direction(change: float) -> str:
        """
        Determine change direction (up, down, neutral).
        
        Args:
            change: Change amount
            
        Returns:
            Direction: "up" (increase), "down" (decrease), "neutral" (no change)
        """
        if change > 0:
            return "up"
        elif change < 0:
            return "down"
        else:
            return "neutral"

    @staticmethod
    def format_stat_value(value: float, unit: str = "", decimal_places: int = 1) -> str:
        """
        Format statistic value for display.
        
        Args:
            value: Numeric value
            unit: Unit of measurement (kg, %, etc.)
            decimal_places: Number of decimal places
            
        Returns:
            Formatted string value
        """
        formatted = f"{value:.{decimal_places}f}"
        return f"{formatted}{unit}"
