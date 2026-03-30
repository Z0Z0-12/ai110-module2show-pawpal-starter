# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

Phase 4 adds four algorithmic improvements to `pawpal_system.py`:

### Sorting by time
`sort_tasks_by_time(tasks)` returns tasks ordered by their assigned `HH:MM` start slot.
Because start times are zero-padded strings, lexicographic order equals chronological order — no `datetime` parsing required. The `Scheduler` exposes this as `scheduler.sort_tasks_by_time()` for convenience.

### Filtering
`filter_tasks(tasks, *, status, category, priority, min_duration, max_duration, frequency)` returns a filtered subset of any task list. All arguments are keyword-only and ANDed together, so you can combine them freely:

```python
# pending high-priority tasks under 10 minutes
filter_tasks(all_tasks, status="pending", priority="high", max_duration=10)
```

### Recurring tasks
`Task` now has a `frequency` field (`"none"` / `"daily"` / `"weekly"`). Calling `mark_complete()` on a recurring task automatically sets `next_due` using `timedelta`:

- daily → `next_due = today + 1 day`
- weekly → `next_due = today + 7 days`

`Task.is_due_today()` returns `False` until `next_due` arrives, and the `Scheduler` respects this — completed recurring tasks are automatically excluded from the next plan run.

### Conflict detection
`Scheduler.detect_conflicts(tasks)` checks a list of time-stamped tasks for overlapping `[start, end)` windows and returns human-readable warning strings. The greedy scheduler never produces conflicts by construction (tasks are placed sequentially), but conflict detection is useful when tasks carry pre-assigned times from an external source.

## Testing PawPal+

### Running the tests

```bash
python -m pytest              # run all 72 tests
python -m pytest -v           # verbose: show each test name and result
python -m pytest -k "edge"    # run only the TestEdgeCases group
```

### What the tests cover

The suite in `tests/test_pawpal.py` is organised into six test classes:

| Class | Tests | What it verifies |
|---|---|---|
| `TestTask` | 5 | `mark_complete()`, priority ranking, serialisation |
| `TestPet` | 7 | Add/remove tasks, priority ordering, completion tracking, daily reset |
| `TestOwner` | 4 | Add/remove pets, name lookup, cross-pet task aggregation |
| `TestScheduler` | 10 | Budget enforcement, priority ordering, start-time assignment, plan idempotency |
| `TestSortTasksByTime` | 3 | Chronological ordering, unscheduled tasks sort last, no mutation |
| `TestFilterTasks` | 7 | Status, category, priority, duration, combined filters, empty input |
| `TestRecurringTasks` | 6 | daily/weekly `next_due` advancement, `is_due_today()`, scheduler exclusion |
| `TestConflictDetection` | 6 | Single conflict, three-way conflict, adjacent tasks (no conflict), warning content |
| `TestEdgeCases` | 24 | Zero budget, exact-fit boundary, empty pets/owners, bad data, stable sort, `reset_for_today`, independent same-name tasks across pets |

### Key edge cases tested

- **Exact budget fit** — a task that fills the budget to the minute is scheduled, not skipped.
- **All tasks exceed budget** — the plan is empty and all tasks appear in the skipped list.
- **All recurring tasks already done** — when every task's `next_due` is in the future, the plan is empty without raising.
- **Calling `generate_plan()` twice** — the second call replaces, not appends to, `scheduled_tasks`.
- **Two pets with the same task title** — completing one pet's task must not affect the other's.
- **Unknown priority string** — `priority_rank()` returns 0 safely rather than raising `KeyError`.
- **Three mutually-overlapping tasks** — `detect_conflicts()` reports all C(3,2) = 3 pairs.

### Confidence level

**★★★★☆ (4/5)**

The core scheduling behaviours — priority ordering, time-budget enforcement, recurrence, and conflict detection — are thoroughly covered. The primary gap is integration testing: the Streamlit UI layer (`app.py`) is not tested, and there are no tests for multi-day sequences of recurring tasks (e.g., verify that a daily task resurfaces correctly after a simulated day-roll). Those would be the next tests to add.
