"""
PawPal+ — Logic Layer
All backend classes live here. The Streamlit UI (app.py) imports from this module.

Class hierarchy:
  Owner  ──owns──>  Pet  ──has──>  Task
  Scheduler  ──uses──>  Owner, Pet, Task
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PriorityLevel = Literal["low", "medium", "high"]
TaskCategory = Literal["walk", "feed", "meds", "grooming", "enrichment", "other"]

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single pet-care activity with duration, priority, and completion state."""

    title: str
    category: TaskCategory
    duration_minutes: int
    priority: PriorityLevel = "medium"
    is_completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.is_completed = True

    # Alias kept for backward compatibility with earlier skeleton
    complete = mark_complete

    def priority_rank(self) -> int:
        """Return numeric priority so tasks can be sorted (higher = more urgent)."""
        return _PRIORITY_RANK.get(self.priority, 0)

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for st.table / st.dataframe."""
        return {
            "title": self.title,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "is_completed": self.is_completed,
        }

    def __str__(self) -> str:
        """Return a concise single-line representation for terminal output."""
        status = "✓" if self.is_completed else "○"
        return (
            f"{status} [{self.priority.upper():6}] {self.title:<30} "
            f"{self.duration_minutes:>3} min  ({self.category})"
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
        """Remove a task by title. Returns True if a task was removed."""
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.title != title]
        return len(self.tasks) < before

    def get_tasks(self) -> list[Task]:
        """Return all tasks in insertion order."""
        return list(self.tasks)

    def get_tasks_by_priority(self) -> list[Task]:
        """Return tasks sorted from highest to lowest priority."""
        return sorted(self.tasks, key=lambda t: t.priority_rank(), reverse=True)

    def get_completed_tasks(self) -> list[Task]:
        """Return only tasks marked as complete."""
        return [t for t in self.tasks if t.is_completed]

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks not yet completed."""
        return [t for t in self.tasks if not t.is_completed]

    def reset_daily(self) -> None:
        """Clear completion flags at the start of a new day."""
        for task in self.tasks:
            task.is_completed = False

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
        """Remove a pet by name. Returns True if a pet was removed."""
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
    """Builds a time-bounded daily care plan.

    Strategy — greedy priority-first:
      1. Collect candidate tasks (from a specific pet, or all owner pets).
      2. Sort by priority (high → medium → low).
      3. Greedily add each task while it fits in the remaining time budget.
      4. Record skipped tasks so explain_plan() can report them.
    """

    owner: Owner
    scheduled_date: date = field(default_factory=date.today)
    time_budget_minutes: int = 0   # 0 → use owner's available time
    scheduled_tasks: list[Task] = field(default_factory=list)
    _skipped_tasks: list[Task] = field(default_factory=list, repr=False)
    _pet_name: str = field(default="", repr=False)   # set by generate_plan

    def __post_init__(self) -> None:
        """Resolve time budget from owner if not explicitly provided."""
        if self.time_budget_minutes <= 0:
            self.time_budget_minutes = self.owner.get_total_available_time()

    # ------------------------------------------------------------------
    # Plan generation
    # ------------------------------------------------------------------

    def generate_plan(self, pet: Pet) -> list[Task]:
        """Select and order tasks for a single pet within the time budget.

        Talks to the pet directly to retrieve its tasks, then filters and
        sorts them. Results are stored in self.scheduled_tasks.
        """
        self._pet_name = pet.name
        return self._run_greedy(pet.get_tasks_by_priority())

    def generate_full_plan(self) -> list[Task]:
        """Build a plan across all of the owner's pets.

        Retrieves tasks from every pet via the Owner, combines them, and
        runs the same greedy algorithm — useful when the owner cares for
        multiple animals in one session.
        """
        self._pet_name = "all pets"
        all_tasks = sorted(
            self.owner.get_all_tasks(),
            key=lambda t: t.priority_rank(),
            reverse=True,
        )
        return self._run_greedy(all_tasks)

    def _run_greedy(self, sorted_tasks: list[Task]) -> list[Task]:
        """Core greedy loop: add tasks while time remains."""
        self.scheduled_tasks = []
        self._skipped_tasks = []
        remaining = self.time_budget_minutes

        for task in sorted_tasks:
            if task.duration_minutes <= remaining:
                self.scheduled_tasks.append(task)
                remaining -= task.duration_minutes
            else:
                self._skipped_tasks.append(task)

        return self.scheduled_tasks

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def explain_plan(self) -> str:
        """Return a human-readable explanation of the generated plan."""
        if not self.scheduled_tasks and not self._skipped_tasks:
            return "No plan generated yet. Call generate_plan(pet) first."

        header = (
            f"{'='*60}\n"
            f"  PawPal+ Daily Schedule — {self.scheduled_date}\n"
            f"  Owner : {self.owner.name}   Budget: {self.time_budget_minutes} min\n"
            f"  Pet(s): {self._pet_name}\n"
            f"{'='*60}"
        )

        lines = [header, "\nSCHEDULED TASKS:"]
        cumulative = 0
        for i, task in enumerate(self.scheduled_tasks, start=1):
            cumulative += task.duration_minutes
            lines.append(
                f"  {i:>2}. [{task.priority.upper():6}] {task.title:<28} "
                f"{task.duration_minutes:>3} min  (total so far: {cumulative} min)"
            )

        if self._skipped_tasks:
            lines.append("\nSKIPPED (not enough time remaining):")
            for task in self._skipped_tasks:
                lines.append(
                    f"       [{task.priority.upper():6}] {task.title:<28} "
                    f"needs {task.duration_minutes} min"
                )

        used = self.get_total_duration()
        lines.append(
            f"\n  Time used : {used} / {self.time_budget_minutes} min  "
            f"({self.time_budget_minutes - used} min remaining)"
        )
        lines.append("=" * 60)
        return "\n".join(lines)

    def get_total_duration(self) -> int:
        """Return the total minutes consumed by all scheduled tasks."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)

    def get_skipped_tasks(self) -> list[Task]:
        """Return tasks that were excluded due to time constraints."""
        return list(self._skipped_tasks)
