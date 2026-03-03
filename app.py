"""
Smart Timetable Builder – Streamlit front-end.

Clean rebuild of the main app:
- Stable Streamlit layout (no backend code leaked into UI)
- Dark, colorful, beginner‑friendly design
- Uses the existing solver / storage / PDF modules
"""

from __future__ import annotations

import copy
from datetime import timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from models import Class, ClassPriorityConfig, ClassSubject, SchoolConfig, Teacher
import plotly.express as px

from pdf_export import (
    export_class_timetables_pdf,
    export_teacher_timetables_pdf,
    flat_to_class_timetables,
)
from solver.engine import invert_to_teacher_timetable, solve_timetable
from solver.constraint_manager import manage_constraints
from solver.rotation import generate_rotations
from storage import (
    append_history,
    clear_base_timetable,
    clear_demo_loaded,
    clear_scenario_state,
    is_demo_loaded,
    load_base_timetable,
    load_classes,
    load_config,
    load_history,
    load_priority_configs,
    load_scenario_state,
    load_teachers,
    save_base_timetable,
    save_classes,
    save_config,
    save_scenario_state,
    save_teachers,
    set_demo_loaded,
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

ANIMATION_CSS = """
<style>
    /* GitHub / Medium‑style dark UI */
    .main {
        background-color: #0d1117;
        color: #f0f6fc;
    }
    .main .block-container {
        padding-top: 32px;
        padding-bottom: 32px;
    }
    h1, h2, h3 {
        color: #f0f6fc !important;
    }
    p, span, label, .stMarkdown {
        color: #c9d1d9 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label {
        color: #e6edf3 !important;
    }

    /* Tabs */
    .stTabs {
        background-color: transparent;
        padding: 6px 8px;
        border-radius: 10px;
    }
    .stTabs > div > div { background-color: transparent; }
    .stTabs [data-baseweb="tab-list"]{
        background-color: #0d1117;
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #30363d;
        box-shadow: 0 0 0 1px rgba(240,246,252,0.02);
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8b949e;
        border-radius: 6px;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: #161b22;
    }
    .stTabs [aria-selected="true"] {
        background-color: #161b22;
        color: #ffffff !important;
        box-shadow: 0 0 0 1px #f0f6fc;
    }

    /* Toasts */
    .toast-item {
        font-size: 13px;
        color: #e6edf3;
        max-width: 320px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        border-radius: 999px;
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 4px 10px;
        animation: toastFadeIn 0.2s ease-out;
    }
    @keyframes toastFadeIn {
        from { opacity: 0; transform: translateY(-3px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .toast-msg { flex: 1; }
    .toast-countdown { font-size: 11px; color: #8b949e; min-width: 24px; }

    /* Buttons */
    button {
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        border-radius: 6px !important;
        border: 1px solid #30363d !important;
    }
    button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    }
    button:active { transform: translateY(0); box-shadow: none; }
    .stButton button[kind="primary"] {
        background-color: #238636;
        color: #ffffff;
        border-color: #2ea043 !important;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #2ea043;
        border-color: #3fb950 !important;
    }
    .stButton button[kind="primary"]:active {
        background-color: #196c2e;
        border-color: #238636 !important;
    }

    /* Cards / expanders */
    .stExpander {
        animation: cardFadeIn 0.2s ease-out;
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    @keyframes cardFadeIn {
        from { opacity: 0; transform: translateY(2px); }
        to   { opacity: 1; transform: translateY(0); }
    }
</style>
"""


st.set_page_config(
    page_title="Smart Timetable Builder",
    page_icon="📅",
    layout="wide",
)
st.markdown(ANIMATION_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers / session state
# ---------------------------------------------------------------------------

Timetable = Dict[Tuple[str, int, int], Tuple[str, str]]


def deep_copy_tt(tt: Timetable | None) -> Timetable | None:
    return copy.deepcopy(tt) if tt is not None else None


def _shorten(text: str, max_len: int = 20) -> str:
    """Shorten long cell text so it fits inside timetable tables."""
    if not isinstance(text, str):
        text = str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _init_session() -> None:
    if "initialized" in st.session_state:
        return

    # Load from persistent storage first
    st.session_state.teachers: List[Teacher] = load_teachers()
    st.session_state.classes: List[Class] = load_classes()
    st.session_state.priority_configs: List[ClassPriorityConfig] = load_priority_configs()
    st.session_state.config: SchoolConfig = load_config()

    base = load_base_timetable()
    st.session_state.class_timetable: Timetable | None = base or None
    st.session_state.teacher_timetable: Dict[str, Dict[Tuple[int, int], Tuple[str, str]]] | None = None

    st.session_state.notifications: List[dict] = []
    st.session_state.scenario_state = load_scenario_state()

    st.session_state.initialized = True


def show_toast(msg: str, duration_sec: int = 3) -> None:
    uid = f"n_{len(st.session_state.notifications)}_{hash(msg)}"
    st.session_state.notifications.append(
        {"msg": msg, "until": timedelta(seconds=duration_sec), "id": uid}
    )


@st.fragment(run_every=timedelta(seconds=1))
def _notification_ticker() -> None:
    now = timedelta(seconds=0)
    notifications = st.session_state.get("notifications", [])
    active: List[dict] = []

    for n in notifications:
        remaining = n["until"] - timedelta(seconds=1)
        if remaining > now:
            n["until"] = remaining
            active.append(n)

    st.session_state.notifications = active

    for n in active:
        secs = int(n["until"].total_seconds())
        st.markdown(
            f"<div class='toast-item'><span class='toast-msg'>{n['msg']}</span>"
            f"<span class='toast-countdown'>{secs}s</span></div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------


def load_demo_into_session() -> None:
    """Populate in‑memory teachers/classes with demo data."""
    st.session_state.teachers = [
        Teacher(teacher_id="Eric Simon", name="Eric Simon", subjects=["Physics"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Aisha Khan", name="Aisha Khan", subjects=["Chemistry"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Rahul Mehta", name="Rahul Mehta", subjects=["Mathematics"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Neha Verma", name="Neha Verma", subjects=["Biology"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Daniel Brooks", name="Daniel Brooks", subjects=["English"], max_periods_per_day=4, max_periods_per_week=20, target_free_periods_per_day=4),
        Teacher(teacher_id="Priya Nair", name="Priya Nair", subjects=["Economics"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Arjun Patel", name="Arjun Patel", subjects=["Accountancy"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Kavita Rao", name="Kavita Rao", subjects=["Business Studies"], max_periods_per_day=4, max_periods_per_week=24, target_free_periods_per_day=4),
        Teacher(teacher_id="Sofia Mendes", name="Sofia Mendes", subjects=["History"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Aman Gupta", name="Aman Gupta", subjects=["Political Science"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Ritu Chawla", name="Ritu Chawla", subjects=["Geography"], max_periods_per_day=4, max_periods_per_week=24, target_free_periods_per_day=4),
        Teacher(teacher_id="Marcus Lee", name="Marcus Lee", subjects=["Physical Education"], max_periods_per_day=3, max_periods_per_week=15, target_free_periods_per_day=5),
        Teacher(teacher_id="Rashmi Joshi", name="Rashmi Joshi", subjects=["Hindi"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Vikram Singh", name="Vikram Singh", subjects=["Computer Science"], max_periods_per_day=5, max_periods_per_week=30, target_free_periods_per_day=3),
        Teacher(teacher_id="Anjali Roy", name="Anjali Roy", subjects=["Art"], max_periods_per_day=3, max_periods_per_week=15, target_free_periods_per_day=5),
    ]

    def cls(cid: str, subjects: List[Tuple[str, int, str]]) -> Class:
        return Class(id=cid, name=cid, subjects=[ClassSubject(s, w, t) for (s, w, t) in subjects])

    st.session_state.classes = [
        cls("11NM", [("Physics",6,"Eric Simon"),("Chemistry",6,"Aisha Khan"),("Mathematics",6,"Rahul Mehta"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("11M", [("Biology",6,"Neha Verma"),("Chemistry",6,"Aisha Khan"),("Physics",6,"Eric Simon"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("11COM", [("Accountancy",6,"Arjun Patel"),("Economics",6,"Priya Nair"),("Business Studies",6,"Kavita Rao"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("11HUM", [("History",6,"Sofia Mendes"),("Political Science",6,"Aman Gupta"),("Geography",6,"Ritu Chawla"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("12SCI", [("Physics",6,"Eric Simon"),("Chemistry",6,"Aisha Khan"),("Mathematics",6,"Rahul Mehta"),("Biology",6,"Neha Verma"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("12COM", [("Accountancy",6,"Arjun Patel"),("Economics",6,"Priya Nair"),("Business Studies",6,"Kavita Rao"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("12HUM", [("History",6,"Sofia Mendes"),("Political Science",6,"Aman Gupta"),("Geography",6,"Ritu Chawla"),("English",4,"Daniel Brooks"),("Hindi",3,"Rashmi Joshi"),("Physical Education",2,"Marcus Lee")]),
        cls("11CS", [("Computer Science",6,"Vikram Singh"),("English",4,"Daniel Brooks"),("Physical Education",2,"Marcus Lee"),("Hindi",3,"Rashmi Joshi"),("Art",2,"Anjali Roy")]),
        cls("12CS", [("Computer Science",6,"Vikram Singh"),("English",4,"Daniel Brooks"),("Physical Education",2,"Marcus Lee"),("Hindi",3,"Rashmi Joshi"),("Art",2,"Anjali Roy")]),
    ]

    show_toast("Demo data loaded (teachers + classes)")
    set_demo_loaded()
    from storage import save_teachers, save_classes
    save_teachers(st.session_state.teachers)
    save_classes(st.session_state.classes)


# ---------------------------------------------------------------------------
# Sidebar – configuration & demo controls
# ---------------------------------------------------------------------------


def render_sidebar() -> None:
    cfg = st.session_state.config
    st.sidebar.title("⚙️ School Setup")

    with st.sidebar.form("sidebar_config", clear_on_submit=False):
        st.markdown("**📆 Days & Periods**")
        days_str = st.text_input(
            "Days (comma-separated)",
            value=",".join(cfg.days),
        )
        periods = st.number_input(
            "Periods per day",
            min_value=4,
            max_value=12,
            value=cfg.periods_per_day,
        )
        st.markdown("**🥤 Break Periods**")
        st.caption("One per line: period_number,name (e.g. 4,Lunch)")
        break_str = st.text_area(
            "Break periods",
            value="\n".join(f"{i+1},{name}" for i, name in cfg.break_periods.items()),
            height=80,
        )

        if st.form_submit_button("Apply Config"):
            days = [d.strip() for d in days_str.split(",") if d.strip()]
            breaks: Dict[int, str] = {}
            for line in break_str.splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    try:
                        idx = int(parts[0]) - 1
                        breaks[idx] = parts[1]
                    except ValueError:
                        continue
            st.session_state.config = SchoolConfig(
                days=days or cfg.days,
                periods_per_day=int(periods),
                break_periods=breaks or cfg.break_periods,
            )
            save_config(st.session_state.config)
            show_toast("Config saved")

    st.sidebar.markdown("---")
    with st.sidebar.expander("🧪 Demo / Testing"):
        if st.button("Load Demo Data"):
            load_demo_into_session()

    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear all generated timetables"):
        st.session_state.class_timetable = None
        st.session_state.teacher_timetable = None
        clear_base_timetable()
        clear_scenario_state()
        clear_demo_loaded()
        show_toast("Cleared generated timetables")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def tab_teachers_classes() -> None:
    st.header("Teachers & Classes")

    cfg: SchoolConfig = st.session_state.config

    # --- Teachers ---
    st.subheader("1. Teachers")
    with st.expander("➕ Add teacher", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            t_id = st.text_input("Teacher name / ID", key="new_teacher_id")
        with col2:
            subs = st.text_input(
                "Subjects (comma-separated)", key="new_teacher_subjects"
            )
        free_per_day = st.number_input(
            "Free periods per day",
            min_value=0,
            max_value=cfg.periods_per_day,
            value=max(0, cfg.periods_per_day - 6),
            key="new_teacher_free_per_day",
        )
        max_day = max(cfg.periods_per_day - int(free_per_day), 0)
        st.caption(f"Teacher will teach at most {max_day} periods/day.")
        if st.button("Save Teacher", key="save_teacher_btn"):
            if t_id.strip():
                teacher = Teacher(
                    teacher_id=t_id.strip(),
                    name=t_id.strip(),
                    subjects=[s.strip() for s in subs.split(",") if s.strip()],
                    max_periods_per_day=int(max_day),
                    max_periods_per_week=30,
                    target_free_periods_per_day=int(free_per_day),
                )
                st.session_state.teachers.append(teacher)
                show_toast(f"Teacher {t_id} added")
                append_history("add", f"Teacher {t_id}", f"Added teacher {t_id}")
                save_teachers(st.session_state.teachers)

    if st.session_state.teachers:
        for i, t in enumerate(st.session_state.teachers):
            cols = st.columns([4, 1])
            with cols[0]:
                subjects = ", ".join(t.subjects) if isinstance(t.subjects, list) else str(
                    t.subjects
                )
                st.markdown(
                    f"**{t.teacher_id}** — {subjects or 'No subjects yet'} "
                    f"(max {t.max_periods_per_day}/day)"
                )
            with cols[1]:
                if st.button("Remove", key=f"rm_teacher_{i}"):
                    removed = st.session_state.teachers.pop(i)
                    show_toast(f"Teacher {removed.teacher_id} removed")
                    append_history(
                        "delete",
                        f"Teacher {removed.teacher_id}",
                        f"Removed teacher {removed.teacher_id}",
                    )
                    save_teachers(st.session_state.teachers)
                    st.rerun()
    else:
        st.info("No teachers yet. Add a few above.")

    st.markdown("---")

    # --- Classes ---
    st.subheader("2. Classes")
    with st.expander("➕ Add class", expanded=True):
        cid = st.text_input("Class ID (e.g. 11SCI)", key="new_class_id")
        subj_lines = st.text_area(
            "Subjects (one per line: subject,weekly_periods,teacher_id)",
            key="new_class_subjects",
        )
        if st.button("Save Class", key="save_class_btn"):
            if cid.strip():
                subjects: List[ClassSubject] = []
                for line in subj_lines.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 3:
                        try:
                            subjects.append(
                                ClassSubject(
                                    subject=parts[0],
                                    weekly_periods=int(parts[1]),
                                    teacher_id=parts[2],
                                )
                            )
                        except ValueError:
                            continue
                st.session_state.classes.append(
                    Class(id=cid.strip(), name=cid.strip(), subjects=subjects)
                )
                show_toast(f"Class {cid} added")
                append_history("add", f"Class {cid}", f"Added class {cid}")
                from storage import save_classes
                save_classes(st.session_state.classes)

    if st.session_state.classes:
        for i, c in enumerate(st.session_state.classes):
            subj_str = ", ".join(
                f"{cs.subject}({cs.weekly_periods}w → {cs.teacher_id})"
                for cs in c.subjects
            ) or "No subjects yet"
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"**{c.id}** — {subj_str}")
            with cols[1]:
                if st.button("Remove", key=f"rm_class_{i}"):
                    removed = st.session_state.classes.pop(i)
                    show_toast(f"Class {removed.id} removed")
                    append_history(
                        "delete",
                        f"Class {removed.id}",
                        f"Removed class {removed.id}",
                    )
                    from storage import save_classes
                    save_classes(st.session_state.classes)
                    st.rerun()
    else:
        st.info("No classes yet. Add a few above.")

    # --- Teacher Preferences ---
    st.markdown("---")
    st.subheader("3. Teacher Availability")
    
    from teacher_preferences import load_preferences, save_preferences, TeacherPreference
    
    prefs = load_preferences()
    cfg: SchoolConfig = st.session_state.config
    
    if st.session_state.teachers:
        # Select teacher to configure
        teacher_options = [t.teacher_id for t in st.session_state.teachers]
        selected_teacher = st.selectbox("Select Teacher", options=teacher_options, key="pref_teacher_select")
        
        if selected_teacher:
            current_pref = prefs.get(selected_teacher, TeacherPreference(teacher_id=selected_teacher))
            
            st.markdown(f"**Configure: {selected_teacher}**")
            
            # Day-by-day preference
            for day_idx, day_name in enumerate(cfg.days):
                with st.expander(f"{day_name}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Preferred periods
                        current_preferred = current_pref.preferred_periods.get(day_idx, [])
                        preferred_periods = st.multiselect(
                            f"Preferred periods on {day_name}",
                            options=[f"P{i+1}" for i in range(cfg.periods_per_day)],
                            default=[f"P{p+1}" for p in current_preferred if p < cfg.periods_per_day],
                            key=f"pref_{selected_teacher}_{day_idx}"
                        )
                    
                    with col2:
                        # Unavailable periods
                        current_unavailable = current_pref.unavailable_periods.get(day_idx, [])
                        unavailable_periods = st.multiselect(
                            f"Unavailable periods on {day_name}",
                            options=[f"P{i+1}" for i in range(cfg.periods_per_day)],
                            default=[f"P{p+1}" for p in current_unavailable if p < cfg.periods_per_day],
                            key=f"unavail_{selected_teacher}_{day_idx}"
                        )
                    
                    # Convert to indices and save
                    pref_indices = [int(p.replace("P", "")) - 1 for p in preferred_periods]
                    unavail_indices = [int(p.replace("P", "")) - 1 for p in unavailable_periods]
                    
                    current_pref.preferred_periods[day_idx] = pref_indices
                    current_pref.unavailable_periods[day_idx] = unavail_indices
            
            # Max consecutive periods
            current_pref.max_consecutive_periods = st.number_input(
                "Max consecutive periods",
                min_value=1,
                max_value=8,
                value=current_pref.max_consecutive_periods,
                key=f"max_consec_{selected_teacher}"
            )
            
            # Save button
            if st.button(f"💾 Save Preferences", key=f"save_pref_{selected_teacher}"):
                prefs[selected_teacher] = current_pref
                save_preferences(prefs)
                show_toast(f"Preferences saved for {selected_teacher}")
                
                # Show summary
                total_preferred = sum(len(v) for v in current_pref.preferred_periods.values())
                total_unavailable = sum(len(v) for v in current_pref.unavailable_periods.values())
                st.success(f"✅ Saved: {total_preferred} preferred periods, {total_unavailable} unavailable periods")
    else:
        st.info("Add teachers first to set their availability.")

    # --- Subject Prerequisites ---
    st.markdown("---")
    st.subheader("4. Subject Prerequisites")
    
    from subject_sequencing import (
        load_prerequisites, save_prerequisites, 
        add_prerequisite, remove_prerequisite,
        validate_prerequisites
    )
    
    st.markdown("""
    **📖 How to set prerequisites:**
    - A prerequisite means the dependent subject should be taught *after* the prerequisite
    - Example: Physics → Mathematics means Physics cannot be scheduled before Mathematics
    - This helps maintain proper subject sequence in the weekly timetable
    """)
    
    if st.session_state.classes:
        # Select class
        class_options = [c.id for c in st.session_state.classes]
        selected_class = st.selectbox(
            "Select Class",
            options=class_options,
            key="prereq_class_select"
        )
        
        if selected_class:
            # Get subjects for this class
            cls = next((c for c in st.session_state.classes if c.id == selected_class), None)
            if cls:
                class_subjects = [cs.subject for cs in cls.subjects]
                st.markdown(f"**Subjects in {selected_class}:** {', '.join(class_subjects)}")
                
                # Load current prerequisites
                prereqs = load_prerequisites()
                class_prereqs = prereqs.get(selected_class, {})
                
                # Show current prerequisites
                if class_prereqs:
                    st.markdown("**Current Prerequisites:**")
                    for subj, prereq_list in class_prereqs.items():
                        if prereq_list:
                            for prereq in prereq_list:
                                cols = st.columns([3, 3, 1])
                                with cols[0]:
                                    st.markdown(f"`{prereq}` → `{subj}`")
                                with cols[2]:
                                    if st.button("🗑️", key=f"del_prereq_{selected_class}_{subj}_{prereq}"):
                                        remove_prerequisite(selected_class, subj, prereq)
                                        st.rerun()
                
                # Add new prerequisite
                st.markdown("**➕ Add New Prerequisite:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    dependent_subject = st.selectbox(
                        "Dependent Subject (should come AFTER)",
                        options=class_subjects,
                        key="dependent_subject"
                    )
                
                with col2:
                    # Get subjects that can be prerequisites (exclude dependent subject)
                    prereq_options = [s for s in class_subjects if s != dependent_subject]
                    prerequisite = st.selectbox(
                        "Prerequisite Subject (should come FIRST)",
                        options=prereq_options,
                        key="prerequisite_subject"
                    )
                
                if st.button("➕ Add Prerequisite", key="add_prereq_btn"):
                    add_prerequisite(selected_class, dependent_subject, prerequisite)
                    show_toast(f"Added: {prerequisite} → {dependent_subject}")
                    st.rerun()
                
                # Validate prerequisites
                is_valid, errors = validate_prerequisites(selected_class, class_subjects)
                if not is_valid:
                    st.error("Prerequisite Errors:")
                    for err in errors:
                        st.markdown(f"⚠️ {err}")
                
                # Help text
                with st.expander("❓ How Prerequisites Work"):
                    st.markdown("""
                    **Example:**
                    - If you set: `Mathematics → Physics` 
                    - Then Physics cannot be scheduled before Mathematics in the same week
                    
                    **Tips:**
                    - Start with foundational subjects as prerequisites
                    - Sciences typically need Mathematics prerequisite
                    - Keep chains short (2-3 subjects max) for best results
                    """)
    else:
        st.info("Add classes first to set subject prerequisites.")

    # --- Shared Teacher Analysis ---
    st.markdown("---")
    st.subheader("5. Shared Teacher Analysis")
    
    from shared_teacher_analysis import (
        analyze_shared_teachers, get_shared_teachers, 
        get_overloaded_teachers, generate_sharing_recommendations
    )
    
    if st.session_state.teachers and st.session_state.classes:
        cfg: SchoolConfig = st.session_state.config
        
        # Analyze all teachers
        all_teachers = analyze_shared_teachers(
            st.session_state.teachers, 
            st.session_state.classes,
            cfg
        )
        
        # Get stats
        shared = get_shared_teachers(st.session_state.teachers, st.session_state.classes, cfg)
        overloaded = get_overloaded_teachers(st.session_state.teachers, st.session_state.classes, cfg)
        
        # Show metrics
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Teachers", len(all_teachers))
        with cols[1]:
            st.metric("Shared Teachers", len(shared))
        with cols[2]:
            st.metric("Overloaded", len(overloaded))
        with cols[3]:
            st.metric("Healthy", len(all_teachers) - len(overloaded))
        
        # Show recommendations
        if overloaded:
            st.markdown("### ⚠️ Overloaded Teachers")
            for rec in generate_sharing_recommendations(st.session_state.teachers, st.session_state.classes, cfg):
                st.markdown(rec)
        
        # Show detailed table
        st.markdown("### 📊 Teacher Workload Details")
        
        # Create dataframe
        import pandas as pd
        rows = []
        for tid, info in all_teachers.items():
            rows.append({
                "Teacher": tid,
                "Subjects": ", ".join(info.subjects),
                "Classes": ", ".join(info.classes_assigned),
                "Periods/Week": info.total_periods_per_week,
                "Max Possible": info.max_possible_periods,
                "Utilization": f"{info.utilization_percentage}%",
                "Status": "⚠️ Overloaded" if info.is_overloaded else "✅ OK"
            })
        
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, width='stretch', hide_index=True)
        
        # Help
        with st.expander("❓ About Shared Teachers"):
            st.markdown("""
            **Shared Teachers** are those teaching multiple classes.
            
            **Why it matters:**
            - Teachers with high utilization may need backup
            - Overloaded teachers cannot complete all assignments
            - Consider splitting subjects between teachers
            
            **Solutions:**
            1. Add another teacher for the subject
            2. Temporarily increase max periods/day
            3. Reduce weekly periods for some classes
            """)
    else:
        st.info("Add teachers and classes first to see analysis.")

    # --- Load Balancing ---
    st.markdown("---")
    st.subheader("6. Load Balancing")
    
    from load_balancer import (
        analyze_subject_distribution, get_load_balance_stats,
        calculate_ideal_distribution, get_teacher_daily_load
    )
    
    if st.session_state.classes and st.session_state.class_timetable:
        cfg: SchoolConfig = st.session_state.config
        
        # Get load balance stats
        stats = get_load_balance_stats(
            st.session_state.classes,
            cfg,
            st.session_state.class_timetable
        )
        
        # Show metrics
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Subjects", stats.total_classes * 5)  # Approx
        with cols[1]:
            st.metric("✅ Balanced", stats.balanced_subjects)
        with cols[2]:
            st.metric("⚠️ Unbalanced", stats.unbalanced_subjects)
        with cols[3]:
            st.metric("Max Variance", f"{stats.max_daily_variance}")
        
        # Show recommendations
        if stats.recommendations:
            st.markdown("### 💡 Recommendations")
            for rec in stats.recommendations[:5]:
                st.markdown(rec)
        
        # Show teacher daily load
        st.markdown("### 📊 Teacher Daily Load")
        teacher_load = get_teacher_daily_load(st.session_state.class_timetable, cfg)
        
        import pandas as pd
        rows = []
        for tid, daily in sorted(teacher_load.items()):
            rows.append({
                "Teacher": tid,
                "Mon": daily[0] if len(daily) > 0 else 0,
                "Tue": daily[1] if len(daily) > 1 else 0,
                "Wed": daily[2] if len(daily) > 2 else 0,
                "Thu": daily[3] if len(daily) > 3 else 0,
                "Fri": daily[4] if len(daily) > 4 else 0,
                "Total": sum(daily)
            })
        
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, width='stretch', hide_index=True)
        
        with st.expander("❓ About Load Balancing"):
            st.markdown("""
            **Load Balancing** ensures:
            - Subject periods are evenly spread across days
            - Teachers have consistent daily workload
            - No day is overloaded with too many periods
            
            **Variance**: Difference between most and least busy teaching day
            - Variance of 0-1 = ✅ Well balanced
            - Variance of 2 = ⚠️ Noticeable imbalance
            - Variance of 3+ = 🔴 Needs attention
            """)
    elif st.session_state.classes:
        st.info("Generate a timetable first to see load balancing analysis.")
    else:
        st.info("Add classes first to see load balancing.")

    # --- Elective / Optional Classes ---
    st.markdown("---")
    st.subheader("7. Elective / Optional Classes")
    
    from elective_manager import (
        load_elective_groups, save_elective_groups,
        load_student_electives, save_student_electives,
        add_elective_group, format_electives_for_display
    )
    
    st.markdown("""
    **📖 How Electives Work:**
    - Electives are optional subjects that students can choose
    - Groups allow students to pick from a set of subjects
    - Solver assigns electives after core subjects to avoid conflicts
    """)
    
    # Load current groups
    groups = load_elective_groups()
    
    # Show current elective groups
    if groups:
        st.markdown("### Current Elective Groups")
        for name, group in groups.items():
            cols = st.columns([3, 2, 1])
            with cols[0]:
                st.markdown(f"**{name}**")
            with cols[1]:
                st.caption(f"{', '.join(group.subjects)}")
            with cols[2]:
                if st.button("🗑️", key=f"del_group_{name}"):
                    from elective_manager import remove_elective_group
                    remove_elective_group(name)
                    st.rerun()
    
    # Add new elective group
    st.markdown("### ➕ Add Elective Group")
    
    col1, col2 = st.columns(2)
    with col1:
        group_name = st.text_input("Group Name", placeholder="e.g., Science Electives")
        subjects = st.text_area("Subjects (comma-separated)", placeholder="e.g., Biotechnology, Computer Science, Psychology")
    
    with col2:
        min_select = st.number_input("Min to Select", min_value=1, max_value=5, value=1)
        max_select = st.number_input("Max to Select", min_value=1, max_value=5, value=1)
    
    if st.button("➕ Add Group"):
        if group_name and subjects:
            subject_list = [s.strip() for s in subjects.split(",") if s.strip()]
            add_elective_group(group_name, subject_list, min_select, max_select)
            show_toast(f"Added elective group: {group_name}")
            st.rerun()
    
    # Help
    with st.expander("❓ How Electives Work"):
        st.markdown("""
        **Example Elective Setup:**
        - Group: "Science Electives"
          - Subjects: Biotechnology, Computer Science, Psychology
          - Students pick 1-2
        
        **Workflow:**
        1. Add elective groups here
        2. In class subjects, mark subjects as "optional"
        3. Solver will assign elective subjects after core
        
        **Note:** Full elective scheduling requires additional integration.
        This section lets you define elective groups for future use.
        """)


def tab_history() -> None:
    st.header("🕓 History")
    history = load_history()
    if not history:
        st.info("No history yet.")
        return
    for entry in history:
        ts = entry.get("ts", "")
        summary = entry.get("summary", "")
        action = entry.get("action", "")
        target = entry.get("target", "")
        with st.expander(f"{ts} — {summary}"):
            st.markdown(f"**Action:** {action}  •  **Target:** {target}")
            details = entry.get("details", "")
            if details:
                st.caption(details)


def tab_class_timetables() -> None:
    st.header("Class Timetables")
    cfg: SchoolConfig = st.session_state.config

    if st.button("🚀 Generate Timetable", type="primary"):
        if not st.session_state.teachers:
            st.error("Add at least one teacher first.")
            return
        if not st.session_state.classes:
            st.error("Add at least one class first.")
            return
        
        with st.spinner("Managing constraints and solving..."):
            # First, resolve any constraint violations
            teachers, classes, constraint_msg = manage_constraints(
                st.session_state.teachers, 
                st.session_state.classes, 
                cfg
            )
            
            # Show constraint messages
            if constraint_msg and "successfully" not in constraint_msg.lower():
                st.warning(constraint_msg)
            
            # Generate timetable with adjusted data
            tt = solve_timetable(cfg, teachers, classes)
        
        if tt is None:
            st.error("No solution found. Try changing config or weekly periods.")
            append_history("generate", "Timetable", "No solution found")
            return

        st.session_state.class_timetable = tt
        st.session_state.teacher_timetable = invert_to_teacher_timetable(tt, cfg)
        save_base_timetable(tt)
        append_history("generate", "Timetable", "Generated clash‑free timetable")
        show_toast("Timetable generated!")

    if not st.session_state.class_timetable:
        st.info("Generate a timetable to see class views.")
        return

    # Keys should be (class_id, day, period) tuples, but be defensive.
    keys = list(st.session_state.class_timetable.keys())
    class_ids = sorted(
        {k[0] for k in keys if isinstance(k, (tuple, list)) and len(k) >= 1}
    )
    breaks = cfg.break_periods
    period_cols = [
        f"P{p+1}" + (f" ({breaks[p]})" if p in breaks else "")
        for p in range(cfg.periods_per_day)
    ]

    col_config = {"Day": st.column_config.TextColumn("Day", width="medium")}
    for pc in period_cols:
        col_config[pc] = st.column_config.TextColumn(pc, width="large")

    for cid in class_ids:
        st.subheader(f"Class {cid}")
        rows = []
        for d, day_name in enumerate(cfg.days):
            row = [day_name]
            for p in range(cfg.periods_per_day):
                if p in breaks:
                    row.append(breaks[p])
                else:
                    val = st.session_state.class_timetable.get((cid, d, p), ("", ""))[0]
                    cell = val or "Free period"
                    row.append(_shorten(cell, 18))
            rows.append(row)
        st.dataframe(
            pd.DataFrame(rows, columns=["Day"] + period_cols),
            column_config=col_config,
            width="stretch",
            hide_index=True,
        )


def tab_teacher_timetables() -> None:
    st.header("Teacher Timetables")
    if not st.session_state.teacher_timetable:
        st.info("Generate a timetable first.")
        return

    cfg: SchoolConfig = st.session_state.config
    breaks = cfg.break_periods
    period_cols = [
        f"P{p+1}" + (f" ({breaks[p]})" if p in breaks else "")
        for p in range(cfg.periods_per_day)
    ]
    col_config = {"Day": st.column_config.TextColumn("Day", width="medium")}
    for pc in period_cols:
        col_config[pc] = st.column_config.TextColumn(pc, width="large")

    for tid, tt in sorted(st.session_state.teacher_timetable.items()):
        st.subheader(f"Teacher {tid}")
        rows = []
        for d, day_name in enumerate(cfg.days):
            row = [day_name]
            for p in range(cfg.periods_per_day):
                if p in breaks:
                    row.append(breaks[p])
                else:
                    cid, subj = tt.get((d, p), ("", ""))
                    cell = f"{cid}: {subj}" if subj else "Free period"
                    row.append(_shorten(cell, 22))
            rows.append(row)
        st.dataframe(
            pd.DataFrame(rows, columns=["Day"] + period_cols),
            column_config=col_config,
            width="stretch",
            hide_index=True,
        )


def tab_connections() -> None:
    st.header("🔗 Teacher-Class Connections")
    
    if not st.session_state.teachers or not st.session_state.classes:
        st.info("Add teachers and classes first to see connections.")
        return
    
    from teacher_class_connections import prepare_connections, get_legend, SUBJECT_COLORS, STREAM_PALETTE
    
    # Prepare connection data
    conn_data = prepare_connections(st.session_state.teachers, st.session_state.classes)
    
    # Show stats
    cols = st.columns(3)
    with cols[0]:
        st.metric("👨‍🏫 Teachers", conn_data["stats"]["total_teachers"])
    with cols[1]:
        st.metric("📚 Classes", conn_data["stats"]["total_classes"])
    with cols[2]:
        st.metric("🔗 Connections", conn_data["stats"]["total_connections"])
    
    # Legend
    st.markdown("**Legend:**")
    legend_cols = st.columns(4)
    
    # Subject colors (teachers)
    for i, (group, color) in enumerate(SUBJECT_COLORS.items()):
        with legend_cols[i % 4]:
            st.markdown(f'<span style="color:{color}">●</span> {group}', unsafe_allow_html=True)
    
    # Create network graph using visd
    import plotly.graph_objects as go
    
    # Prepare node positions (circular layout)
    nodes = conn_data["nodes"]
    edges = conn_data["edges"]
    
    teacher_nodes = [n for n in nodes if n["type"] == "teacher"]
    class_nodes = [n for n in nodes if n["type"] == "class"]
    
    # Calculate positions
    n_teachers = len(teacher_nodes)
    n_classes = len(class_nodes)
    
    # Teacher positions (inner circle)
    teacher_x = []
    teacher_y = []
    for i, n in enumerate(teacher_nodes):
        angle = 2 * 3.14159 * i / max(n_teachers, 1)
        teacher_x.append(0.5 * 10 * (1 + 0.5) * (1 if i % 2 == 0 else 0.8) * (1 if i % 3 == 0 else 0.9) * (1 if i % 4 == 0 else 0.85) * (1 if i % 5 == 0 else 0.95) * 0.6 if False else 3 * (0.5 + 0.5 * (i / max(n_teachers - 1, 1))))
        teacher_x.append(3 * (0.5 + 0.5 * (i / max(n_teachers - 1, 1))) * (1 if i % 2 == 0 else -1) if n_teachers > 1 else 0)
        teacher_y.append(3 * (0.5 + 0.5 * (i / max(n_teachers - 1, 1))) * (1 if i % 3 == 0 else -1) if n_teachers > 1 else 0)
    
    # Simpler: use force-directed-like positions
    teacher_x = []
    teacher_y = []
    for i, n in enumerate(teacher_nodes):
        angle = 2 * 3.14159 * i / max(n_teachers, 1)
        teacher_x.append(4 * (0.5 + 0.5 * (i / max(n_teachers - 1, 1))) * (1 if i % 2 == 0 else -1) if n_teachers > 1 else 0)
        teacher_y.append(4 * (0.5 + 0.5 * (i / max(n_teachers - 1, 1))) * (1 if i % 3 == 0 else -1) if n_teachers > 1 else 0)
    
    class_x = []
    class_y = []
    for i, n in enumerate(class_nodes):
        angle = 2 * 3.14159 * i / max(n_classes, 1)
        class_x.append(8 + 3 * (0.5 + 0.5 * (i / max(n_classes - 1, 1))) * (1 if i % 2 == 0 else -1) if n_classes > 1 else 8)
        class_y.append(4 * (0.5 + 0.5 * (i / max(n_classes - 1, 1))) * (1 if i % 3 == 0 else -1) if n_classes > 1 else 0)
    
    # Create node trace
    node_x = teacher_x + class_x
    node_y = teacher_y + class_y
    node_colors = [n["color"] for n in teacher_nodes + class_nodes]
    node_labels = [n["label"] for n in teacher_nodes + class_nodes]
    node_types = [n["type"] for n in teacher_nodes + class_nodes]
    node_titles = [n["title"] for n in teacher_nodes + class_nodes]
    
    # Node sizes
    node_sizes = [25 if t == "teacher" else 35 for t in node_types]
    
    # Create edges
    edge_x = []
    edge_y = []
    edge_colors = []
    edge_widths = []
    
    for edge in edges:
        # Find source and target positions
        src_id = edge["from"]
        tgt_id = edge["to"]
        
        src_idx = next((i for i, n in enumerate(nodes) if n["id"] == src_id), None)
        tgt_idx = next((i for i, n in enumerate(nodes) if n["id"] == tgt_id), None)
        
        if src_idx is not None and tgt_idx is not None:
            edge_x.extend([node_x[src_idx], node_x[tgt_idx], None])
            edge_y.extend([node_y[src_idx], node_y[tgt_idx], None])
            edge_colors.append("#888")
            edge_widths.append(edge["width"])
    
    # Create figure
    fig = go.Figure()
    
    # Add edges
    for i, edge in enumerate(edges):
        src_id = edge["from"]
        tgt_id = edge["to"]
        
        src_idx = next((j for j, n in enumerate(nodes) if n["id"] == src_id), None)
        tgt_idx = next((j for j, n in enumerate(nodes) if n["id"] == tgt_id), None)
        
        if src_idx is not None and tgt_idx is not None:
            fig.add_trace(go.Scatter(
                x=[node_x[src_idx], node_x[tgt_idx]],
                y=[node_y[src_idx], node_y[tgt_idx]],
                mode='lines',
                line=dict(width=edge["width"], color='#666666'),
                hoverinfo='text',
                text=edge["title"],
                showlegend=False
            ))
    
    # Add nodes
    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='#333333')
        ),
        text=node_labels,
        textposition="top center",
        textfont=dict(size=10, color='#f0f0f0'),
        hoverinfo='text',
        hovertext=node_titles,
        showlegend=False
    ))
    
    # Update layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2, 15]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-6, 6]),
        hovermode='closest',
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
        title=dict(
            text="<b>Teacher-Class Connection Network</b>",
            font=dict(size=20, color='#f0f0f0'),
            x=0.5
        ),
        annotations=[
            dict(x=3, y=5.5, text="<b>Teachers</b>", showarrow=False, font=dict(size=14, color='#aaa')),
            dict(x=10, y=5.5, text="<b>Classes</b>", showarrow=False, font=dict(size=14, color='#aaa'))
        ]
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # Connection details
    st.markdown("### 📊 Connection Details")
    
    # Create a dataframe for display
    import pandas as pd
    conn_df = pd.DataFrame([
        {
            "Teacher": edge["from"].replace("teacher_", ""),
            "Class": edge["to"].replace("class_", ""),
            "Subject": edge["subject"],
            "Periods/Week": edge["periods"]
        }
        for edge in edges
    ])
    
    if not conn_df.empty:
        conn_df = conn_df.sort_values(["Teacher", "Class"])
        st.dataframe(conn_df, width='stretch', hide_index=True)


def tab_heatmaps() -> None:
    st.header("🔥 Heatmaps")
    if not st.session_state.class_timetable:
        st.info("Generate a timetable first.")
        return

    cfg: SchoolConfig = st.session_state.config
    tt: Timetable = st.session_state.class_timetable
    teachers = [t.teacher_id for t in st.session_state.teachers]
    days = cfg.days

    # Build teacher × day load matrix
    load = np.zeros((len(teachers), len(days)), dtype=int)
    for key, (_, tid) in tt.items():
        if not isinstance(key, (tuple, list)) or len(key) != 3:
            continue
        _, d, p = key
        if p in cfg.break_periods:
            continue
        if tid in teachers:
            i = teachers.index(tid)
            load[i, d] += 1

    if not teachers:
        st.info("Add some teachers first.")
        return

    # Build a "wave-dot" style heatmap: grid of circles whose size and brightness
    # represent load. This feels more cinematic than plain blocks.
    xs: List[str] = []
    ys: List[str] = []
    sizes: List[float] = []
    colors: List[int] = []
    for i, tid in enumerate(teachers):
        for j, day in enumerate(days):
            xs.append(day)
            ys.append(tid)
            val = int(load[i, j])
            colors.append(val)
            # Base dot size + extra per period
            sizes.append(10 + 10 * val)

    fig = px.scatter(
        x=xs,
        y=ys,
        color=colors,
        size=sizes,
        color_continuous_scale="Viridis",
        labels=dict(x="Day", y="Teacher", color="Load"),
    )
    fig.update_traces(
        mode="markers",
        marker=dict(
            opacity=0.85,
            line=dict(width=0),
        ),
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#f0f6fc"),
        margin=dict(l=40, r=20, t=40, b=40),
        yaxis=dict(categoryorder="array", categoryarray=teachers),
    )
    st.plotly_chart(fig, width='stretch')
    st.caption("Bigger, brighter dots = more periods for that teacher on that day.")


def tab_pdf_export() -> None:
    st.header("📄 Export PDFs")
    if not (st.session_state.class_timetable and st.session_state.teacher_timetable):
        st.info("Generate a timetable first.")
        return

    cfg: SchoolConfig = st.session_state.config
    class_tt = flat_to_class_timetables(st.session_state.class_timetable)
    class_pdf = export_class_timetables_pdf(class_tt, cfg)
    teacher_pdf = export_teacher_timetables_pdf(
        st.session_state.teacher_timetable, cfg
    )
    st.subheader("All timetables")
    col1, col2 = st.columns(2)
    with col1:
        if st.download_button(
            "📥 Download ALL Class Timetables (PDF)",
            data=class_pdf,
            file_name="class_timetables.pdf",
            mime="application/pdf",
            key="dl_all_classes_pdf",
        ):
            append_history("export", "PDF", "Exported all class timetables PDF")
            show_toast("All class PDFs downloaded")
    with col2:
        if st.download_button(
            "📥 Download ALL Teacher Timetables (PDF)",
            data=teacher_pdf,
            file_name="teacher_timetables.pdf",
            mime="application/pdf",
            key="dl_all_teachers_pdf",
        ):
            append_history("export", "PDF", "Exported all teacher timetables PDF")
            show_toast("All teacher PDFs downloaded")

    st.markdown("---")
    st.subheader("Single class / teacher")

    class_ids = sorted(class_tt.keys())
    teacher_ids = sorted(st.session_state.teacher_timetable.keys())

    colc, colt = st.columns(2)
    with colc:
        sel_class = st.selectbox(
            "Class", ["— select class —"] + class_ids, key="pdf_single_class"
        )
        if sel_class != "— select class —":
            single_class_pdf = export_class_timetables_pdf(
                {sel_class: class_tt[sel_class]}, cfg
            )
            st.download_button(
                f"📥 Download {sel_class} Timetable (PDF)",
                data=single_class_pdf,
                file_name=f"{sel_class}_timetable.pdf",
                mime="application/pdf",
                key="dl_one_class_pdf",
            )

    with colt:
        sel_teacher = st.selectbox(
            "Teacher", ["— select teacher —"] + teacher_ids, key="pdf_single_teacher"
        )
        if sel_teacher != "— select teacher —":
            single_teacher_pdf = export_teacher_timetables_pdf(
                {sel_teacher: st.session_state.teacher_timetable[sel_teacher]}, cfg
            )
            st.download_button(
                f"📥 Download {sel_teacher} Timetable (PDF)",
                data=single_teacher_pdf,
                file_name=f"{sel_teacher}_timetable.pdf",
                mime="application/pdf",
                key="dl_one_teacher_pdf",
            )


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    _init_session()
    render_sidebar()

    st.title("📅 Smart Timetable Builder")
    st.markdown("*Smooth, stable, alive.*")

    _notification_ticker()
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "👥 Teachers & Classes",
            "📋 Class Timetables",
            "👨🏫 Teacher Timetables",
            "🔗 Connections",
            "🔥 Heatmaps",
            "📄 PDF Export",
            "🕓 History",
            "🎯 Electives",
        ]
    )

    with tab1:
        tab_teachers_classes()
    with tab2:
        tab_class_timetables()
    with tab3:
        tab_teacher_timetables()
    with tab4:
        tab_connections()
    with tab5:
        tab_heatmaps()
    with tab6:
        tab_pdf_export()
    with tab7:
        tab_history()
    with tab8:
        st.header("🎯 Electives")
        st.info("Elective management is in the Teachers & Classes tab.")
if __name__ == "__main__":
    main()

