"""
break_scheduler.py — Break & Lunch Period Scheduling

Manages break periods during timetable generation.
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass


@dataclass
class BreakPeriod:
    """Represents a break period."""
    period_index: int  # 0-based
    name: str  # "Lunch", "Short Break", etc.
    duration: int  # number of periods (usually 1)


class BreakScheduler:
    """
    Manages break periods in the timetable.
    """
    
    def __init__(self, break_periods: Dict[int, str] = None):
        """
        Args:
            break_periods: Dict mapping period index to break name
                          e.g., {3: "Lunch", 6: "Short Break"}
        """
        self.break_periods = break_periods or {}
    
    def get_break_periods(self, day: int = None) -> Dict[int, str]:
        """Get break periods (optionally for specific day)."""
        return self.break_periods
    
    def is_break(self, period: int, day: int = None) -> bool:
        """Check if a period is a break period."""
        return period in self.break_periods
    
    def get_break_name(self, period: int) -> Optional[str]:
        """Get the name of a break period."""
        return self.break_periods.get(period)
    
    def get_non_break_periods(self, periods_per_day: int) -> List[int]:
        """Get list of non-break period indices."""
        return [p for p in range(periods_per_day) if p not in self.break_periods]
    
    def validate_break_placement(self, break_period: int, max_consecutive: int) -> Tuple[bool, str]:
        """
        Validate if break is placed optimally.
        
        Returns (is_valid, message).
        """
        if break_period == 0:
            return False, "Break cannot be at the start of the day"
        
        if break_period > 6:
            return False, "Break too late in the day"
        
        return True, "Break placement is good"
    
    def suggest_break_placement(self, periods_per_day: int) -> int:
        """
        Suggest optimal break period based on typical scheduling.
        
        Returns suggested period index.
        """
        if periods_per_day <= 5:
            return 2  # After 2nd period
        elif periods_per_day <= 7:
            return 3  # After 3rd period (lunch time)
        else:
            return 4  # After 4th period
    
    def get_schedule_without_breaks(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]]) -> Dict:
        """
        Get schedule statistics excluding break periods.
        """
        stats = {}
        
        for (class_id, day, period), (subject, teacher, _) in schedule.items():
            if self.is_break(period):
                continue
            
            if class_id not in stats:
                stats[class_id] = {}
            if day not in stats[class_id]:
                stats[class_id][day] = []
            stats[class_id][day].append(period)
        
        return stats
    
    def ensure_break_in_schedule(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                               periods_per_day: int, days: List[str]) -> List[Tuple[int, int]]:
        """
        Check if all break periods are unfilled in the schedule.
        
        Returns list of unfilled break slots.
        """
        unfilled = []
        
        for day in range(len(days)):
            for break_period in self.break_periods.keys():
                key = (day, break_period)
                if key not in schedule:
                    unfilled.append((day, break_period))
        
        return unfilled


def format_break_schedule(break_periods: Dict[int, str], periods_per_day: int) -> str:
    """
    Format break periods for display.
    """
    lines = []
    for p in range(periods_per_day):
        if p in break_periods:
            lines.append(f"Period {p+1}: {break_periods[p]} (Break)")
        else:
            lines.append(f"Period {p+1}: Regular")
    
    return "\n".join(lines)
