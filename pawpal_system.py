"""
PawPal+ — Logic Layer
All backend classes live here. The Streamlit UI (app.py) imports from this module.

Class hierarchy:
  Owner  ──owns──>  Pet  ──has──>  Task
  Scheduler  ──uses──>  Owner, Pet, Task

New in Phase 4:
  - Task.frequency / next_due — recurring task support
  - Task.start_time           — wall-clock slot assigned by Scheduler
  - sort_tasks_by_time()      — module-level sort helper (HH:MM strings)
  - filter_tasks()            — module-level filter helper
  - Scheduler.detect_conflicts() — overlap detection with warning strings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal


# ---------------------------------------------------------------------------
# Type aliases & constants
# ---------------------------------------------------------------------------

PriorityLevel = Literal["low", "medium", "high"]
TaskCategory  = Literal["walk", "feed", "meds", "grooming", "enrichment", "other"]
Frequency     = Literal["none", "daily", "weekly"]

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}
_FREQ_DAYS:     dict[str, int] = {"daily": 1, "weekly": 7}


# ---------------------------------------------------------------------------
# Internal time helpers
# ---------------------------------------------------------------------------


def _time_to_minutes(hhmm: str) -> int:
    """Convert 'HH:MM' string to total minutes since midnight."""
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_time(total_minutes: int) -> str:
    """Convert total minutes since midnight to 'HH:MM' string."""
    total_minutes = max(0, total_minutes)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Module-level algorithms (sorting & filtering)
# ---------------------------------------------------------------------------


def sort_tasks_by_time(tasks: list[Task]) -> list[Task]:
    """Return a new list of tasks sorted by their assigned start_time (HH:MM).

    Tasks without a start_time are placed at the end.  Because HH:MM strings
    sort correctly in lexicographic order (zero-padded hours and minutes),
    a simple string comparison is sufficient — no datetime parsing needed.

    Example:
        sort_tasks_by_time([task_at_10, task_at_08, unscheduled])
        → [task_at_08, task_at_10, unscheduled]
    """
    return sorted(
        tasks,
        key=lambda t: t.start_time if t.start_time is not None else "99:99",
    )


def filter_tasks(
    tasks: list[Task],
    *,
    status: Literal["all", "pending", "completed"] = "all",
    category: str | None = None,
    priority: str | None = None,
    min_duration: int | None = None,
    max_duration: int | None = None,
    frequency: str | None = None,
) -> list[Task]:
    """Return a filtered subset of *tasks* based on the given criteria.

    All keyword arguments are optional and are ANDed together.

    Parameters
    ----------
    tasks:        The source list to filter.
    status:       'all' (default), 'pending', or 'completed'.
    category:     Keep only tasks whose category matches this string.
    priority:     Keep only tasks with this priority level.
    min_duration: Keep only tasks at least this many minutes long.
    max_duration: Keep only tasks at most this many minutes long.
    frequency:    Keep only tasks with this recurrence frequency.
    """
    result = list(tasks)

    if status == "pending":
        result = [t for t in result if not t.is_completed]
    elif status == "completed":
        result = [t for t in result if t.is_completed]

    if category is not None:
        result = [t for t in result if t.category == category]

    if priority is not None:
        result = [t for t in result if t.priority == priority]

    if min_duration is not None:
        result = [t for t in result if t.duration_minutes >= min_duration]

    if max_duration is not None:
        result = [t for t in result if t.duration_minutes <= max_duration]

    if frequency is not None:
        result = [t for t in result if t.frequency == frequency]

    return result


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single pet-care activity with duration, priority, recurrence, and a time slot."""

    # Required
    title: str
    category: TaskCategory
    duration_minutes: int

    # Optional with defaults
    priority: PriorityLevel = "medium"
    is_completed: bool = False

    # Recurrence — when frequency != "none", mark_complete() auto-advances next_due
    frequency: Frequency = "none"
    next_due: date | None = None   # None means "always due"; set for recurring tasks

    # Assigned by Scheduler during plan generation; None until scheduled
    start_time: str | None = None  # "HH:MM" wall-clock slot

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def mark_complete(self) -> None:
        """Mark this task as done and, for recurring tasks, advance next_due.

        Daily tasks become due again tomorrow; weekly tasks in seven days.
        Non-recurring tasks simply flip is_completed to True with no side effects.
        """
        self.is_completed = True
        if self.frequency in _FREQ_DAYS:
            self.next_due = date.today() + timedelta(days=_FREQ_DAYS[self.frequency])

    # Alias for backward compatibility
    complete = mark_complete

    def is_due_today(self) -> bool:
        """Return True if this task should appear in today's schedule.

        A task is due today when:
          - it has no next_due date (non-recurring or never been completed), OR
          - its next_due is today or in the past.
        """
        return self.next_due is None or self.next_due <= date.today()

    def reset_for_today(self) -> None:
        """Clear completion flag without touching recurrence state."""
        self.is_completed = False
        self.start_time = None

    def priority_rank(self) -> int:
        """Return numeric priority rank (higher = more urgent)."""
        return _PRIORITY_RANK.get(self.priority, 0)

    def end_time(self) -> str | None:
        """Return the calculated end time ('HH:MM') if a start_time is assigned."""
        if self.start_time is None:
            return None
        return _minutes_to_time(_time_to_minutes(self.start_time) + self.duration_minutes)

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for st.table / st.dataframe."""
        return {
            "title": self.title,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "frequency": self.frequency,
            "start_time": self.start_time or "—",
            "end_time": self.end_time() or "—",
            "is_completed": self.is_completed,
        }

    def __str__(self) -> str:
        """Return a concise single-line representation for terminal output."""
        status   = "✓" if self.is_completed else "○"
        time_str = f"  {self.start_time}–{self.end_time()}" if self.start_time else ""
        recur    = f" ↺{self.frequency}" if self.frequency != "none" else ""
        return (
            f"{status} [{self.priority.upper():6}] {self.title:<30} "
            f"{self.duration_minutes:>3} min{time_str}{recur}"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------


@dataclass
class Pet:
    """A pet profile that owns a list of care tasks."""

    name: str
    species: str
    age_years: int = 0
    weight_kg: float = 0.0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> bool:
        """Remove a task by title. Returns True if a task was found and removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.title != title]
        return len(self.tasks) < before

    def get_tasks(self) -> list[Task]:
        """Return all tasks in insertion order."""
        return list(self.tasks)

    def get_tasks_by_priority(self) -> list[Task]:
        """Return tasks sorted from highest to lowest priority."""
        return sorted(self.tasks, key=lambda t: t.priority_rank(), reverse=True)

    def get_due_tasks(self) -> list[Task]:
        """Return only tasks that are due today (respects recurrence state)."""
        return [t for t in self.tasks if t.is_due_today()]

    def get_completed_tasks(self) -> list[Task]:
        """Return only tasks marked as complete."""
        return [t for t in self.tasks if t.is_completed]

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks not yet completed."""
        return [t for t in self.tasks if not t.is_completed]

    def reset_daily(self) -> None:
        """Clear completion flags and start_times at the start of a new day."""
        for task in self.tasks:
            task.reset_for_today()

    def __str__(self) -> str:
        """Return a concise summary line for terminal output."""
        return (
            f"{self.name} ({self.species}, {self.age_years}yr, "
            f"{self.weight_kg}kg) — {len(self.tasks)} task(s)"
        )


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------


@dataclass
class Owner:
    """The pet owner — provides the time budget and manages the pet roster."""

    name: str
    available_time_minutes: int = 60
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> bool:
        """Remove a pet by name. Returns True if a pet was found and removed."""
        before = len(self.pets)
        self.pets = [p for p in self.pets if p.name != name]
        return len(self.pets) < before

    def get_pets(self) -> list[Pet]:
        """Return all registered pets."""
        return list(self.pets)

    def get_pet(self, name: str) -> Pet | None:
        """Look up a single pet by name; returns None if not found."""
        for pet in self.pets:
            if pet.name == name:
                return pet
        return None

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all pets in a flat list."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_tasks())
        return tasks

    def get_all_due_tasks(self) -> list[Task]:
        """Return every task due today across all pets."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_due_tasks())
        return tasks

    def get_total_available_time(self) -> int:
        """Return the owner's total time budget in minutes."""
        return self.available_time_minutes

    def __str__(self) -> str:
        """Return a concise summary line for terminal output."""
        return (
            f"{self.name} — {self.available_time_minutes} min available, "
            f"{len(self.pets)} pet(s)"
        )


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


