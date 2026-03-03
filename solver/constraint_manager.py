"""
constraint_manager.py — Backend Constraint Management for Timetabling

Handles teacher scheduling constraints automatically:
- Detects conflicts (teacher overloaded)
- Applies best resolution strategy
- Notifies user about adjustments
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from models import Teacher, Class, ClassSubject, SchoolConfig


@dataclass
class ConstraintViolation:
    """Represents a constraint violation that was detected."""
    teacher_id: str
    subject: str
    conflict_type: str  # "overload", "conflict", "unavailable"
    details: str
    resolution_applied: str
    recommendation: str = ""


@dataclass
class ConstraintResolution:
    """Result of applying a constraint resolution."""
    success: bool
    violations_resolved: List[ConstraintViolation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    adjustments_made: Dict[str, Any] = field(default_factory=dict)


class ConstraintManager:
    """
    Manages teacher scheduling constraints and automatically resolves conflicts.
    """
    
    def __init__(self, config: SchoolConfig):
        self.config = config
        self.num_days = len(config.days)
        self.notifications: List[Dict] = []
    
    def calculate_teacher_demand(self, teachers: List[Teacher], classes: List[Class]) -> Dict[str, Dict]:
        """
        Calculate total weekly periods required for each teacher.
        
        Returns: {teacher_id: {
            "total_required": int,
            "max_possible": int,
            "classes_assigned": List[str],
            "subjects": Dict[subject_name -> periods_per_week],
            "is_overloaded": bool,
            "overload_amount": int
        }}
        """
        demand = {}
        
        for teacher in teachers:
            teacher_id = teacher.teacher_id
            max_per_day = teacher.max_periods_per_day
            max_possible = max_per_day * self.num_days
            
            # Find all classes where this teacher is assigned
            classes_assigned = []
            subjects = {}
            
            for cls in classes:
                for cs in cls.subjects:
                    if cs.teacher_id == teacher_id:
                        classes_assigned.append(cls.id)
                        subjects[cs.subject] = cs.weekly_periods
            
            total_required = sum(subjects.values())
            is_overloaded = total_required > max_possible
            overload_amount = max(0, total_required - max_possible)
            
            demand[teacher_id] = {
                "total_required": total_required,
                "max_possible": max_possible,
                "classes_assigned": classes_assigned,
                "subjects": subjects,
                "is_overloaded": is_overloaded,
                "overload_amount": overload_amount,
                "max_per_day": max_per_day
            }
        
        return demand
    
    def detect_conflicts(self, demand: Dict) -> List[Tuple[str, Dict]]:
        """Detect all teachers with conflicts."""
        conflicts = []
        for teacher_id, info in demand.items():
            if info["is_overloaded"]:
                conflicts.append((teacher_id, info))
        return conflicts
    
    def evaluate_resolution_options(self, teacher_id: str, demand_info: Dict, 
                                   all_teachers: List[Teacher], classes: List[Class]) -> List[Dict]:
        """
        Evaluate possible resolution options for an overloaded teacher.
        
        Returns list of options with scores.
        """
        options = []
        
        total_required = demand_info["total_required"]
        max_per_day = demand_info["max_per_day"]
        subjects = demand_info["subjects"]
        
        # Option A: Temporarily increase max/day
        new_max_day = (total_required + self.num_days - 1) // self.num_days  # ceil
        if new_max_day <= 10:  # Reasonable upper limit
            options.append({
                "type": "increase_max_day",
                "description": f"Temporarily increase max periods/day from {max_per_day} to {new_max_day}",
                "new_max_day": new_max_day,
                "disruption": "low",
                "reversible": True
            })
        
        # Option B: Suggest reducing weekly periods
        overload = demand_info["overload_amount"]
        reduction_needed = overload // self.num_days
        if reduction_needed > 0:
            # Find subjects that can be reduced
            reducible = []
            for subj, periods in subjects.items():
                if periods > 3:  # Minimum reasonable periods
                    reducible.append((subj, periods))
            
            if reducible:
                options.append({
                    "type": "reduce_weekly",
                    "description": f"Reduce weekly periods of {len(reducible)} subject(s) by {reduction_needed}",
                    "reductions": {subj: min(reduction_needed, per - 3) for subj, per in reducible},
                    "disruption": "medium",
                    "reversible": True
                })
        
        # Option C: Check for available backup teachers
        for subj, periods in subjects.items():
            backup = self._find_backup_teacher(subj, teacher_id, all_teachers, classes)
            if backup:
                options.append({
                    "type": "split_teacher",
                    "description": f"Split {subj} with another teacher ({backup})",
                    "subject": subj,
                    "backup_teacher": backup,
                    "disruption": "medium",
                    "reversible": True
                })
        
        return options
    
    def _find_backup_teacher(self, subject: str, exclude_teacher_id: str,
                             teachers: List[Teacher], classes: List[Class]) -> Optional[str]:
        """Find an available teacher who can teach this subject."""
        # Get all teachers who can teach this subject
        capable_teachers = [
            t.teacher_id for t in teachers 
            if t.teacher_id != exclude_teacher_id and subject in t.subjects
        ]
        
        if not capable_teachers:
            return None
        
        # Find the one with least current load
        demand = self.calculate_teacher_demand(teachers, classes)
        
        best_teacher = None
        best_load = float('inf')
        
        for tid in capable_teachers:
            if tid in demand:
                load = demand[tid]["total_required"]
                if load < best_load:
                    best_load = load
                    best_teacher = tid
        
        return best_teacher
    
    def select_best_option(self, options: List[Dict]) -> Optional[Dict]:
        """Select the best resolution option based on minimal disruption."""
        if not options:
            return None
        
        # Sort by disruption level
        disruption_order = {"low": 0, "medium": 1, "high": 2}
        
        sorted_options = sorted(options, key=lambda x: disruption_order.get(x.get("disruption", "high"), 2))
        return sorted_options[0]
    
    def apply_resolution(self, option: Dict, teacher_id: str, 
                        teachers: List[Teacher], classes: List[Class]) -> Tuple[List[Teacher], List[Class]]:
        """
        Apply a resolution option and return updated teachers/classes.
        """
        teachers = list(teachers)  # Copy
        classes = list(classes)  # Copy
        
        option_type = option.get("type")
        
        if option_type == "increase_max_day":
            new_max = option.get("new_max_day", 6)
            for t in teachers:
                if t.teacher_id == teacher_id:
                    t.max_periods_per_day = new_max
                    self.notifications.append({
                        "type": "adjustment",
                        "teacher": teacher_id,
                        "change": f"max periods/day increased to {new_max}",
                        "reversible": True
                    })
        
        elif option_type == "reduce_weekly":
            reductions = option.get("reductions", {})
            for cls in classes:
                for cs in cls.subjects:
                    if cs.teacher_id == teacher_id and cs.subject in reductions:
                        cs.weekly_periods -= reductions[cs.subject]
                        self.notifications.append({
                            "type": "adjustment",
                            "teacher": teacher_id,
                            "subject": cs.subject,
                            "change": f"weekly periods reduced by {reductions[cs.subject]}",
                            "reversible": True
                        })
        
        elif option_type == "split_teacher":
            subject = option.get("subject")
            backup = option.get("backup_teacher")
            # This would require more complex logic to actually split
            # For now, just notify
            self.notifications.append({
                "type": "suggestion",
                "teacher": teacher_id,
                "subject": subject,
                "suggestion": f"Consider adding {backup} to share {subject}",
                "action_required": True
            })
        
        return teachers, classes
    
    def resolve_constraints(self, teachers: List[Teacher], classes: List[Class]) -> ConstraintResolution:
        """
        Main method: detect and resolve all constraint violations.
        """
        violations_resolved = []
        warnings = []
        adjustments = {}
        
        # Step 1: Calculate demand
        demand = self.calculate_teacher_demand(teachers, classes)
        
        # Step 2: Detect conflicts
        conflicts = self.detect_conflicts(demand)
        
        if not conflicts:
            return ConstraintResolution(success=True)
        
        # Step 3: Resolve each conflict
        for teacher_id, info in conflicts:
            overload = info["overload_amount"]
            total = info["total_required"]
            max_day = info["max_per_day"]
            
            # Generate warning
            warning = (
                f"Teacher {teacher_id} is overloaded: "
                f"{total} periods needed across {self.num_days} days, "
                f"but max is {max_day}/day ({max_day * self.num_days} max possible)."
            )
            warnings.append(warning)
            
            # Evaluate options
            options = self.evaluate_resolution_options(teacher_id, info, teachers, classes)
            
            if not options:
                warnings.append(f"Could not find resolution for {teacher_id}")
                continue
            
            # Select best option
            best_option = self.select_best_option(options)
            
            if best_option:
                # Apply resolution
                teachers, classes = self.apply_resolution(best_option, teacher_id, teachers, classes)
                
                violation = ConstraintViolation(
                    teacher_id=teacher_id,
                    subject=",".join(info["subjects"].keys()),
                    conflict_type="overload",
                    details=f"Required {total} periods, max {max_day * self.num_days}",
                    resolution_applied=best_option["description"],
                    recommendation=f"Consider permanently increasing max/day or adding backup teacher"
                )
                violations_resolved.append(violation)
                adjustments[teacher_id] = best_option
        
        return ConstraintResolution(
            success=len(violations_resolved) > 0,
            violations_resolved=violations_resolved,
            warnings=warnings,
            adjustments_made=adjustments
        )
    
    def get_notifications(self) -> List[Dict]:
        """Get all notifications generated during constraint resolution."""
        return self.notifications
    
    def generate_user_message(self, resolution: ConstraintResolution) -> str:
        """Generate a user-friendly message about adjustments made."""
        if not resolution.success:
            return "No constraint issues detected."
        
        messages = []
        
        for v in resolution.violations_resolved:
            msg = f"⚠️ **{v.teacher_id}** was overloaded ({v.details}). "
            msg += f"Solution applied: {v.resolution_applied}."
            if v.recommendation:
                msg += f" {v.recommendation}"
            messages.append(msg)
        
        return "\n\n".join(messages) if messages else "Timetable generated successfully!"


def manage_constraints(teachers: List[Teacher], classes: List[Class], 
                       config: SchoolConfig) -> Tuple[List[Teacher], List[Class], str]:
    """
    Convenience function to manage constraints and return adjusted data.
    
    Returns: (adjusted_teachers, adjusted_classes, user_message)
    """
    manager = ConstraintManager(config)
    resolution = manager.resolve_constraints(teachers, classes)
    message = manager.generate_user_message(resolution)
    
    return teachers, classes, message
