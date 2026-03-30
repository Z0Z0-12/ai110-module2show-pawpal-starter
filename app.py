"""
PawPal+ — Streamlit UI
Connects every smart feature of the logic layer to a polished, interactive UI.
Phase 6 additions: recurring task controls, schedule start-time picker,
sort-by-time view, conflict warnings, task filter panel, mark-complete buttons.
"""

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task, filter_tasks, sort_tasks_by_time

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _priority_badge(priority: str) -> str:
    """Return a coloured emoji prefix for a priority level."""
    return {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}.get(priority, priority)


def _recur_badge(frequency: str) -> str:
    return {"daily": "↺ daily", "weekly": "↺ weekly", "none": "—"}.get(frequency, frequency)


def display_plan(scheduler: Scheduler) -> None:
    """Render the full schedule result with metrics, time-sorted table,
    conflict warnings, skipped list, and plain-English explanation."""

    scheduled  = scheduler.scheduled_tasks
    skipped    = scheduler.get_skipped_tasks()
    conflicts  = scheduler.detect_conflicts()
    used       = scheduler.get_total_duration()
    budget     = scheduler.time_budget_minutes

    # ── Metrics row ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tasks scheduled", len(scheduled))
    c2.metric("Time used",        f"{used} min")
    c3.metric("Budget",           f"{budget} min")
    c4.metric("Remaining",        f"{budget - used} min")

    st.divider()

    # ── Conflict warnings — shown prominently before the table ───────────────
    if conflicts:
        st.error(
            f"**⚠ {len(conflicts)} scheduling conflict(s) detected.**  "
            "Two tasks overlap in time. Review the warnings below, then "
            "adjust task durations or your available-time budget."
        )
        for w in conflicts:
            st.warning(w)
    else:
        st.success("✅ No scheduling conflicts detected.")

    st.divider()

    if not scheduled:
        st.warning(
            "No tasks could be scheduled within the time budget. "
            "Try increasing your available time or reducing task durations."
        )
        return

    # ── Schedule table — sorted by wall-clock time ───────────────────────────
    sorted_plan = scheduler.sort_tasks_by_time()   # ← Scheduler.sort_tasks_by_time()
    st.markdown("#### 📅 Today's Schedule *(sorted by start time)*")

    rows = []
    for t in sorted_plan:
        rows.append({
            "Start": t.start_time or "—",
            "End":   t.end_time()  or "—",
            "Task":  t.title,
            "Category": t.category,
            "Duration": f"{t.duration_minutes} min",
            "Priority": _priority_badge(t.priority),
            "Recurs":   _recur_badge(t.frequency),
        })
    st.table(rows)

    # ── Skipped tasks ────────────────────────────────────────────────────────
    if skipped:
        with st.expander(f"⏭ Skipped tasks ({len(skipped)}) — not enough time remaining"):
            for t in skipped:
                st.write(
                    f"**{t.title}** — {t.duration_minutes} min, {_priority_badge(t.priority)}"
                )

    # ── Plain-English explanation ────────────────────────────────────────────
    with st.expander("📝 Full plain-English explanation"):
        st.code(scheduler.explain_plan(), language=None)


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# Sidebar — quick stats
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("Daily pet-care planner")
    st.divider()

    if st.session_state.owner:
        owner_sb: Owner = st.session_state.owner
        st.metric("Pets registered", len(owner_sb.get_pets()))
        st.metric("Total tasks", len(owner_sb.get_all_tasks()))
        st.metric("Due today", len(owner_sb.get_all_due_tasks()))
        st.divider()
        st.markdown("**Owner preferences**")
        if owner_sb.preferences:
            for p in owner_sb.preferences:
                st.caption(f"• {p}")
        else:
            st.caption("None set.")
    else:
        st.info("Set up your owner profile to see stats.")

# ---------------------------------------------------------------------------
# Main area header
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+")
st.caption("Your daily pet-care planning assistant.")
st.divider()

# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.subheader("1. Owner Profile")