@dataclass
class Scheduler:
    """Builds a time-bounded daily care plan with time-slot assignment.

    Strategy — greedy priority-first:
      1. Collect candidate tasks that are due today (respects recurrence).
      2. Sort by priority (high → medium → low).
      3. Greedily add each task while it fits in the remaining time budget.
      4. Assign sequential HH:MM start_times starting from schedule_start_time.
      5. Record skipped tasks for reporting and conflict detection.
    """

    owner: Owner
    scheduled_date: date = field(default_factory=date.today)
    time_budget_minutes: int = 0        # 0 → inherit from owner
    schedule_start_time: str = "08:00"  # wall-clock start for the day's plan
    scheduled_tasks: list[Task] = field(default_factory=list)
    _skipped_tasks: list[Task] = field(default_factory=list, repr=False)
    _pet_name: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        """Resolve time budget from owner when not set explicitly."""
        if self.time_budget_minutes <= 0:
            self.time_budget_minutes = self.owner.get_total_available_time()

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    def generate_plan(self, pet: Pet) -> list[Task]:
        """Select, time-stamp, and order tasks for one pet within the time budget.

        Only tasks that are due today (task.is_due_today()) are considered.
        Results are stored in self.scheduled_tasks.
        """
        self._pet_name = pet.name
        due = sorted(pet.get_due_tasks(), key=lambda t: t.priority_rank(), reverse=True)
        return self._run_greedy(due)

    def generate_full_plan(self) -> list[Task]:
        """Build a plan across all of the owner's pets.

        Retrieves tasks via owner.get_all_due_tasks() so recurrence is respected,
        then runs the greedy algorithm over all pets combined.
        """
        self._pet_name = "all pets"
        due = sorted(
            self.owner.get_all_due_tasks(),
            key=lambda t: t.priority_rank(),
            reverse=True,
        )
        return self._run_greedy(due)

    def _run_greedy(self, sorted_tasks: list[Task]) -> list[Task]:
        """Core greedy loop: add tasks while time remains and assign start_times."""
        self.scheduled_tasks = []
        self._skipped_tasks  = []
        remaining    = self.time_budget_minutes
        current_mins = _time_to_minutes(self.schedule_start_time)

        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                task.start_time = _minutes_to_time(current_mins)
                self.scheduled_tasks.append(task)
                current_mins += task.duration_minutes
                remaining    -= task.duration_minutes
            else:
                task.start_time = None   # not scheduled — clear any stale time
                self._skipped_tasks.append(task)

        return self.scheduled_tasks

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_tasks_by_time(self, tasks: list[Task] | None = None) -> list[Task]:
        """Return scheduled tasks sorted by their assigned HH:MM start_time.

        Delegates to the module-level sort_tasks_by_time() helper.
        Pass a custom list to sort an arbitrary set; omit to sort self.scheduled_tasks.
        """
        target = tasks if tasks is not None else self.scheduled_tasks
        return sort_tasks_by_time(target)

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, tasks: list[Task] | None = None) -> list[str]:
        """Scan time-stamped tasks for overlapping windows.

        Two tasks conflict when their [start, end) intervals intersect.
        The greedy scheduler never produces conflicts by construction, but
        manually-time-stamped tasks (e.g. from external sources) may overlap.

        Parameters
        ----------
        tasks: Tasks to check. Defaults to self.scheduled_tasks.

        Returns
        -------
        A list of human-readable warning strings; empty means no conflicts.
        """
        candidates = tasks if tasks is not None else self.scheduled_tasks
        stamped = [t for t in candidates if t.start_time is not None]

        warnings: list[str] = []
        for i, a in enumerate(stamped):
            a_start = _time_to_minutes(a.start_time)
            a_end   = a_start + a.duration_minutes
            for b in stamped[i + 1:]:
                b_start = _time_to_minutes(b.start_time)
                b_end   = b_start + b.duration_minutes
                # Overlap: intervals [a_start, a_end) and [b_start, b_end) intersect
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"⚠  CONFLICT: '{a.title}' ({a.start_time}–{_minutes_to_time(a_end)}) "
                        f"overlaps '{b.title}' ({b.start_time}–{_minutes_to_time(b_end)})"
                    )
        return warnings

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def explain_plan(self) -> str:
        """Return a human-readable, time-annotated explanation of the generated plan."""
        if not self.scheduled_tasks and not self._skipped_tasks:
            return "No plan generated yet. Call generate_plan(pet) first."

        header = (
            f"{'='*65}\n"
            f"  PawPal+ Daily Schedule — {self.scheduled_date}\n"
            f"  Owner : {self.owner.name}   Budget: {self.time_budget_minutes} min"
            f"  (starts {self.schedule_start_time})\n"
            f"  Pet(s): {self._pet_name}\n"
            f"{'='*65}"
        )

        lines = [header, "\nSCHEDULED TASKS:"]
        for i, task in enumerate(self.scheduled_tasks, start=1):
            end = task.end_time() or "?"
            recur = f"  ↺ {task.frequency}" if task.frequency != "none" else ""
            lines.append(
                f"  {i:>2}. [{task.priority.upper():6}] {task.title:<28} "
                f"{task.start_time}–{end}  ({task.duration_minutes} min){recur}"
            )

        if self._skipped_tasks:
            lines.append("\nSKIPPED (not enough time remaining):")
            for task in self._skipped_tasks:
                lines.append(
                    f"       [{task.priority.upper():6}] {task.title:<28} "
                    f"needs {task.duration_minutes} min"
                )

        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append("\nCONFLICT WARNINGS:")
            lines.extend(f"  {w}" for w in conflicts)

        used = self.get_total_duration()
        lines.append(
            f"\n  Time used : {used} / {self.time_budget_minutes} min  "
            f"({self.time_budget_minutes - used} min remaining)"
        )
        lines.append("=" * 65)
        return "\n".join(lines)

    def get_total_duration(self) -> int:
        """Return total minutes consumed by all scheduled tasks."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def get_skipped_tasks(self) -> list[Task]:
        """Return tasks excluded due to time constraints."""
        return list(self._skipped_tasks)
