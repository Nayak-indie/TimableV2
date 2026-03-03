"""
consecutive_period_manager.py — Max Consecutive Periods Enforcement

Monitors and enforces max consecutive teaching periods for teachers.
"""

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field


@dataclass
class ConsecutivePeriodViolation:
    """Represents a violation of max consecutive periods rule."""
    teacher_id: str
    class_id: str
    subject: str
    day: int
    consecutive_count: int
    max_allowed: int
    resolution: str  # "gap_inserted", "reassigned", "allowed"


@dataclass
class PeriodSlot:
    """Represents a single period slot."""
    day: int
    period: int
    teacher_id: str
    class_id: str
    subject: str


class ConsecutivePeriodManager:
    """
    Manages max consecutive periods constraints for teachers.
    """
    
    def __init__(self, max_consecutive: int = 3):
        self.max_consecutive = max_consecutive
        self.violations: List[ConsecutivePeriodViolation] = []
    
    def set_max_consecutive(self, teacher_id: str, max_consecutive: int) -> None:
        """Set max consecutive periods for a specific teacher."""
        if not hasattr(self, 'teacher_limits'):
            self.teacher_limits = {}
_limits[teacher_id] = max_consecutive
    
    def        self.teacher get_max_consecutive(self, teacher_id: str) -> int:
        """Get max consecutive periods for a teacher."""
        if hasattr(self, 'teacher_limits') and teacher_id in self.teacher_limits:
            return self.teacher_limits[teacher_id]
        return self.max_consecutive
    
    def find_gaps(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                  teacher_id: str, day: int, periods) -> List[int]:
        """
       _per_day: int Find available period slots for a teacher on a given day.
        
        Returns list of available period indices.
        """
        available = []
        for p in range(periods_per_day):
            key = (day, p)
            if key in schedule:
                _, assigned_teacher, _ = schedule[key]
                if assigned_teacher == teacher_id:
                    continue  # Already assigned
            available.append(p)
        return available
    
    def count_consecutive(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                         teacher_id: str, day: int, period: int, periods_per_day: int) -> int:
        """
        Count consecutive periods around a given slot.
        
        Returns total consecutive count including the given period.
        """
        count = 1
        
        # Check previous periods
        p = period - 1
        while p >= 0:
            key = (day, p)
            if key in schedule:
                _, assigned_teacher, _ = schedule[key]
                if assigned_teacher == teacher_id:
                    count += 1
                else:
                    break
            else:
                break
            p -= 1
        
        # Check next periods
        p = period + 1
        while p < periods_per_day:
            key = (day, p)
            if key in schedule:
                _, assigned_teacher, _ = schedule[key]
                if assigned_teacher == teacher_id:
                    count += 1
                else:
                    break
            else:
                break
            p += 1
        
        return count
    
    def would_exceed_limit(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                          teacher_id: str, day: int, period: int, 
                          periods_per_day: int) -> bool:
        """
        Check if assigning a period would exceed max consecutive limit.
        """
        max_allowed = self.get_max_consecutive(teacher_id)
        
        # Count what consecutive would be after adding this period
        consecutive = self.count_consecutive(schedule, teacher_id, day, period, periods_per_day)
        
        return consecutive > max_allowed
    
    def find_best_slot_with_gaps(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                                teacher_id: str, day: int,
                                preferred_periods: List[int],
                                unavailable_periods: List[int],
                                periods_per_day: int) -> Optional[int]:
        """
        Find best slot that respects max consecutive constraint.
        
        Prefers:
        1. Preferred periods that don't exceed limit
        2. Available periods with gaps
        3. Any available period
        """
        max_allowed = self.get_max_consecutive(teacher_id)
        
        # Try preferred periods first
        for period in preferred_periods:
            if period in unavailable_periods:
                continue
            
            # Check if slot is available
            key = (day, period)
            if key in schedule:
                continue
            
            # Check if adding here would exceed limit
            if not self.would_exceed_limit(schedule, teacher_id, day, period, periods_per_day):
                return period
        
        # Find available periods that don't exceed limit
        available = self.find_gaps(schedule, teacher_id, day, periods_per_day)
        for period in available:
            if period in unavailable_periods:
                continue
            if not self.would_exceed_limit(schedule, teacher_id, day, period, periods_per_day):
                return period
        
        # If nothing fits, return first available (let solver handle conflict)
        return available[0] if available else None
    
    def enforce_consecutive_limits(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                                   teacher_id: str, day: int, 
                                   periods_per_day: int) -> List[Tuple[int, int]]:
        """
        Find all period assignments that exceed max consecutive limit.
        
        Returns list of (period, current_consecutive_count) that exceed limit.
        """
        max_allowed = self.get_max_consecutive(teacher_id)
        violations = []
        
        # Find consecutive runs
        consecutive_count = 0
        consecutive_start = -1
        
        for p in range(periods_per_day):
            key = (day, p)
            if key in schedule:
                _, assigned_teacher, _ = schedule[key]
                if assigned_teacher == teacher_id:
                    if consecutive_count == 0:
                        consecutive_start = p
                    consecutive_count += 1
                else:
                    if consecutive_count > max_allowed:
                        for v in range(consecutive_start, p):
                            violations.append((v, consecutive_count))
                    consecutive_count = 0
            else:
                # Gap (unassigned)
                if consecutive_count > max_allowed and consecutive_count > 0:
                    for v in range(consecutive_start, p):
                        violations.append((v, consecutive_count))
                consecutive_count = 0
        
        # Check end of day
        if consecutive_count > max_allowed and consecutive_count > 0:
            for v in range(consecutive_start, periods_per_day):
                violations.append((v, consecutive_count))
        
        return violations
    
    def get_schedule_by_teacher(self, schedule: Dict[Tuple[int, int], Tuple[str, str, str]], 
                               teacher_id: str, day: int, periods_per_day: int) -> List[Tuple[int, str]]:
        """
        Get all period assignments for a teacher on a given day.
        
        Returns list of (period, subject).
        """
        assignments = []
        for p in range(periods_per_day):
            key = (day, p)
            if key in schedule:
                class_id, assigned_teacher, subject = schedule[key]
                if assigned_teacher == teacher_id:
                    assignments.append((p, subject))
        return assignments