with st.form("owner_form"):
    col_name, col_time = st.columns(2)
    with col_name:
        owner_name = st.text_input("Your name", value="Jordan")
    with col_time:
        available_time = st.number_input(
            "Time available today (minutes)", min_value=5, max_value=480, value=60, step=5
        )
    preferences_raw = st.text_input(
        "Preferences (comma-separated, optional)",
        placeholder="e.g. prefer morning tasks, skip grooming on weekdays",
    )
    submitted_owner = st.form_submit_button("Save owner profile")

if submitted_owner:
    prefs = [p.strip() for p in preferences_raw.split(",") if p.strip()]
    st.session_state.owner = Owner(
        name=owner_name,
        available_time_minutes=int(available_time),
        preferences=prefs,
    )
    st.success(f"✅ Owner profile saved for **{owner_name}** ({available_time} min available).")

if st.session_state.owner:
    owner: Owner = st.session_state.owner
    st.info(
        f"**{owner.name}** — {owner.available_time_minutes} min available today | "
        f"{len(owner.get_pets())} pet(s) | "
        f"{len(owner.get_all_due_tasks())} task(s) due today"
    )
else:
    st.warning("Fill in your owner profile above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Section 2 — Pet management
# ---------------------------------------------------------------------------

st.divider()
st.subheader("2. Your Pets")

with st.form("add_pet_form"):
    col_pname, col_species, col_age, col_weight = st.columns(4)
    with col_pname:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col_species:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    with col_age:
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
    with col_weight:
        weight = st.number_input("Weight (kg)", min_value=0.1, max_value=200.0, value=10.0, step=0.1)
    submitted_pet = st.form_submit_button("Add pet")

if submitted_pet:
    if owner.get_pet(pet_name):
        st.error(f"A pet named **{pet_name}** already exists. Choose a different name.")
    else:
        owner.add_pet(Pet(name=pet_name, species=species,
                          age_years=int(age), weight_kg=round(float(weight), 1)))
        st.success(f"✅ Added **{pet_name}** the {species}!")

pets = owner.get_pets()
if pets:
    for pet in pets:
        pending   = len(pet.get_pending_tasks())
        completed = len(pet.get_completed_tasks())
        label = (
            f"🐾 {pet.name} — {pet.species}, {pet.age_years} yr, {pet.weight_kg} kg  |  "
            f"{pending} pending · {completed} done"
        )
        with st.expander(label):
            tasks = pet.get_tasks()
            if tasks:
                # ── Filter controls ──────────────────────────────────────────
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    f_status = st.selectbox(
                        "Status", ["all", "pending", "completed"],
                        key=f"fstatus_{pet.name}"
                    )
                with fc2:
                    f_cat = st.selectbox(
                        "Category", ["all", "walk", "feed", "meds", "grooming", "enrichment", "other"],
                        key=f"fcat_{pet.name}"
                    )
                with fc3:
                    f_pri = st.selectbox(
                        "Priority", ["all", "high", "medium", "low"],
                        key=f"fpri_{pet.name}"
                    )

                # Apply filters via filter_tasks() ← from pawpal_system.py
                filtered = filter_tasks(
                    tasks,
                    status=f_status if f_status != "all" else "all",
                    category=f_cat  if f_cat  != "all" else None,
                    priority=f_pri  if f_pri  != "all" else None,
                )

                if filtered:
                    rows = []
                    for t in filtered:
                        status_icon = "✓" if t.is_completed else "○"
                        rows.append({
                            "": status_icon,
                            "Task": t.title,
                            "Category": t.category,
                            "Duration": f"{t.duration_minutes} min",
                            "Priority": _priority_badge(t.priority),
                            "Recurs": _recur_badge(t.frequency),
                            "Next due": str(t.next_due) if t.next_due else "—",
                        })
                    st.table(rows)

                    # ── Mark complete controls ────────────────────────────────
                    st.markdown("**Mark a task complete:**")
                    pending_titles = [t.title for t in pet.get_pending_tasks()]
                    if pending_titles:
                        mc1, mc2 = st.columns([3, 1])
                        with mc1:
                            task_to_complete = st.selectbox(
                                "Choose task", pending_titles,
                                key=f"complete_sel_{pet.name}",
                                label_visibility="collapsed",
                            )
                        with mc2:
                            if st.button("Mark done", key=f"complete_btn_{pet.name}"):
                                target = next(
                                    (t for t in pet.get_tasks() if t.title == task_to_complete), None
                                )
                                if target:
                                    target.mark_complete()   # ← Task.mark_complete()
                                    nd = target.next_due
                                    msg = f"✅ **{task_to_complete}** marked complete."
                                    if nd:
                                        msg += f" Next due: **{nd}**."
                                    st.success(msg)
                                    st.rerun()
                    else:
                        st.caption("All tasks for today are complete! 🎉")
                else:
                    st.caption("No tasks match the current filters.")
            else:
                st.caption("No tasks yet — add some in Section 3.")

            if st.button(f"Remove {pet.name}", key=f"remove_{pet.name}"):
                owner.remove_pet(pet.name)
                st.rerun()
else:
    st.info("No pets yet. Add your first pet above.")

# ---------------------------------------------------------------------------
# Section 3 — Task management
# ---------------------------------------------------------------------------

st.divider()
st.subheader("3. Add a Care Task")

if not pets:
    st.info("Add a pet first, then assign tasks to it.")
else:
    with st.form("add_task_form"):
        col_pet, col_title, col_cat = st.columns(3)
        with col_pet:
            target_pet_name = st.selectbox("Assign to pet", [p.name for p in pets])
        with col_title:
            task_title = st.text_input("Task title", value="Morning walk")
        with col_cat:
            category = st.selectbox(
                "Category", ["walk", "feed", "meds", "grooming", "enrichment", "other"]
            )

        col_dur, col_pri, col_freq = st.columns(3)
        with col_dur:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col_pri:
            priority = st.selectbox("Priority", ["high", "medium", "low"])
        with col_freq:
            frequency = st.selectbox("Recurrence", ["none", "daily", "weekly"],
                                     help="Daily/weekly tasks reschedule themselves after being marked complete.")

        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = owner.get_pet(target_pet_name)
        target_pet.add_task(Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
            frequency=frequency,
        ))
        st.success(
            f"✅ **{task_title}** ({duration} min, {_priority_badge(priority)}, "
            f"{_recur_badge(frequency)}) added to **{target_pet_name}**."
        )

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("4. Generate Today's Schedule")

