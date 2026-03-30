"""
PawPal+ — Unit Tests
Run with:  python -m pytest
"""

from datetime import date, timedelta

import pytest
from pawpal_system import Owner, Pet, Scheduler, Task, filter_tasks, sort_tasks_by_time


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_task() -> Task:
    return Task(title="Morning walk", category="walk", duration_minutes=20, priority="high")


@pytest.fixture
def sample_pet() -> Pet:
    return Pet(name="Mochi", species="dog", age_years=3, weight_kg=12.5)


@pytest.fixture
def sample_owner() -> Owner:
    return Owner(name="Jordan", available_time_minutes=60)


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------


class TestTask:
    def test_mark_complete_changes_status(self, sample_task: Task) -> None:
        """Calling mark_complete() must flip is_completed to True."""
        assert sample_task.is_completed is False
        sample_task.mark_complete()
        assert sample_task.is_completed is True

    def test_complete_alias_works(self, sample_task: Task) -> None:
        """complete() is an alias for mark_complete() and must behave identically."""
        sample_task.complete()
        assert sample_task.is_completed is True

    def test_mark_complete_is_idempotent(self, sample_task: Task) -> None:
        """Calling mark_complete() twice should not raise and status stays True."""
        sample_task.mark_complete()
        sample_task.mark_complete()
        assert sample_task.is_completed is True

    def test_priority_rank_values(self) -> None:
        """High priority must outrank medium, which must outrank low."""
        high   = Task("a", "walk", 10, priority="high")
        medium = Task("b", "walk", 10, priority="medium")
        low    = Task("c", "walk", 10, priority="low")
        assert high.priority_rank() > medium.priority_rank() > low.priority_rank()

    def test_to_dict_keys(self, sample_task: Task) -> None:
        """to_dict() must contain all expected keys (including Phase 4 additions)."""
        d = sample_task.to_dict()
        assert set(d.keys()) == {
            "title", "category", "duration_minutes", "priority", "is_completed",
            "frequency", "start_time", "end_time",
        }


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------


class TestPet:
    def test_add_task_increases_count(self, sample_pet: Pet, sample_task: Task) -> None:
        """Adding a task must increase the pet's task count by exactly 1."""
        before = len(sample_pet.get_tasks())
        sample_pet.add_task(sample_task)
        assert len(sample_pet.get_tasks()) == before + 1

    def test_add_multiple_tasks(self, sample_pet: Pet) -> None:
        """Adding three tasks should result in exactly three tasks."""
        for i in range(3):
            sample_pet.add_task(Task(f"Task {i}", "other", duration_minutes=5))
        assert len(sample_pet.get_tasks()) == 3

    def test_get_tasks_by_priority_order(self, sample_pet: Pet) -> None:
        """Tasks returned by get_tasks_by_priority must be in high→medium→low order."""
        sample_pet.add_task(Task("Low task",    "other", 5, priority="low"))
        sample_pet.add_task(Task("High task",   "other", 5, priority="high"))
        sample_pet.add_task(Task("Medium task", "other", 5, priority="medium"))

        ordered = sample_pet.get_tasks_by_priority()
        ranks = [t.priority_rank() for t in ordered]
        assert ranks == sorted(ranks, reverse=True)

    def test_remove_task(self, sample_pet: Pet, sample_task: Task) -> None:
        """remove_task() must return True and the task must no longer be in the list."""
        sample_pet.add_task(sample_task)
        removed = sample_pet.remove_task(sample_task.title)
        assert removed is True
        assert sample_task not in sample_pet.get_tasks()

    def test_remove_nonexistent_task_returns_false(self, sample_pet: Pet) -> None:
        """Removing a task that doesn't exist must return False without raising."""
        assert sample_pet.remove_task("Ghost task") is False

    def test_get_completed_and_pending(self, sample_pet: Pet) -> None:
        """get_completed_tasks and get_pending_tasks must partition the task list."""
        t1 = Task("Walk",  "walk", 10)
        t2 = Task("Feed",  "feed", 5)
        sample_pet.add_task(t1)
        sample_pet.add_task(t2)
        t1.mark_complete()

        assert t1 in sample_pet.get_completed_tasks()
        assert t2 in sample_pet.get_pending_tasks()
        assert t1 not in sample_pet.get_pending_tasks()

    def test_reset_daily_clears_completions(self, sample_pet: Pet) -> None:
        """reset_daily() must set is_completed=False on every task."""
        t = Task("Walk", "walk", 10)
        sample_pet.add_task(t)
        t.mark_complete()
        sample_pet.reset_daily()
        assert all(not task.is_completed for task in sample_pet.get_tasks())


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------