def apply_consecutive_period_heuristic(
    schedule: Dict[Tuple[int, int], Tuple[str, str, str]],
    teacher_preferences: Dict[str, Dict[int, List[int]]],  # teacher_id -> day -> preferred periods
    max_consecutive: int = 3
) -> Dict[Tuple[int, int], Tuple[str, str, str]]:
    """
    Apply consecutive period heuristics to improve schedule.
    
    This is a post-processing heuristic that tries to distribute
    periods more evenly for teachers.
    """
    # This would be called as a post-processing step
    # to reorganize the schedule to respect consecutive limits
    
    return schedule


def calculate_consecutive_stats(
    schedule: Dict[Tuple[int, int], Tuple[str, str, str]],
    teacher_id: str,
    days: List[str],
    periods_per_day: int
) -> Dict[str, Dict]:
    """
    Calculate consecutive period statistics for a teacher.
    
    Returns detailed stats per day.
    """
    stats = {}
    
    for day_idx, day_name in enumerate(days):
        assignments = []
        for p in range(periods_per_day):
            key = (day_idx, p)
            if key in schedule:
                class_id, assigned_teacher, subject = schedule[key]
                if assigned_teacher == teacher_id:
                    assignments.append(p)
        
        # Find consecutive runs
        runs = []
        if assignments:
            run_start = assignments[0]
            run_length = 1
            
            for i in range(1, len(assignments)):
                if assignments[i] == assignments[i-1] + 1:
                    run_length += 1
                else:
                    runs.append((run_start, run_length))
                    run_start = assignments[i]
                    run_length = 1
            
            runs.append((run_start, run_length))
        
        max_run = max([r[1] for r in runs]) if runs else 0
        
        stats[day_name] = {
            "total_periods": len(assignments),
            "consecutive_runs": runs,
            "max_consecutive": max_run,
            "periods": assignments
        }
    
    return stats
