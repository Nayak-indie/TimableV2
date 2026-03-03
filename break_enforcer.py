"""
break_enforcer.py — Break Period Enforcement

Ensures that break/lunch periods are never scheduled for teaching.
This is already integrated into the solver, but this module provides utilities.
"""

from typing import Dict, List, Set, Tuple
from models import SchoolConfig


def get_break_indices(config: SchoolConfig) -> Set[int]:
    """
    Get set of break period indices from config.
    
    Args:
        config: SchoolConfig with break_periods dict
        
    Returns:
        Set of period indices that are breaks
    """
    return set(config.break_periods.keys())


def get_teaching_periods(config: SchoolConfig) -> List[int]:
    """
    Get list of available teaching periods (excluding breaks).
    
    Args:
        config: SchoolConfig with break_periods
        
    Returns:
        List of period indices available for teaching
    """
    breaks = get_break_indices(config)
    return [p for p in range(config.periods_per_day) if p not in breaks]


def is_teaching_period(config: SchoolConfig, period: int) -> bool:
    """Check if a period is available for teaching."""
    return period not in config.break_periods


def format_break_schedule(config: SchoolConfig) -> str:
    """
    Format the break schedule for display.
    """
    lines = []
    for p in range(config.periods_per_day):
        if p in config.break_periods:
            lines.append(f"  Period {p+1}: {config.break_periods[p]} (BREAK - No teaching)")
        else:
            lines.append(f"  Period {p+1}: Teaching available")
    return "\n".join(lines)


def validate_break_config(config: SchoolConfig) -> Tuple[bool, List[str]]:
    """
    Validate break period configuration.
    
    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    
    # Check if breaks are in valid range
    for p in config.break_periods.keys():
        if p < 0 or p >= config.periods_per_day:
            issues.append(f"Break period {p} is out of range (0-{config.periods_per_day-1})")
    
    # Check for too many breaks
    if len(config.break_periods) >= config.periods_per_day:
        issues.append("Too many break periods - no time for teaching!")
    
    # Check if breaks are at reasonable positions
    breaks = list(config.break_periods.keys())
    if breaks:
        if breaks[0] == 0:
            issues.append("First period cannot be a break")
        if breaks[-1] == config.periods_per_day - 1:
            issues.append("Last period cannot be a break")
    
    return len(issues) == 0, issues


def suggest_break_schedule(periods_per_day: int) -> Dict[int, str]:
    """
    Suggest a reasonable break schedule based on typical school hours.
    """
    if periods_per_day <= 5:
        return {2: "Short Break"}
    elif periods_per_day <= 7:
        return {3: "Lunch"}
    else:
        return {3: "Lunch", 6: "Short Break"}