class TestOwner:
    def test_add_pet_increases_count(self, sample_owner: Owner, sample_pet: Pet) -> None:
        """add_pet() must increase the pet count by 1."""
        before = len(sample_owner.get_pets())
        sample_owner.add_pet(sample_pet)
        assert len(sample_owner.get_pets()) == before + 1

    def test_get_pet_by_name(self, sample_owner: Owner, sample_pet: Pet) -> None:
        """get_pet() must return the matching pet or None."""
        sample_owner.add_pet(sample_pet)
        assert sample_owner.get_pet("Mochi") is sample_pet
        assert sample_owner.get_pet("Unknown") is None

    def test_get_all_tasks_aggregates_across_pets(self, sample_owner: Owner) -> None:
        """get_all_tasks() must return tasks from every pet combined."""
        p1 = Pet("Dog", "dog")
        p2 = Pet("Cat", "cat")
        p1.add_task(Task("Walk", "walk", 10))
        p1.add_task(Task("Feed", "feed", 5))
        p2.add_task(Task("Meds", "meds", 3))
        sample_owner.add_pet(p1)
        sample_owner.add_pet(p2)
        assert len(sample_owner.get_all_tasks()) == 3

    def test_remove_pet(self, sample_owner: Owner, sample_pet: Pet) -> None:
        """remove_pet() must return True and the pet must no longer appear in the list."""
        sample_owner.add_pet(sample_pet)
        removed = sample_owner.remove_pet("Mochi")
        assert removed is True
        assert sample_pet not in sample_owner.get_pets()


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------


