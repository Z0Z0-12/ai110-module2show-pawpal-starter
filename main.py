"""
PawPal+ — CLI Demo Script
Exercises all Phase 4 features: sorting, filtering, recurring tasks,
and conflict detection.

Usage:
    python main.py
"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task, filter_tasks, sort_tasks_by_time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    print(f"\n{'─'*65}")
    print(f"  {title}")
    print("─" * 65)


# ---------------------------------------------------------------------------
# Demo world
# ---------------------------------------------------------------------------


def build_demo_world() -> tuple[Owner, Pet, Pet]:
    """Create a sample owner with two pets and a rich task list."""

    jordan = Owner(
        name="Jordan",
        available_time_minutes=90,
        preferences=["prefer morning tasks"],
    )

    # Mochi — daily recurring tasks mixed with one-off tasks
    mochi = Pet(name="Mochi", species="dog", age_years=3, weight_kg=12.5)
    mochi.add_task(Task("Morning walk",      "walk",       25, priority="high",   frequency="daily"))
    mochi.add_task(Task("Breakfast feeding", "feed",        5, priority="high",   frequency="daily"))
    mochi.add_task(Task("Evening walk",      "walk",       20, priority="medium", frequency="daily"))
    mochi.add_task(Task("Flea medication",   "meds",        5, priority="high",   frequency="weekly"))
    mochi.add_task(Task("Brush coat",        "grooming",   15, priority="low"))
    mochi.add_task(Task("Puzzle toy",        "enrichment", 10, priority="low"))

    # Luna — mix of recurring and one-off tasks; tasks added out of priority order on purpose
    luna = Pet(name="Luna", species="cat", age_years=5, weight_kg=4.2)
    luna.add_task(Task("Nail trim",          "grooming",   10, priority="low"))          # low first
    luna.add_task(Task("Laser play session", "enrichment", 10, priority="medium"))
    luna.add_task(Task("Thyroid meds",       "meds",        3, priority="high",  frequency="daily"))
    luna.add_task(Task("Litter box clean",   "other",       5, priority="high",  frequency="daily"))
    luna.add_task(Task("Breakfast feeding",  "feed",        5, priority="high",  frequency="daily"))

    jordan.add_pet(mochi)
    jordan.add_pet(luna)
    return jordan, mochi, luna


# ---------------------------------------------------------------------------
# Demo 1 — Sorting tasks by time
# ---------------------------------------------------------------------------


def demo_sorting(scheduler: Scheduler) -> None:
    section("DEMO 1 — Sort by Time (HH:MM)")

    print("  Tasks in plan order (priority-first, as scheduled):")
    for t in scheduler.scheduled_tasks:
        print(f"    {t}")

    sorted_by_time = scheduler.sort_tasks_by_time()
    print("\n  Same tasks sorted by wall-clock start time:")
    for t in sorted_by_time:
        print(f"    {t}")

    print(
        "\n  Note: sort_tasks_by_time() uses a lambda on 'HH:MM' strings.\n"
        "  Lexicographic order is identical to chronological order\n"
        "  because hours and minutes are zero-padded — no datetime parsing needed."
    )


# ---------------------------------------------------------------------------
# Demo 2 — Filtering
# ---------------------------------------------------------------------------


def demo_filtering(jordan: Owner, mochi: Pet, luna: Pet) -> None:
    section("DEMO 2 — Filtering Tasks")

    all_tasks = jordan.get_all_tasks()
    print(f"  Total tasks across all pets: {len(all_tasks)}")

    high_tasks = filter_tasks(all_tasks, priority="high")
    print(f"\n  High-priority tasks ({len(high_tasks)}):")
    for t in high_tasks:
        print(f"    • {t.title} ({t.category}, {t.duration_minutes} min)")

    walk_tasks = filter_tasks(all_tasks, category="walk")
    print(f"\n  Walk tasks only ({len(walk_tasks)}):")
    for t in walk_tasks:
        print(f"    • {t.title}")

    short_pending = filter_tasks(all_tasks, status="pending", max_duration=5)
    print(f"\n  Pending tasks ≤ 5 min ({len(short_pending)}):")
    for t in short_pending:
        print(f"    • {t.title} ({t.duration_minutes} min, {t.priority})")

    recurring = filter_tasks(mochi.get_tasks(), frequency="daily")
    print(f"\n  Mochi's recurring (daily) tasks ({len(recurring)}):")
    for t in recurring:
        print(f"    • {t.title}")


# ---------------------------------------------------------------------------
# Demo 3 — Recurring tasks
# ---------------------------------------------------------------------------


def demo_recurring(mochi: Pet) -> None:
    section("DEMO 3 — Recurring Tasks & next_due")

    walk = next(t for t in mochi.get_tasks() if t.title == "Morning walk")
    flea = next(t for t in mochi.get_tasks() if t.title == "Flea medication")

    print(f"  Before completion:")
    print(f"    Morning walk  — next_due={walk.next_due}  is_due_today={walk.is_due_today()}")
    print(f"    Flea meds     — next_due={flea.next_due}  is_due_today={flea.is_due_today()}")

    walk.mark_complete()
    flea.mark_complete()

    print(f"\n  After mark_complete():")
    print(f"    Morning walk  — next_due={walk.next_due}  (daily: tomorrow)")
    print(f"    Flea meds     — next_due={flea.next_due}  (weekly: 7 days from now)")

    # Now the tasks are NOT due today — scheduler should skip them
    print(f"\n  is_due_today() after completion:")
    print(f"    Morning walk  → {walk.is_due_today()}  (False: rescheduled to tomorrow)")
    print(f"    Flea meds     → {flea.is_due_today()}  (False: rescheduled to next week)")

    print(
        "\n  If we run generate_plan() again now, these two tasks will be excluded\n"
        "  because is_due_today() returns False until their next_due arrives."
    )

    # Simulate "next_due already passed" to show re-inclusion
    walk.next_due = date(2000, 1, 1)   # far in the past
    print(f"\n  After artificially back-dating next_due to 2000-01-01:")
    print(f"    Morning walk  is_due_today() → {walk.is_due_today()}  (True: overdue)")

    # Restore for later demos
    walk.next_due = None
    walk.is_completed = False
    flea.next_due = None
    flea.is_completed = False


# ---------------------------------------------------------------------------
# Demo 4 — Conflict detection
# ---------------------------------------------------------------------------


def demo_conflicts(jordan: Owner) -> None:
    section("DEMO 4 — Conflict Detection")

    scheduler = Scheduler(owner=jordan, schedule_start_time="09:00")

    # Build three tasks with manually overlapping start times
    t1 = Task("Vet appointment",  "other", 60, priority="high")
    t2 = Task("Groomer drop-off", "grooming", 30, priority="high")
    t3 = Task("Afternoon walk",   "walk",  20, priority="medium")

    t1.start_time = "09:00"   # 09:00 – 10:00
    t2.start_time = "09:30"   # 09:30 – 10:00  ← overlaps t1
    t3.start_time = "10:15"   # 10:15 – 10:35  ← no overlap

    manual_tasks = [t1, t2, t3]

    print("  Manually time-stamped tasks:")
    for t in manual_tasks:
        print(f"    {t.start_time}–{t.end_time()}  {t.title}")

    conflicts = scheduler.detect_conflicts(manual_tasks)
    if conflicts:
        print(f"\n  Conflict warnings ({len(conflicts)} found):")
        for w in conflicts:
            print(f"    {w}")
    else:
        print("  No conflicts detected.")

    print(
        "\n  Note: the greedy scheduler never produces conflicts because it\n"
        "  assigns start_times sequentially. detect_conflicts() is most\n"
        "  useful when tasks come from external sources with preset times."
    )

    # Confirm that the greedy plan itself is conflict-free
    sched = Scheduler(owner=jordan, schedule_start_time="08:00")
    pet = jordan.get_pets()[0]
    sched.generate_plan(pet)
    greedy_conflicts = sched.detect_conflicts()
    print(f"\n  Conflicts in greedy-generated plan: {len(greedy_conflicts)}  ← always 0")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    jordan, mochi, luna = build_demo_world()

    # ── Base schedule ────────────────────────────────────────────────────
    section("Base Schedule (all pets, priority-first, starts 08:00)")
    scheduler = Scheduler(owner=jordan, schedule_start_time="08:00")
    scheduler.generate_full_plan()
    print(scheduler.explain_plan())

    # ── Phase 4 demos ────────────────────────────────────────────────────
    demo_sorting(scheduler)
    demo_filtering(jordan, mochi, luna)
    demo_recurring(mochi)
    demo_conflicts(jordan)

    print()


if __name__ == "__main__":
    main()
