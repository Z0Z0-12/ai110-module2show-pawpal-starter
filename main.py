"""
PawPal+ — CLI Demo Script
Run this to verify your logic works end-to-end before touching the Streamlit UI.

Usage:
    python main.py
"""

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_world() -> tuple[Owner, Pet, Pet]:
    """Create a sample owner with two pets and a realistic task list."""

    # --- Owner ---
    jordan = Owner(
        name="Jordan",
        available_time_minutes=75,
        preferences=["prefer morning tasks", "skip grooming on weekdays"],
    )

    # --- Pet 1: Mochi the dog ---
    mochi = Pet(name="Mochi", species="dog", age_years=3, weight_kg=12.5)
    mochi.add_task(Task("Morning walk",      "walk",       duration_minutes=25, priority="high"))
    mochi.add_task(Task("Breakfast feeding", "feed",       duration_minutes=5,  priority="high"))
    mochi.add_task(Task("Evening walk",      "walk",       duration_minutes=20, priority="medium"))
    mochi.add_task(Task("Flea medication",   "meds",       duration_minutes=5,  priority="high"))
    mochi.add_task(Task("Brush coat",        "grooming",   duration_minutes=15, priority="low"))
    mochi.add_task(Task("Puzzle toy",        "enrichment", duration_minutes=10, priority="low"))

    # --- Pet 2: Luna the cat ---
    luna = Pet(name="Luna", species="cat", age_years=5, weight_kg=4.2)
    luna.add_task(Task("Breakfast feeding",  "feed",       duration_minutes=5,  priority="high"))
    luna.add_task(Task("Litter box clean",   "other",      duration_minutes=5,  priority="high"))
    luna.add_task(Task("Thyroid meds",       "meds",       duration_minutes=3,  priority="high"))
    luna.add_task(Task("Laser play session", "enrichment", duration_minutes=10, priority="medium"))
    luna.add_task(Task("Nail trim",          "grooming",   duration_minutes=10, priority="low"))

    jordan.add_pet(mochi)
    jordan.add_pet(luna)
    return jordan, mochi, luna


def print_section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print("─" * 60)


def main() -> None:
    jordan, mochi, luna = build_demo_world()

    # ── Owner summary ────────────────────────────────────────────────
    print_section("Owner & Pets")
    print(f"  {jordan}")
    for pet in jordan.get_pets():
        print(f"    └─ {pet}")

    # ── All tasks for each pet ────────────────────────────────────────
    print_section("Mochi's Task List (priority order)")
    for task in mochi.get_tasks_by_priority():
        print(f"  {task}")

    print_section("Luna's Task List (priority order)")
    for task in luna.get_tasks_by_priority():
        print(f"  {task}")

    # ── Single-pet schedule ───────────────────────────────────────────
    print_section("Single-pet Schedule: Mochi")
    scheduler = Scheduler(owner=jordan)
    scheduler.generate_plan(mochi)
    print(scheduler.explain_plan())

    # ── Mark a task complete and show the update ──────────────────────
    print_section("Mark 'Morning walk' complete")
    walk = next(t for t in mochi.get_tasks() if t.title == "Morning walk")
    walk.mark_complete()
    print(f"  {walk}")
    completed = mochi.get_completed_tasks()
    pending   = mochi.get_pending_tasks()
    print(f"  Mochi: {len(completed)} done, {len(pending)} still pending")

    # ── Full multi-pet schedule ───────────────────────────────────────
    print_section("Full Multi-pet Schedule (all of Jordan's pets)")
    full_scheduler = Scheduler(owner=jordan)
    full_scheduler.generate_full_plan()
    print(full_scheduler.explain_plan())

    # ── Summary totals ────────────────────────────────────────────────
    print_section("Summary")
    total_tasks = len(jordan.get_all_tasks())
    scheduled   = len(full_scheduler.scheduled_tasks)
    skipped     = len(full_scheduler.get_skipped_tasks())
    print(f"  Total tasks across all pets : {total_tasks}")
    print(f"  Scheduled in today's plan   : {scheduled}")
    print(f"  Skipped (time ran out)      : {skipped}")
    print()


if __name__ == "__main__":
    main()