class TestScheduler:
    def _make_scheduler(self, budget: int = 60) -> tuple[Scheduler, Pet]:
        owner = Owner(name="Alex", available_time_minutes=budget)
        pet = Pet(name="Rex", species="dog")
        return Scheduler(owner=owner), pet

    def test_scheduler_uses_owner_time_budget(self) -> None:
        """Scheduler must inherit time_budget_minutes from owner when not set explicitly."""
        owner = Owner(name="Sam", available_time_minutes=45)
        s = Scheduler(owner=owner)
        assert s.time_budget_minutes == 45

    def test_generate_plan_fits_within_budget(self) -> None:
        """Total duration of scheduled tasks must not exceed the time budget."""
        scheduler, pet = self._make_scheduler(budget=30)
        pet.add_task(Task("Walk",  "walk", 20, priority="high"))
        pet.add_task(Task("Feed",  "feed", 10, priority="high"))
        pet.add_task(Task("Groom", "grooming", 15, priority="low"))

        scheduler.generate_plan(pet)
        assert scheduler.get_total_duration() <= 30

    def test_high_priority_tasks_scheduled_before_low(self) -> None:
        """High-priority tasks must appear before low-priority tasks in the plan."""
        scheduler, pet = self._make_scheduler(budget=60)
        pet.add_task(Task("Low task",  "other", 5, priority="low"))
        pet.add_task(Task("High task", "other", 5, priority="high"))

        plan = scheduler.generate_plan(pet)
        titles = [t.title for t in plan]
        assert titles.index("High task") < titles.index("Low task")

    def test_task_exceeding_budget_is_skipped(self) -> None:
        """A task longer than the entire budget must appear in skipped, not scheduled."""
        scheduler, pet = self._make_scheduler(budget=10)
        big_task = Task("Long walk", "walk", 60, priority="high")
        pet.add_task(big_task)

        scheduler.generate_plan(pet)
        assert big_task not in scheduler.scheduled_tasks
        assert big_task in scheduler.get_skipped_tasks()

    def test_empty_task_list_produces_empty_plan(self) -> None:
        """A pet with no tasks should yield an empty scheduled list."""
        scheduler, pet = self._make_scheduler()
        plan = scheduler.generate_plan(pet)
        assert plan == []

    def test_generate_full_plan_aggregates_pets(self) -> None:
        """generate_full_plan() must consider tasks from all owner pets."""
        owner = Owner(name="Pat", available_time_minutes=100)
        p1 = Pet("Dog", "dog")
        p2 = Pet("Cat", "cat")
        p1.add_task(Task("Walk", "walk", 20, priority="high"))
        p2.add_task(Task("Meds", "meds", 5,  priority="high"))
        owner.add_pet(p1)
        owner.add_pet(p2)

        s = Scheduler(owner=owner)
        plan = s.generate_full_plan()
        titles = [t.title for t in plan]
        assert "Walk" in titles
        assert "Meds" in titles

    def test_explain_plan_contains_scheduled_task_title(self) -> None:
        """explain_plan() output must mention the title of every scheduled task."""
        scheduler, pet = self._make_scheduler(budget=60)
        pet.add_task(Task("Morning walk", "walk", 20, priority="high"))
        scheduler.generate_plan(pet)

        explanation = scheduler.explain_plan()
        assert "Morning walk" in explanation

    def test_explain_plan_before_generate_returns_message(self) -> None:
        """explain_plan() called before generate_plan() must return a helpful message."""
        owner = Owner(name="Sam", available_time_minutes=30)
        s = Scheduler(owner=owner)
        msg = s.explain_plan()
        assert "No plan generated" in msg

    def test_scheduled_tasks_have_start_times(self) -> None:
        """Every task in the generated plan must have a non-None start_time."""
        scheduler, pet = self._make_scheduler(budget=60)
        pet.add_task(Task("Walk", "walk", 10, priority="high"))
        pet.add_task(Task("Feed", "feed", 5,  priority="medium"))
        scheduler.generate_plan(pet)
        for task in scheduler.scheduled_tasks:
            assert task.start_time is not None

    def test_start_times_are_sequential(self) -> None:
        """Tasks must be assigned non-decreasing start times."""
        scheduler, pet = self._make_scheduler(budget=60)
        pet.add_task(Task("A", "walk", 10, priority="high"))
        pet.add_task(Task("B", "feed", 10, priority="high"))
        pet.add_task(Task("C", "meds", 10, priority="high"))
        scheduler.generate_plan(pet)
        times = [task.start_time for task in scheduler.scheduled_tasks]
        assert times == sorted(times)


# ---------------------------------------------------------------------------
# Sorting tests
# ---------------------------------------------------------------------------


class TestSortTasksByTime:
    def test_sorts_chronologically(self) -> None:
        """sort_tasks_by_time() must return tasks in HH:MM ascending order."""
        t1 = Task("Noon",    "other", 10); t1.start_time = "12:00"
        t2 = Task("Morning", "other", 10); t2.start_time = "08:30"
        t3 = Task("Eve",     "other", 10); t3.start_time = "17:00"
        result = sort_tasks_by_time([t1, t2, t3])
        assert [t.start_time for t in result] == ["08:30", "12:00", "17:00"]

    def test_unscheduled_tasks_go_last(self) -> None:
        """Tasks without a start_time must be placed after all timed tasks."""
        timed   = Task("Timed",   "other", 5); timed.start_time = "09:00"
        untimed = Task("Untimed", "other", 5)
        result = sort_tasks_by_time([untimed, timed])
        assert result[0].title == "Timed"
        assert result[-1].title == "Untimed"

    def test_returns_new_list(self) -> None:
        """sort_tasks_by_time() must not mutate the original list."""
        tasks = [Task("A", "other", 5), Task("B", "other", 5)]
        tasks[0].start_time = "10:00"
        tasks[1].start_time = "08:00"
        original_order = [t.title for t in tasks]
        sort_tasks_by_time(tasks)
        assert [t.title for t in tasks] == original_order


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------


