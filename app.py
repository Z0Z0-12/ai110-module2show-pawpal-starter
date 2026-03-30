"""
PawPal+ — Streamlit UI
Connects the user interface to the logic layer (pawpal_system.py).
All application state is stored in st.session_state so data persists
across reruns (Streamlit re-executes the whole file on every interaction).
"""

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Helper — defined first so it can be called anywhere below
# ---------------------------------------------------------------------------


def display_plan(scheduler: Scheduler) -> None:
    """Render scheduler results in a tidy Streamlit layout."""
    scheduled = scheduler.scheduled_tasks
    skipped   = scheduler.get_skipped_tasks()

    used   = scheduler.get_total_duration()
    budget = scheduler.time_budget_minutes

    col_used, col_budget, col_left = st.columns(3)
    col_used.metric("Time used",  f"{used} min")
    col_budget.metric("Budget",   f"{budget} min")
    col_left.metric("Remaining",  f"{budget - used} min")

    if scheduled:
        st.markdown("#### Scheduled tasks")
        st.table([t.to_dict() for t in scheduled])
    else:
        st.warning("No tasks could be scheduled within the time budget.")

    if skipped:
        with st.expander(f"Skipped tasks ({len(skipped)}) — not enough time remaining"):
            st.table([t.to_dict() for t in skipped])

    with st.expander("Full plain-English explanation"):
        st.text(scheduler.explain_plan())


# ---------------------------------------------------------------------------
# Session-state initialisation
# Checked once per browser session; the Owner object is never recreated on rerun.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None   # type: Owner | None

# ---------------------------------------------------------------------------
# Header
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
    # Store the Owner object in the session vault — survives reruns
    st.session_state.owner = Owner(
        name=owner_name,
        available_time_minutes=int(available_time),
        preferences=prefs,
    )
    st.success(f"Owner profile saved for **{owner_name}** ({available_time} min available).")

# Show current owner summary, or stop early if no owner yet
if st.session_state.owner:
    owner: Owner = st.session_state.owner
    st.info(
        f"**{owner.name}** — {owner.available_time_minutes} min available today | "
        f"{len(owner.get_pets())} pet(s) registered"
    )
else:
    st.warning("Fill in your owner profile above to get started.")
    st.stop()   # Nothing below makes sense without an owner

# Convenience alias — same object, not a copy
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
        new_pet = Pet(
            name=pet_name,
            species=species,
            age_years=int(age),
            weight_kg=round(float(weight), 1),
        )
        owner.add_pet(new_pet)           # ← Owner.add_pet() from pawpal_system.py
        st.success(f"Added **{pet_name}** the {species}!")

# Display registered pets with their task tables
pets = owner.get_pets()
if pets:
    for pet in pets:
        with st.expander(
            f"🐾 {pet.name} — {pet.species}, {pet.age_years} yr, {pet.weight_kg} kg "
            f"({len(pet.get_tasks())} task(s))"
        ):
            tasks = pet.get_tasks()
            if tasks:
                st.table([t.to_dict() for t in tasks])
            else:
                st.caption("No tasks yet — add some in Section 3.")
            if st.button(f"Remove {pet.name}", key=f"remove_{pet.name}"):
                owner.remove_pet(pet.name)   # ← Owner.remove_pet() from pawpal_system.py
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

        col_dur, col_pri = st.columns(2)
        with col_dur:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        with col_pri:
            priority = st.selectbox("Priority", ["high", "medium", "low"])

        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        target_pet = owner.get_pet(target_pet_name)   # ← Owner.get_pet() from pawpal_system.py
        new_task = Task(
            title=task_title,
            category=category,
            duration_minutes=int(duration),
            priority=priority,
        )
        target_pet.add_task(new_task)                 # ← Pet.add_task() from pawpal_system.py
        st.success(f"Task **{task_title}** ({duration} min, {priority}) added to **{target_pet_name}**.")

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("4. Generate Today's Schedule")

if not pets:
    st.info("Add at least one pet with tasks to generate a schedule.")
else:
    schedule_mode = st.radio(
        "Schedule for",
        ["All pets", "Specific pet"],
        horizontal=True,
    )

    selected_pet_name = None
    if schedule_mode == "Specific pet":
        selected_pet_name = st.selectbox("Choose pet", [p.name for p in pets], key="sched_pet")

    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner=owner)           # ← Scheduler from pawpal_system.py

        if schedule_mode == "All pets":
            all_tasks = owner.get_all_tasks()        # ← Owner.get_all_tasks() from pawpal_system.py
            if not all_tasks:
                st.warning("No tasks found. Add tasks to your pets first.")
            else:
                scheduler.generate_full_plan()       # ← Scheduler.generate_full_plan()
                display_plan(scheduler)
        else:
            pet_obj = owner.get_pet(selected_pet_name)
            if not pet_obj.get_tasks():
                st.warning(f"{selected_pet_name} has no tasks yet.")
            else:
                scheduler.generate_plan(pet_obj)     # ← Scheduler.generate_plan()
                display_plan(scheduler)
