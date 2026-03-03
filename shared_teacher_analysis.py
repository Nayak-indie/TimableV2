"""
shared_teacher_analysis.py — Shared Teacher Analysis & Management

Analyzes teachers teaching multiple classes and provides detailed insights.
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class SharedTeacherInfo:
    """Information about a teacher teaching multiple classes."""
    teacher_id: str
    subjects: List[str]
    classes_assigned: List[str]
    total_periods_per_week: int
    max_possible_periods: int
    is_overloaded: bool
    overload_amount: int
    utilization_percentage: float
    recommended_max_per_day: int


def analyze_shared_teachers(teachers: List, classes: List, config) -> Dict[str, SharedTeacherInfo]:
    """
    Analyze all teachers and identify shared ones.
    
    Returns:
        {teacher_id: SharedTeacherInfo}
    """
    results = {}
    num_days = len(config.days)
    
    for teacher in teachers:
        teacher_id = teacher.teacher_id
        
        # Find all classes where this teacher is assigned
        classes_assigned = []
        subjects = {}
        total_periods = 0
        
        for cls in classes:
            for cs in cls.subjects:
                if cs.teacher_id == teacher_id:
                    classes_assigned.append(cls.id)
                    if cs.subject not in subjects:
                        subjects[cs.subject] = 0
                    subjects[cs.subject] += cs.weekly_periods
                    total_periods += cs.weekly_periods
        
        # Calculate max possible periods
        max_possible = teacher.max_periods_per_day * num_days
        
        # Check overload
        is_overloaded = total_periods > max_possible
        overload_amount = max(0, total_periods - max_possible)
        
        # Calculate utilization
        utilization = (total_periods / max_possible * 100) if max_possible > 0 else 0
        
        # Recommended max per day
        recommended_max = (total_periods + num_days - 1) // num_days  # ceil
        
        results[teacher_id] = SharedTeacherInfo(
            teacher_id=teacher_id,
            subjects=list(subjects.keys()),
            classes_assigned=classes_assigned,
            total_periods_per_week=total_periods,
            max_possible_periods=max_possible,
            is_overloaded=is_overloaded,
            overload_amount=overload_amount,
            utilization_percentage=round(utilization, 1),
            recommended_max_per_day=recommended_max
        )
    
    return results


def get_shared_teachers(teachers: List, classes: List, config) -> List[SharedTeacherInfo]:
    """
    Get list of teachers teaching multiple classes.
    """
    all_info = analyze_shared_teachers(teachers, classes, config)
    return [info for info in all_info.values() if len(info.classes_assigned) > 1]


def get_overloaded_teachers(teachers: List, classes: List, config) -> List[SharedTeacherInfo]:
    """
    Get list of overloaded teachers.
    """
    all_info = analyze_shared_teachers(teachers, classes, config)
    return [info for info in all_info.values() if info.is_overloaded]


def generate_sharing_recommendations(teachers: List, classes: List, config) -> List[str]:
    """
    Generate recommendations for sharing teacher workload.
    """
    recommendations = []
    shared = get_shared_teachers(teachers, classes, config)
    
    for info in shared:
        if info.is_overloaded:
            recommendations.append(
                f"⚠️ **{info.teacher_id}** is overloaded: "
                f"{info.total_periods_per_week} periods needed, "
                f"max {info.max_possible_periods} possible. "
                f"Consider splitting {info.subjects[0] if info.subjects else 'subjects'} with another teacher."
            )
        elif info.utilization_percentage > 80:
            recommendations.append(
                f"💡 **{info.teacher_id}** is at {info.utilization_percentage}% utilization. "
                f"May need backup for {info.subjects[0] if info.subjects else 'subjects'}."
            )
    
    return recommendations


def get_subject_distribution(teachers: List, classes: List) -> Dict[str, List[str]]:
    """
    Get which classes each subject is taught in.
    
    Returns:
        {subject: [class_ids]}
    """
    distribution = {}
    
    for cls in classes:
        for cs in cls.subjects:
            if cs.subject not in distribution:
                distribution[cs.subject] = []
            if cls.id not in distribution[cs.subject]:
                distribution[cs.subject].append(cls.id)
    
    return distribution