class TestFilterTasks:
    def _sample_tasks(self) -> list[Task]:
        t1 = Task("Walk",  "walk",      25, priority="high")
        t2 = Task("Feed",  "feed",       5, priority="high")
        t3 = Task("Brush", "grooming",  15, priority="low")
        t4 = Task("Play",  "enrichment", 10, priority="medium")
        t2.mark_complete()
        return [t1, t2, t3, t4]

    def test_filter_pending(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, status="pending")
        assert all(not t.is_completed for t in result)
        assert len(result) == 3

    def test_filter_completed(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, status="completed")
        assert all(t.is_completed for t in result)
        assert len(result) == 1

    def test_filter_by_category(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, category="walk")
        assert all(t.category == "walk" for t in result)

    def test_filter_by_priority(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, priority="high")
        assert all(t.priority == "high" for t in result)
        assert len(result) == 2

    def test_filter_by_max_duration(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, max_duration=10)
        assert all(t.duration_minutes <= 10 for t in result)

    def test_combined_filters(self) -> None:
        tasks = self._sample_tasks()
        result = filter_tasks(tasks, status="pending", priority="high")
        assert len(result) == 1
        assert result[0].title == "Walk"

    def test_no_filter_returns_all(self) -> None:
        tasks = self._sample_tasks()
        assert len(filter_tasks(tasks)) == len(tasks)


# ---------------------------------------------------------------------------
# Recurring task tests
# ---------------------------------------------------------------------------


