"""
load_balancer.py — Subject Load Balancing Across Days

Ensures even distribution of subject periods across the week.
"""

from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from models import Class, SchoolConfig, Teacher


@dataclass
class SubjectDistribution:
    """Represents how a subject's periods are distributed."""
    subject: str
    class_id: str
    teacher_id: str
    weekly_periods: int
    periods_per_day: List[int]  # List of periods per day
    is_balanced: bool


@dataclass
class LoadBalanceStats:
    """Statistics about load balancing."""
    total_classes: int
    balanced_subjects: int
    unbalanced_subjects: int
    max_daily_variance: int
    recommendations: List[str]


def calculate_ideal_distribution(weekly_periods: int, num_days: int) -> List[int]:
    """
    Calculate ideal periods per day for even distribution.
    
    Example: 5 periods over 3 days -> [2, 2, 1] or [2, 1, 2]
    """
    base = weekly_periods // num_days
    remainder = weekly_periods % num_days
    
    # Distribute remainders evenly at the start
    distribution = [base] * num_days
    for i in range(remainder):
        distribution[i] += 1
    
    return distribution


def analyze_subject_distribution(
    classes: List[Class], 
    config: SchoolConfig,
    timetable: Dict[Tuple[str, int, int], Tuple[str, str]] = None
) -> Dict[str, SubjectDistribution]:
    """
    Analyze how subjects are distributed across days.
    
    If timetable is provided, analyzes actual distribution.
    If not, calculates ideal distribution.
    """
    results = {}
    num_days = len(config.days)
    
    for cls in classes:
        for cs in cls.subjects:
            key = f"{cls.id}_{cs.subject}"
            
            if timetable:
                # Analyze actual distribution from timetable
                actual = [0] * num_days
                for (cid, day, period), (subj, tid) in timetable.items():
                    if cid == cls.id and subj == cs.subject:
                        actual[day] += 1
                
                is_balanced = max(actual) - min([a for a in actual if a > 0]) <= 1 if any(actual) else True
                
                results[key] = SubjectDistribution(
                    subject=cs.subject,
                    class_id=cls.id,
                    teacher_id=cs.teacher_id,
                    weekly_periods=cs.weekly_periods,
                    periods_per_day=actual,
                    is_balanced=is_balanced
                )
            else:
                # Calculate ideal distribution
                ideal = calculate_ideal_distribution(cs.weekly_periods, num_days)
                
                results[key] = SubjectDistribution(
                    subject=cs.subject,
                    class_id=cls.id,
                    teacher_id=cs.teacher_id,
                    weekly_periods=cs.weekly_periods,
                    periods_per_day=ideal,
                    is_balanced=True
                )
    
    return results


def get_load_balance_stats(
    classes: List[Class],
    config: SchoolConfig,
    timetable: Dict[Tuple[str, int, int], Tuple[str, str]]
) -> LoadBalanceStats:
    """
    Get overall load balancing statistics.
    """
    distribution = analyze_subject_distribution(classes, config, timetable)
    
    balanced = sum(1 for d in distribution.values() if d.is_balanced)
    unbalanced = len(distribution) - balanced
    
    # Calculate max daily variance
    max_variance = 0
    for d in distribution.values():
        non_zero = [p for p in d.periods_per_day if p > 0]
        if non_zero:
            variance = max(non_zero) - min(non_zero)
            max_variance = max(max_variance, variance)
    
    # Generate recommendations
    recommendations = []
    for key, dist in distribution.items():
        if not dist.is_balanced:
            recommendations.append(
                f"⚠️ **{dist.class_id} - {dist.subject}**: "
                f"Periods per day vary too much: {dist.periods_per_day}"
            )
    
    # Check for teacher overload across days
    teacher_daily_load = {}
    for (cid, day, period), (subj, tid) in timetable.items():
        if tid not in teacher_daily_load:
            teacher_daily_load[tid] = [0] * len(config.days)
        teacher_daily_load[tid][day] += 1
    
    for tid, daily in teacher_daily_load.items():
        non_zero = [d for d in daily if d > 0]
        if non_zero and max(non_zero) - min(non_zero) > 2:
            recommendations.append(
                f"💡 **{tid}**: Daily load varies significantly: {daily}"
            )
    
    return LoadBalanceStats(
        total_classes=len(classes),
        balanced_subjects=balanced,
        unbalanced_subjects=unbalanced,
        max_daily_variance=max_variance,
        recommendations=recommendations
    )


def suggest_balanced_schedule(
    weekly_periods: int,
    num_days: int,
    fixed_slots: Dict[int, List[int]] = None  # day -> [forbidden periods]
) -> List[int]:
    """
    Suggest which days should have the subject for best balance.
    
    Returns list of period counts per day.
    """
    if fixed_slots is None:
        fixed_slots = {}
    
    # Start with ideal distribution
    ideal = calculate_ideal_distribution(weekly_periods, num_days)
    
    # Adjust for fixed slots (like unavailable days)
    result = ideal.copy()
    for day_idx, forbidden in fixed_slots.items():
        if day_idx < len(result):
            result[day_idx] = min(result[day_idx], config.periods_per_day - len(forbidden))
    
    return result


def enforce_load_balance(
    timetable: Dict[Tuple[str, int, int], Tuple[str, str]],
    classes: List[Class],
    config: SchoolConfig,
    max_variance: int = 1
) -> Dict[Tuple[str, int, int], Tuple[str, str]]:
    """
    Post-process timetable to improve load balancing.
    
    This is a heuristic that tries to swap periods to achieve better balance.
    Returns the (optionally) improved timetable.
    """
    # This would be called as a post-processing step
    # For now, return the original as the solver already tries to balance
    
    return timetable


def get_teacher_daily_load(
    timetable: Dict[Tuple[str, int, int], Tuple[str, str]],
    config: SchoolConfig
) -> Dict[str, List[int]]:
    """
    Get daily teaching load for each teacher.
    
    Returns:
        {teacher_id: [count_day_0, count_day_1, ...]}
    """
    load = {}
    
    for (cid, day, period), (subj, tid) in timetable.items():
        if tid not in load:
            load[tid] = [0] * len(config.days)
        load[tid][day] += 1
    
    return load


def calculate_teacher_balance_score(teacher_load: List[int]) -> float:
    """
    Calculate how balanced a teacher's daily load is.
    
    Returns:
        0.0 = perfectly balanced, higher = less balanced
    """
    if not teacher_load:
        return 0.0
    
    non_zero = [l for l in teacher_load if l > 0]
    if len(non_zero) <= 1:
        return 0.0
    
    return max(non_zero) - min(non_zero)
