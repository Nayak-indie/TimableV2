"""
teacher_preferences.py — Teacher Availability & Preference Management

Collects and stores teacher preferences for preferred teaching periods.
Applies as soft constraints during timetable generation.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

# File path for preferences
PREFERENCES_FILE = Path(__file__).parent.parent / "data" / "teacher_preferences.json"


@dataclass
class TeacherPreference:
    """Individual teacher preference data."""
    teacher_id: str
    preferred_periods: Dict[int, List[int]] = field(default_factory=dict)  # day_index -> [period_indices]
    unavailable_periods: Dict[int, List[int]] = field(default_factory=dict)  # day_index -> [period_indices]
    max_consecutive_periods: int = 3  # Max periods in a row


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_preferences() -> Dict[str, TeacherPreference]:
    """Load teacher preferences from disk."""
    _ensure_data_dir()
    
    if not PREFERENCES_FILE.exists():
        return {}
    
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        preferences = {}
        for teacher_id, prefs in data.items():
            preferences[teacher_id] = TeacherPreference(
                teacher_id=teacher_id,
                preferred_periods=prefs.get("preferred_periods", {}),
                unavailable_periods=prefs.get("unavailable_periods", {}),
                max_consecutive_periods=prefs.get("max_consecutive_periods", 3),
            )
        return preferences
    except (json.JSONDecodeError, KeyError):
        return {}


def save_preferences(preferences: Dict[str, TeacherPreference]) -> None:
    """Save teacher preferences to disk."""
    _ensure_data_dir()
    
    data = {}
    for teacher_id, prefs in preferences.items():
        data[teacher_id] = {
            "preferred_periods": prefs.preferred_periods,
            "unavailable_periods": prefs.unavailable_periods,
            "max_consecutive_periods": prefs.max_consecutive_periods,
        }
    
    with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_teacher_preference(teacher_id: str) -> TeacherPreference:
    """Get preference for a specific teacher."""
    prefs = load_preferences()
    if teacher_id not in prefs:
        prefs[teacher_id] = TeacherPreference(teacher_id=teacher_id)
    return prefs[teacher_id]


def update_teacher_preference(teacher_id: str, preference: TeacherPreference) -> None:
    """Update preference for a specific teacher."""
    prefs = load_preferences()
    prefs[teacher_id] = preference
    save_preferences(prefs)


def clear_preferences() -> None:
    """Clear all teacher preferences."""
    if PREFERENCES_FILE.exists():
        PREFERENCES_FILE.unlink()


# --- Soft Constraint Application ---

def is_period_preferred(teacher_id: str, day: int, period: int) -> bool:
    """Check if a period is preferred by the teacher."""
    prefs = load_preferences()
    if teacher_id not in prefs:
        return True  # No preferences = all periods OK
    
    preferred = prefs[teacher_id].preferred_periods
    return day not in preferred or period in preferred.get(day, [])


def is_period_available(teacher_id: str, day: int, period: int) -> bool:
    """Check if a period is marked as unavailable by the teacher."""
    prefs = load_preferences()
    if teacher_id not in prefs:
        return True  # No preferences = all periods available
    
    unavailable = prefs[teacher_id].unavailable_periods
    return day not in unavailable or period not in unavailable.get(day, [])


def get_available_periods(teacher_id: str, day: int) -> List[int]:
    """Get list of available periods for a teacher on a given day."""
    prefs = load_preferences()
    if teacher_id not in prefs:
        # Return all periods 0-7 if no preferences set
        return list(range(8))
    
    unavailable = prefs[teacher_id].unavailable_periods
    all_periods = set(range(8))
    
    if day in unavailable:
        unavailable_set = set(unavailable[day])
        return sorted(all_periods - unavailable_set)
    
    return sorted(all_periods)


def get_preferred_periods(teacher_id: str, day: int) -> List[int]:
    """Get list of preferred periods for a teacher on a given day."""
    prefs = load_preferences()
    if teacher_id not in prefs:
        return list(range(8))  # All periods preferred if no preferences
    
    preferred = prefs[teacher_id].preferred_periods
    return preferred.get(day, list(range(8)))


def score_period_assignment(teacher_id: str, day: int, period: int) -> float:
    """
    Score a period assignment (lower is better).
    Used to prioritize preferred slots during scheduling.
    
    Score ranges:
    - 0: Perfect preferred slot
    - 1-10: Available but not preferred
    - 100: Unavailable (should not be assigned)
    """
    if not is_period_available(teacher_id, day, period):
        return 100  # Unavailable
    
    prefs = load_preferences()
    if teacher_id not in prefs:
        return 1  # Neutral if no preferences
    
    preferred = prefs[teacher_id].preferred_periods
    if day in preferred and period in preferred.get(day, []):
        return 0  # Perfect match
    
    return 5  # Available but not preferred


def apply_soft_constraints(teacher_id: str, available_slots: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Apply soft constraints to filter/sort available slots.
    Returns slots sorted by preference (preferred first).
    
    Args:
        teacher_id: The teacher to filter for
        available_slots: List of (day, period) tuples
    
    Returns:
        Sorted list of (day, period) tuples
    """
    # Score each slot
    scored = []
    for day, period in available_slots:
        score = score_period_assignment(teacher_id, day, period)
        scored.append((score, day, period))
    
    # Sort by score (lower is better)
    scored.sort()
    
    return [(day, period) for score, day, period in scored]
