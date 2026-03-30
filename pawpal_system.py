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
# Task
# ---------------------------------------------------------------------------

PriorityLevel = Literal["low", "medium", "high"]
TaskCategory = Literal["walk", "feed", "meds", "grooming", "enrichment", "other"]

_PRIORITY_RANK: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Task:
    """A single pet-care activity.

    Attributes
    ----------
    title:            Short human-readable label, e.g. "Morning walk".
    category:         Broad category used for grouping and filtering.
    duration_minutes: How long the task takes (must be > 0).
    priority:         Scheduling importance — high tasks are always attempted first.
    is_completed:     Flipped to True once the task has been performed today.
    """

    title: str
    category: TaskCategory
    duration_minutes: int
    priority: PriorityLevel = "medium"
    is_completed: bool = False

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def complete(self) -> None:
        """Mark this task as done for today."""
        self.is_completed = True

    def priority_rank(self) -> int:
        """Return a numeric rank so tasks can be sorted (higher = more urgent)."""
        return _PRIORITY_RANK.get(self.priority, 0)

    def to_dict(self) -> dict:
        """Serialize to a plain dict (handy for st.table / st.dataframe)."""
        return {
            "title": self.title,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "is_completed": self.is_completed,
        }


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------


@dataclass
class Pet:
    """A pet profile.

    Attributes
    ----------
    name:       The pet's name.
    species:    e.g. "dog", "cat", "rabbit".
    age_years:  Age in whole years (0 for < 1 year).
    weight_kg:  Body weight in kilograms.
    tasks:      The pet's task list for today (managed via add_task).
    """

    name: str
    species: str
    age_years: int = 0
    weight_kg: float = 0.0
    tasks: list[Task] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def add_task(self, task: Task) -> None:
        """Append a new task to this pet's task list."""
        self.tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks (unordered)."""
        return list(self.tasks)

    def get_tasks_by_priority(self) -> list[Task]:
        """Return tasks sorted from highest to lowest priority."""
        return sorted(self.tasks, key=lambda t: t.priority_rank(), reverse=True)

    def reset_tasks(self) -> None:
        """Clear completion flags at the start of a new day."""
        for task in self.tasks:
            task.is_completed = False


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------


@dataclass
class Owner:
    """The pet owner — source of scheduling constraints.

    Attributes
    ----------
    name:                   Owner's name.
    available_time_minutes: Total free time today available for pet care.
    preferences:            Optional list of preference strings,
                            e.g. ["prefer morning tasks", "skip grooming on weekdays"].
    pets:                   Pets this owner is responsible for.
    """

    name: str
    available_time_minutes: int = 60
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all registered pets."""
        return list(self.pets)

    def get_total_available_time(self) -> int:
        """Return the owner's time budget in minutes."""
        return self.available_time_minutes


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


@dataclass
class Scheduler:
    """Builds a time-bounded daily care plan for one pet.

    Strategy: greedy priority-first.
      1. Sort the pet's tasks by priority (high → low).
      2. Walk through the sorted list and add each task to the plan
         as long as it fits within the remaining time budget.
      3. Any task that doesn't fit is skipped and noted in the explanation.

    Attributes
    ----------
    owner:               The owner supplying the time constraint.
    scheduled_date:      The calendar date this plan is for.
    time_budget_minutes: Overrides owner.available_time_minutes if set explicitly.
    scheduled_tasks:     Populated after generate_plan() is called.
    """

    owner: Owner
    scheduled_date: date = field(default_factory=date.today)
    time_budget_minutes: int = 0          # 0 means "use owner's time"
    scheduled_tasks: list[Task] = field(default_factory=list)
    _skipped_tasks: list[Task] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.time_budget_minutes <= 0:
            self.time_budget_minutes = self.owner.get_total_available_time()

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def generate_plan(self, pet: Pet) -> list[Task]:
        """Select and order tasks that fit within the time budget.

        Parameters
        ----------
        pet: The pet whose task list should be scheduled.

        Returns
        -------
        The list of selected Task objects (also stored in self.scheduled_tasks).
        """
        self.scheduled_tasks = []
        self._skipped_tasks = []
        remaining = self.time_budget_minutes

        for task in pet.get_tasks_by_priority():
            if task.duration_minutes <= remaining:
                self.scheduled_tasks.append(task)
                remaining -= task.duration_minutes
            else:
                self._skipped_tasks.append(task)

        return self.scheduled_tasks

    def explain_plan(self) -> str:
        """Return a plain-English explanation of the generated plan.

        Must be called after generate_plan().
        """
        if not self.scheduled_tasks and not self._skipped_tasks:
            return "No plan generated yet. Call generate_plan(pet) first."

        lines: list[str] = [
            f"Plan for {self.scheduled_date} "
            f"(budget: {self.time_budget_minutes} min)\n"
        ]

        lines.append("Scheduled tasks:")
        cumulative = 0
        for task in self.scheduled_tasks:
            cumulative += task.duration_minutes
            lines.append(
                f"  [{task.priority.upper()}] {task.title} "
                f"— {task.duration_minutes} min (ends at {cumulative} min)"
            )

        if self._skipped_tasks:
            lines.append("\nSkipped (not enough time):")
            for task in self._skipped_tasks:
                lines.append(
                    f"  [{task.priority.upper()}] {task.title} "
                    f"— {task.duration_minutes} min"
                )

        lines.append(f"\nTotal scheduled: {self.get_total_duration()} min")
        return "\n".join(lines)

    def get_total_duration(self) -> int:
        """Return the sum of durations of all scheduled tasks in minutes."""
        return sum(t.duration_minutes for t in self.scheduled_tasks)
