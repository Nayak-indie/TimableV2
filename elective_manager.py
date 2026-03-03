"""
elective_manager.py — Elective / Optional Classes Management

Manages elective subject selection and ensures no conflicts.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field


# File path for electives
ELECTIVES_FILE = Path(__file__).parent / "data" / "electives.json"


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    ELECTIVES_FILE.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class ElectiveGroup:
    """Represents a group of elective subjects."""
    group_name: str  # e.g., "Science Electives", "Arts"
    subjects: List[str]  # Available subjects in this group
    min_select: int = 1  # Minimum to select
    max_select: int = 1  # Maximum to select


@dataclass
class StudentElective:
    """Elective choice for a student."""
    student_id: str
    class_id: str
    group_name: str
    selected_subjects: List[str]


def load_elective_groups() -> Dict[str, ElectiveGroup]:
    """Load elective groups from disk."""
    _ensure_data_dir()
    
    if not ELECTIVES_FILE.exists():
        return {}
    
    try:
        with open(ELECTIVES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        groups = {}
        for name, info in data.get("groups", {}).items():
            groups[name] = ElectiveGroup(
                group_name=name,
                subjects=info.get("subjects", []),
                min_select=info.get("min_select", 1),
                max_select=info.get("max_select", 1)
            )
        return groups
    except (json.JSONDecodeError, KeyError):
        return {}


def save_elective_groups(groups: Dict[str, ElectiveGroup]) -> None:
    """Save elective groups to disk."""
    _ensure_data_dir()
    
    data = {
        "groups": {
            name: {
                "subjects": g.subjects,
                "min_select": g.min_select,
                "max_select": g.max_select
            }
            for name, g in groups.items()
        }
    }
    
    with open(ELECTIVES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_student_electives() -> Dict[str, List[str]]:
    """Load student elective selections."""
    _ensure_data_dir()
    
    if not ELECTIVES_FILE.exists():
        return {}
    
    try:
        with open(ELECTIVES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("student_selections", {})
    except (json.JSONDecodeError, KeyError):
        return {}


def save_student_electives(selections: Dict[str, List[str]]) -> None:
    """Save student elective selections."""
    _ensure_data_dir()
    
    # Load existing data
    data = {}
    if ELECTIVES_FILE.exists():
        try:
            with open(ELECTIVES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}
    
    data["student_selections"] = selections
    
    with open(ELECTIVES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_elective_group(group_name: str, subjects: List[str], 
                      min_select: int = 1, max_select: int = 1) -> None:
    """Add a new elective group."""
    groups = load_elective_groups()
    groups[group_name] = ElectiveGroup(
        group_name=group_name,
        subjects=subjects,
        min_select=min_select,
        max_select=max_select
    )
    save_elective_groups(groups)


def remove_elective_group(group_name: str) -> None:
    """Remove an elective group."""
    groups = load_elective_groups()
    if group_name in groups:
        del groups[group_name]
        save_elective_groups(groups)


def get_elective_subjects(class_id: str) -> List[str]:
    """Get all elective subjects for a class."""
    groups = load_elective_groups()
    all_subjects = []
    for group in groups.values():
        all_subjects.extend(group.subjects)
    return all_subjects


def validate_electives(class_id: str, selected: Dict[str, List[str]]) -> tuple[bool, List[str]]:
    """
    Validate that elective selections meet requirements.
    
    Returns:
        (is_valid, error_messages)
    """
    groups = load_elective_groups()
    errors = []
    
    for group_name, group in groups.items():
        selected_count = len(selected.get(group_name, []))
        
        if selected_count < group.min_select:
            errors.append(f"Group '{group_name}': need at least {group.min_select}, got {selected_count}")
        
        if selected_count > group.max_select:
            errors.append(f"Group '{group_name}': can select max {group.max_select}, got {selected_count}")
    
    return len(errors) == 0, errors


def get_elective_conflicts(
    elective_subjects: List[str],
    assigned_subjects: List[str]
) -> List[str]:
    """
    Check for conflicts between elective and core subjects.
    
    Returns list of conflicting subjects.
    """
    return [s for s in elective_subjects if s in assigned_subjects]


def format_electives_for_display(groups: Dict[str, ElectiveGroup]) -> str:
    """Format elective groups for display."""
    lines = []
    for name, group in groups.items():
        lines.append(f"**{name}**: {', '.join(group.subjects)} (Select {group.min_select}-{group.max_select})")
    return "\n".join(lines) if lines else "No elective groups configured."
