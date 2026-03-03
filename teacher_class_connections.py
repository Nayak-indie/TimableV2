"""
teacher_class_connections.py — Visual Teacher-Class Connections

Prepares data for network graph visualization of teacher-class connections.
"""

from typing import Dict, List, Tuple, Any
from pathlib import Path

# Subject groups for color coding
SUBJECT_GROUPS = {
    "Physics": "Science",
    "Chemistry": "Science",
    "Biology": "Science",
    "Computer Science": "Science",
    "Mathematics": "Mathematics",
    "Economics": "Commerce",
    "Accountancy": "Commerce",
    "Business Studies": "Commerce",
    "History": "Humanities",
    "Political Science": "Humanities",
    "Geography": "Humanities",
    "English": "Language",
    "Hindi": "Language",
    "Physical Education": "Sports",
    "Art": "Arts",
    "Music": "Arts",
}

# Stream/Class groups for color coding
STREAM_COLORS = {
    "11NM": "Science",
    "12NM": "Science",
    "11M": "Science",
    "12M": "Science",
    "11SCI": "Science",
    "12SCI": "Science",
    "11COM": "Commerce",
    "12COM": "Commerce",
    "11HUM": "Humanities",
    "12HUM": "Humanities",
    "11CS": "Computer Science",
    "12CS": "Computer Science",
}

# Color palettes
SUBJECT_COLORS = {
    "Science": "#FF6B6B",      # Red
    "Mathematics": "#4ECDC4",  # Teal
    "Commerce": "#45B7D1",      # Blue
    "Humanities": "#96CEB4",   # Green
    "Language": "#FFEAA7",     # Yellow
    "Sports": "#DDA0DD",       # Plum
    "Arts": "#FF8C94",         # Pink
    "Computer Science": "#9B59B6",  # Purple
}

STREAM_PALETTE = {
    "Science": "#FF6B6B",
    "Commerce": "#45B7D1",
    "Humanities": "#96CEB4",
    "Computer Science": "#9B59B6",
}


def get_subject_group(subject: str) -> str:
    """Get the group for a subject."""
    return SUBJECT_GROUPS.get(subject, "Other")


def get_subject_color(subject: str) -> str:
    """Get color for a subject group."""
    group = get_subject_group(subject)
    return SUBJECT_COLORS.get(group, "#CCCCCC")


def get_class_stream(class_id: str) -> str:
    """Determine stream from class ID."""
    class_upper = class_id.upper()
    
    # Check for explicit streams
    if "COM" in class_upper or "ACCOUNT" in class_upper or "BUSINESS" in class_upper:
        return "Commerce"
    if "HUM" in class_upper or "HIST" in class_upper or "GEOG" in class_upper:
        return "Humanities"
    if "CS" in class_upper or "COMP" in class_upper:
        return "Computer Science"
    if "M" in class_upper or "SCI" in class_upper or "PHY" in class_upper or "CHEM" in class_upper or "BIO" in class_upper or "MATH" in class_upper:
        return "Science"
    
    return "General"


def get_stream_color(class_id: str) -> str:
    """Get color for a class stream."""
    stream = get_class_stream(class_id)
    return STREAM_PALETTE.get(stream, "#CCCCCC")


def prepare_connections(teachers: List, classes: List) -> Dict[str, Any]:
    """
    Prepare connection data for network graph.
    
    Returns:
        {
            "nodes": [
                {"id": "teacher_Eric Simon", "label": "Eric Simon", "type": "teacher", "color": "#color", "subjects": ["Physics"]},
                {"id": "class_11SCI", "label": "11SCI", "type": "class", "color": "#color", "stream": "Science"}
            ],
            "edges": [
                {"from": "teacher_Eric Simon", "to": "class_11SCI", "subject": "Physics", "periods": 6, "width": 3}
            ]
        }
    """
    nodes = []
    edges = []
    node_ids = set()
    
    # Add teacher nodes
    for teacher in teachers:
        node_id = f"teacher_{teacher.teacher_id}"
        if node_id not in node_ids:
            # Get primary subject for color
            primary_subject = teacher.subjects[0] if teacher.subjects else "Other"
            color = get_subject_color(primary_subject)
            
            nodes.append({
                "id": node_id,
                "label": teacher.teacher_id,
                "type": "teacher",
                "color": color,
                "subjects": teacher.subjects,
                "max_periods_per_day": teacher.max_periods_per_day,
                "title": f"<b>{teacher.teacher_id}</b><br>Subjects: {', '.join(teacher.subjects)}<br>Max {teacher.max_periods_per_day} periods/day"
            })
            node_ids.add(node_id)
    
    # Add class nodes and edges
    for cls in classes:
        class_node_id = f"class_{cls.id}"
        if class_node_id not in node_ids:
            stream = get_class_stream(cls.id)
            color = get_stream_color(cls.id)
            
            subjects_str = ", ".join([f"{cs.subject}({cs.weekly_periods})" for cs in cls.subjects])
            
            nodes.append({
                "id": class_node_id,
                "label": cls.id,
                "type": "class",
                "color": color,
                "stream": stream,
                "title": f"<b>{cls.id}</b><br>Stream: {stream}<br>{subjects_str}"
            })
            node_ids.add(class_node_id)
        
        # Create edges from teacher to class
        for cs in cls.subjects:
            teacher_node_id = f"teacher_{cs.teacher_id}"
            
            # Ensure teacher node exists
            if teacher_node_id not in node_ids:
                color = get_subject_color(cs.subject)
                nodes.append({
                    "id": teacher_node_id,
                    "label": cs.teacher_id,
                    "type": "teacher",
                    "color": color,
                    "subjects": [cs.subject],
                    "title": f"<b>{cs.teacher_id}</b><br>Subject: {cs.subject}"
                })
                node_ids.add(teacher_node_id)
            
            # Edge with thickness based on periods
            edge_width = min(10, max(1, cs.weekly_periods / 2))
            
            edges.append({
                "from": teacher_node_id,
                "to": class_node_id,
                "subject": cs.subject,
                "periods": cs.weekly_periods,
                "width": edge_width,
                "title": f"<b>{cs.teacher_id}</b> → <b>{cls.id}</b><br>Subject: {cs.subject}<br>Periods/week: {cs.weekly_periods}"
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_teachers": len([n for n in nodes if n["type"] == "teacher"]),
            "total_classes": len([n for n in nodes if n["type"] == "class"]),
            "total_connections": len(edges)
        }
    }


def get_legend() -> List[Dict]:
    """Get legend data for the graph."""
    legend = []
    
    # Subject groups
    for group, color in SUBJECT_COLORS.items():
        legend.append({
            "label": group,
            "color": color,
            "type": "subject"
        })
    
    return legend
