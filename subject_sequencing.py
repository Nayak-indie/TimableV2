"""
subject_sequencing.py — Subject Prerequisites & Sequencing

Manages subject prerequisites per class and enforces sequencing during generation.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

# File path for sequencing rules
SEQUENCING_FILE = Path(__file__).parent / "data" / "subject_prerequisites.json"


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    SEQUENCING_FILE.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class SubjectPrerequisite:
    """Represents a subject prerequisite relationship."""
    class_id: str
    subject: str
    prerequisites: List[str] = field(default_factory=list)


def load_prerequisites() -> Dict[str, Dict[str, List[str]]]:
    """
    Load subject prerequisites from disk.
    
    Returns:
        {
            "11SCI": {
                "Physics": ["Mathematics"],
                "Chemistry": [],
                "Mathematics": []
            }
        }
    """
    _ensure_data_dir()
    
    if not SEQUENCING_FILE.exists():
        return {}
    
    try:
        with open(SEQUENCING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return {}


def save_prerequisites(prereqs: Dict[str, Dict[str, List[str]]]) -> None:
    """Save subject prerequisites to disk."""
    _ensure_data_dir()
    
    with open(SEQUENCING_FILE, "w", encoding="utf-8") as f:
        json.dump(prereqs, f, indent=2)


def get_prerequisites(class_id: str, subject: str) -> List[str]:
    """Get prerequisites for a specific subject in a class."""
    prereqs = load_prerequisites()
    return prereqs.get(class_id, {}).get(subject, [])


def add_prerequisite(class_id: str, subject: str, prerequisite: str) -> None:
    """Add a prerequisite for a subject."""
    prereqs = load_prerequisites()
    
    if class_id not in prereqs:
        prereqs[class_id] = {}
    
    if subject not in prereqs[class_id]:
        prereqs[class_id][subject] = []
    
    if prerequisite not in prereqs[class_id][subject]:
        prereqs[class_id][subject].append(prerequisite)
    
    save_prerequisites(prereqs)


def remove_prerequisite(class_id: str, subject: str, prerequisite: str) -> None:
    """Remove a prerequisite."""
    prereqs = load_prerequisites()
    
    if class_id in prereqs and subject in prereqs[class_id]:
        if prerequisite in prereqs[class_id][subject]:
            prereqs[class_id][subject].remove(prerequisite)
    
    save_prerequisites(prereqs)


def clear_prerequisites() -> None:
    """Clear all prerequisites."""
    if SEQUENCING_FILE.exists():
        SEQUENCING_FILE.unlink()


def get_subject_order(class_id: str, subjects: List[str]) -> List[str]:
    """
    Get subjects in prerequisite order (prerequisites first).
    
    Uses topological sort to order subjects so prerequisites come first.
    """
    prereqs = load_prerequisites()
    class_prereqs = prereqs.get(class_id, {})
    
    # Build adjacency list
    graph = {s: [] for s in subjects}
    in_degree = {s: 0 for s in subjects}
    
    for subject, prereq_list in class_prereqs.items():
        if subject not in subjects:
            continue
        for prereq in prereq_list:
            if prereq in subjects:
                graph[prereq].append(subject)
                in_degree[subject] += 1
    
    # Topological sort (Kahn's algorithm)
    queue = [s for s in subjects if in_degree[s] == 0]
    result = []
    
    while queue:
        current = queue.pop(0)
        result.append(current)
        
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Add any remaining subjects (shouldn't happen with valid prerequisites)
    for s in subjects:
        if s not in result:
            result.append(s)
    
    return result


def validate_prerequisites(class_id: str, subjects: List[str]) -> tuple[bool, List[str]]:
    """
    Validate prerequisites for a class.
    
    Returns:
        (is_valid, error_messages)
    """
    prereqs = load_prerequisites()
    class_prereqs = prereqs.get(class_id, {})
    
    errors = []
    
    for subject, prereq_list in class_prereqs.items():
        for prereq in prereq_list:
            if prereq not in subjects:
                errors.append(f"Prerequisite '{prereq}' for '{subject}' in {class_id} does not exist in class subjects")
    
    return len(errors) == 0, errors


def get_sequencing_info(class_id: str, subject: str) -> Dict:
    """Get detailed sequencing info for a subject."""
    prereqs = load_prerequisites()
    class_prereqs = prereqs.get(class_id, {})
    
    return {
        "prerequisites": class_prereqs.get(subject, []),
        "is_first": len(class_prereqs.get(subject, [])) == 0,
        "total_subjects": len(class_prereqs)
    }