if not pets:
    st.info("Add at least one pet with tasks to generate a schedule.")
else:
    col_mode, col_start = st.columns(2)
    with col_mode:
        schedule_mode = st.radio(
            "Schedule for",
            ["All pets", "Specific pet"],
            horizontal=True,
        )
    with col_start:
        start_time_str = st.text_input(
            "Day starts at (HH:MM)",
            value="08:00",
            help="Wall-clock time when the first task begins.",
        )

    selected_pet_name = None
    if schedule_mode == "Specific pet":
        selected_pet_name = st.selectbox("Choose pet", [p.name for p in pets], key="sched_pet")

    if st.button("🗓 Generate schedule", type="primary"):
        # Basic HH:MM validation
        try:
            h, m = start_time_str.split(":")
            assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
            valid_start = True
        except Exception:
            st.error("Start time must be in HH:MM format (e.g. 08:00).")
            valid_start = False

        if valid_start:
            scheduler = Scheduler(
                owner=owner,
                schedule_start_time=start_time_str,
            )

            if schedule_mode == "All pets":
                due_tasks = owner.get_all_due_tasks()
                if not due_tasks:
                    st.warning(
                        "No tasks are due today. Either all recurring tasks have already "
                        "been completed, or no tasks have been added yet."
                    )
                else:
                    scheduler.generate_full_plan()
                    display_plan(scheduler)
            else:
                pet_obj = owner.get_pet(selected_pet_name)
                due_tasks = pet_obj.get_due_tasks()
                if not due_tasks:
                    st.warning(
                        f"**{selected_pet_name}** has no tasks due today. "
                        "Add tasks or check if recurring tasks were already completed."
                    )
                else:
                    scheduler.generate_plan(pet_obj)
                    display_plan(scheduler)