class TestRecurringTasks:
    def test_daily_task_advances_next_due_by_one_day(self) -> None:
        """mark_complete() on a daily task must set next_due to tomorrow."""
        task = Task("Walk", "walk", 20, frequency="daily")
        task.mark_complete()
        assert task.next_due == date.today() + timedelta(days=1)

    def test_weekly_task_advances_next_due_by_seven_days(self) -> None:
        """mark_complete() on a weekly task must set next_due to today + 7."""
        task = Task("Flea meds", "meds", 5, frequency="weekly")
        task.mark_complete()
        assert task.next_due == date.today() + timedelta(days=7)

    def test_non_recurring_task_has_no_next_due(self) -> None:
        """mark_complete() on a one-off task must not set next_due."""
        task = Task("One-off", "other", 10, frequency="none")
        task.mark_complete()
        assert task.next_due is None

    def test_completed_recurring_task_not_due_today(self) -> None:
        """A recurring task marked complete today must report is_due_today() = False."""
        task = Task("Daily walk", "walk", 20, frequency="daily")
        task.mark_complete()
        assert task.is_due_today() is False

    def test_overdue_recurring_task_is_due_today(self) -> None:
        """A recurring task with next_due in the past must report is_due_today() = True."""
        task = Task("Old task", "other", 5, frequency="daily")
        task.next_due = date.today() - timedelta(days=1)
        assert task.is_due_today() is True

    def test_scheduler_skips_tasks_not_due(self) -> None:
        """Scheduler must exclude recurring tasks whose next_due is in the future."""
        owner = Owner(name="Pat", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        task  = Task("Walk", "walk", 20, frequency="daily")
        task.mark_complete()   # next_due = tomorrow — not due today
        pet.add_task(task)
        owner.add_pet(pet)

        s = Scheduler(owner=owner)
        plan = s.generate_plan(pet)
        assert task not in plan


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def _stamped(self, title: str, start: str, duration: int) -> Task:
        t = Task(title, "other", duration)
        t.start_time = start
        return t

    def test_overlapping_tasks_produce_warning(self) -> None:
        """Two tasks whose windows overlap must produce at least one conflict warning."""
        owner = Owner(name="X", available_time_minutes=120)
        s = Scheduler(owner=owner)
        t1 = self._stamped("A", "09:00", 60)   # 09:00–10:00
        t2 = self._stamped("B", "09:30", 30)   # 09:30–10:00 — overlaps A
        warnings = s.detect_conflicts([t1, t2])
        assert len(warnings) == 1
        assert "A" in warnings[0] and "B" in warnings[0]

    def test_non_overlapping_tasks_have_no_warnings(self) -> None:
        """Tasks whose windows do not overlap must produce zero warnings."""
        owner = Owner(name="X", available_time_minutes=120)
        s = Scheduler(owner=owner)
        t1 = self._stamped("A", "09:00", 30)   # 09:00–09:30
        t2 = self._stamped("B", "09:30", 30)   # 09:30–10:00 — adjacent, not overlapping
        assert s.detect_conflicts([t1, t2]) == []

    def test_greedy_plan_is_conflict_free(self) -> None:
        """The scheduler's own generated plan must never contain conflicts."""
        owner = Owner(name="Y", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        pet.add_task(Task("Walk", "walk", 20, priority="high"))
        pet.add_task(Task("Feed", "feed", 10, priority="medium"))
        owner.add_pet(pet)

        s = Scheduler(owner=owner)
        s.generate_plan(pet)
        assert s.detect_conflicts() == []

    def test_tasks_without_start_time_ignored(self) -> None:
        """Tasks with no start_time assigned must be ignored by conflict detection."""
        owner = Owner(name="Z", available_time_minutes=60)
        s = Scheduler(owner=owner)
        t1 = Task("Untimed A", "other", 30)
        t2 = Task("Untimed B", "other", 30)
        assert s.detect_conflicts([t1, t2]) == []

    def test_three_way_overlap_produces_three_warnings(self) -> None:
        """Three mutually-overlapping tasks must produce C(3,2)=3 conflict warnings."""
        owner = Owner(name="X", available_time_minutes=180)
        s = Scheduler(owner=owner)
        # All three tasks start at the same time — every pair overlaps
        t1 = self._stamped("A", "10:00", 60)
        t2 = self._stamped("B", "10:00", 60)
        t3 = self._stamped("C", "10:00", 60)
        warnings = s.detect_conflicts([t1, t2, t3])
        assert len(warnings) == 3

    def test_conflict_warning_contains_time_range(self) -> None:
        """Conflict warning strings must include start and end times for both tasks."""
        owner = Owner(name="X", available_time_minutes=120)
        s = Scheduler(owner=owner)
        t1 = self._stamped("Vet",    "09:00", 60)
        t2 = self._stamped("Groom",  "09:30", 30)
        warnings = s.detect_conflicts([t1, t2])
        assert len(warnings) == 1
        w = warnings[0]
        assert "09:00" in w
        assert "09:30" in w


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs that should never crash the system."""

    # --- Scheduler edge cases ---

    def test_single_task_exactly_fills_budget(self) -> None:
        """A task whose duration equals the budget exactly must be scheduled."""
        owner = Owner(name="Sam", available_time_minutes=20)
        pet   = Pet("Dog", "dog")
        pet.add_task(Task("Exact fit", "walk", 20, priority="high"))
        s = Scheduler(owner=owner)
        plan = s.generate_plan(pet)
        assert len(plan) == 1
        assert s.get_total_duration() == 20

    def test_all_tasks_exceed_budget_yields_empty_plan(self) -> None:
        """When every task is longer than the budget, the plan must be empty."""
        owner = Owner(name="Sam", available_time_minutes=5)
        pet   = Pet("Dog", "dog")
        pet.add_task(Task("Long walk",  "walk", 60, priority="high"))
        pet.add_task(Task("Long groom", "grooming", 30, priority="medium"))
        s = Scheduler(owner=owner)
        plan = s.generate_plan(pet)
        assert plan == []
        assert len(s.get_skipped_tasks()) == 2

    def test_owner_with_no_pets_yields_empty_full_plan(self) -> None:
        """An owner with no pets must produce an empty full plan without raising."""
        owner = Owner(name="Empty", available_time_minutes=60)
        s = Scheduler(owner=owner)
        plan = s.generate_full_plan()
        assert plan == []

    def test_pet_with_no_tasks_yields_empty_plan(self) -> None:
        """A pet whose task list is empty must yield an empty plan."""
        owner = Owner(name="Sam", available_time_minutes=60)
        pet   = Pet("Empty", "cat")
        owner.add_pet(pet)
        s = Scheduler(owner=owner)
        assert s.generate_plan(pet) == []

    def test_all_recurring_tasks_already_done_yields_empty_plan(self) -> None:
        """If every recurring task was already completed today, the plan must be empty."""
        owner = Owner(name="Pat", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        t = Task("Walk", "walk", 20, frequency="daily")
        t.mark_complete()   # next_due = tomorrow
        pet.add_task(t)
        owner.add_pet(pet)
        s = Scheduler(owner=owner)
        plan = s.generate_plan(pet)
        assert plan == []

    def test_zero_time_budget_uses_owner_time(self) -> None:
        """Scheduler(time_budget_minutes=0) must inherit the owner's available time."""
        owner = Owner(name="Sam", available_time_minutes=45)
        s = Scheduler(owner=owner, time_budget_minutes=0)
        assert s.time_budget_minutes == 45

    def test_custom_start_time_reflected_in_first_task(self) -> None:
        """schedule_start_time must be the start_time of the first scheduled task."""
        owner = Owner(name="Sam", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        pet.add_task(Task("Walk", "walk", 20, priority="high"))
        s = Scheduler(owner=owner, schedule_start_time="10:30")
        s.generate_plan(pet)
        assert s.scheduled_tasks[0].start_time == "10:30"

    def test_plan_replaces_previous_plan_on_second_call(self) -> None:
        """Calling generate_plan() twice must replace, not append to, scheduled_tasks."""
        owner = Owner(name="Sam", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        pet.add_task(Task("Walk", "walk", 10, priority="high"))
        s = Scheduler(owner=owner)
        s.generate_plan(pet)
        first_count = len(s.scheduled_tasks)
        s.generate_plan(pet)   # call again
        assert len(s.scheduled_tasks) == first_count   # same count, not doubled

    # --- Task edge cases ---

    def test_task_end_time_none_when_no_start_time(self) -> None:
        """end_time() must return None when start_time has not been assigned."""
        t = Task("Walk", "walk", 20)
        assert t.end_time() is None

    def test_task_end_time_correct(self) -> None:
        """end_time() must add duration to start_time correctly."""
        t = Task("Walk", "walk", 45)
        t.start_time = "08:15"
        assert t.end_time() == "09:00"

    def test_reset_for_today_clears_start_time(self) -> None:
        """reset_for_today() must clear start_time as well as is_completed."""
        t = Task("Walk", "walk", 20)
        t.start_time    = "08:00"
        t.is_completed  = True
        t.reset_for_today()
        assert t.start_time is None
        assert t.is_completed is False

    def test_task_with_unknown_priority_rank_returns_zero(self) -> None:
        """An unrecognised priority string must return rank 0 without raising."""
        t = Task("Walk", "walk", 10)
        t.priority = "urgent"   # type: ignore[assignment]  — simulate bad data
        assert t.priority_rank() == 0

    # --- Sorting edge cases ---

    def test_sort_empty_list_returns_empty(self) -> None:
        """sort_tasks_by_time([]) must return an empty list, not raise."""
        assert sort_tasks_by_time([]) == []

    def test_sort_single_item_returns_same(self) -> None:
        """sort_tasks_by_time with one item must return a list with that one item."""
        t = Task("Solo", "other", 10)
        t.start_time = "09:00"
        result = sort_tasks_by_time([t])
        assert len(result) == 1
        assert result[0].title == "Solo"

    def test_sort_tasks_same_time_preserves_relative_order(self) -> None:
        """Tasks with identical start_times must preserve their relative (stable) order."""
        t1 = Task("First",  "other", 5); t1.start_time = "09:00"
        t2 = Task("Second", "other", 5); t2.start_time = "09:00"
        result = sort_tasks_by_time([t1, t2])
        assert result[0].title == "First"
        assert result[1].title == "Second"

    # --- Filter edge cases ---

    def test_filter_empty_list_returns_empty(self) -> None:
        """filter_tasks([]) must return an empty list for any filter combination."""
        assert filter_tasks([], status="pending", priority="high") == []

    def test_filter_no_matches_returns_empty(self) -> None:
        """A filter that matches nothing must return an empty list."""
        tasks = [Task("Walk", "walk", 20, priority="high")]
        result = filter_tasks(tasks, priority="low")
        assert result == []

    def test_filter_min_duration(self) -> None:
        """filter_tasks with min_duration must exclude tasks shorter than the threshold."""
        tasks = [
            Task("Short", "other",  5),
            Task("Medium", "other", 15),
            Task("Long",  "other",  30),
        ]
        result = filter_tasks(tasks, min_duration=15)
        assert all(t.duration_minutes >= 15 for t in result)
        assert len(result) == 2

    def test_filter_does_not_mutate_input(self) -> None:
        """filter_tasks must not modify the original list."""
        tasks = [Task("Walk", "walk", 20, priority="high")]
        original_len = len(tasks)
        filter_tasks(tasks, priority="low")
        assert len(tasks) == original_len

    # --- Owner edge cases ---

    def test_owner_get_all_due_tasks_excludes_not_due(self) -> None:
        """get_all_due_tasks() must skip recurring tasks not yet due today."""
        owner = Owner(name="Sam", available_time_minutes=60)
        pet   = Pet("Dog", "dog")
        due_task     = Task("Feed",  "feed", 5)
        not_due_task = Task("Walk",  "walk", 20, frequency="daily")
        not_due_task.mark_complete()   # pushes next_due to tomorrow
        pet.add_task(due_task)
        pet.add_task(not_due_task)
        owner.add_pet(pet)

        due = owner.get_all_due_tasks()
        assert due_task in due
        assert not_due_task not in due

    def test_two_pets_same_task_title_are_independent(self) -> None:
        """Tasks with the same title on different pets must be independent objects."""
        owner = Owner(name="Sam", available_time_minutes=60)
        p1 = Pet("Dog", "dog"); p1.add_task(Task("Feed", "feed", 5))
        p2 = Pet("Cat", "cat"); p2.add_task(Task("Feed", "feed", 5))
        owner.add_pet(p1)
        owner.add_pet(p2)

        dog_task = p1.get_tasks()[0]
        cat_task = p2.get_tasks()[0]
        dog_task.mark_complete()

        assert dog_task.is_completed is True
        assert cat_task.is_completed is False   # must not be affected

    # --- Recurring task edge cases ---

    def test_recurring_task_due_exactly_today(self) -> None:
        """A recurring task with next_due == today must be considered due."""
        t = Task("Walk", "walk", 20, frequency="daily")
        t.next_due = date.today()
        assert t.is_due_today() is True

    def test_recurring_task_due_tomorrow_is_not_due(self) -> None:
        """A recurring task with next_due == tomorrow must NOT be due today."""
        t = Task("Walk", "walk", 20, frequency="daily")
        t.next_due = date.today() + timedelta(days=1)
        assert t.is_due_today() is False

    def test_mark_complete_twice_keeps_later_next_due(self) -> None:
        """Calling mark_complete() twice on a daily task must set next_due to tomorrow
        both times (idempotent relative to today's date)."""
        t = Task("Walk", "walk", 20, frequency="daily")
        t.mark_complete()
        first_due = t.next_due
        t.mark_complete()
        assert t.next_due == first_due   # same date both times
