# PawPal+ Project Reflection

## 1. System Design

### Core User Actions

The three core actions a user should be able to perform in PawPal+:

1. **Add and manage a pet profile** — The user enters their pet's name, species, age, and weight. This gives the system a subject to schedule care for, and species/age can influence which task types are relevant (e.g., older dogs need shorter walks).

2. **Add care tasks with duration and priority** — The user creates tasks like "Morning walk (20 min, high)", "Feed dinner (5 min, high)", or "Brush coat (10 min, low)". Each task captures what needs to happen, how long it takes, and how critical it is — the raw input the scheduler needs.

3. **Generate and view today's daily plan** — Given the owner's available time and the pet's task list, the user clicks a button and receives an ordered, time-aware plan for the day along with a plain-English explanation of why each task was included or excluded.

### Mermaid.js Class Diagram

```mermaid
classDiagram
    class Owner {
        +str name
        +int available_time_minutes
        +list~str~ preferences
        +list~Pet~ pets
        +add_pet(pet: Pet) None
        +get_pets() list
        +get_total_available_time() int
    }

    class Pet {
        +str name
        +str species
        +int age_years
        +float weight_kg
        +list~Task~ tasks
        +add_task(task: Task) None
        +get_tasks() list
        +get_tasks_by_priority() list
    }

    class Task {
        +str title
        +str category
        +int duration_minutes
        +str priority
        +bool is_completed
        +complete() None
        +to_dict() dict
    }

    class Scheduler {
        +Owner owner
        +date scheduled_date
        +int time_budget_minutes
        +list~Task~ scheduled_tasks
        +generate_plan(pet: Pet) list
        +explain_plan() str
        +get_total_duration() int
    }

    Owner "1" --> "0..*" Pet : owns
    Pet "1" --> "0..*" Task : has
    Scheduler --> Owner : uses
    Scheduler --> Pet : schedules for
    Scheduler --> Task : selects
```

**a. Initial design**

The design uses four classes:

- **Owner** — Holds the pet owner's identity and constraints (name, available time in minutes, preferences like "prefer morning tasks"). Responsible for managing the list of pets and exposing total scheduling time to the Scheduler.
- **Pet** — Represents a single pet with basic profile info (name, species, age, weight). Owns a list of Task objects and can return them sorted by priority for the scheduler to consume.
- **Task** — A Python dataclass representing one care activity. Stores title, category (walk/feed/meds/grooming), duration, priority (low/medium/high), and completion status. Responsible for marking itself done and serializing to a dict for display.
- **Scheduler** — The orchestration class. Takes an Owner and operates on a specific Pet's task list. `generate_plan()` greedily selects tasks in priority order until the time budget is exhausted. `explain_plan()` returns a human-readable justification string.

Key relationship: `Owner` has many `Pet`s; each `Pet` has many `Task`s; `Scheduler` receives an `Owner` (for time budget) and a `Pet` (for tasks) and produces a sorted, time-bounded plan.

**b. Design changes**

One notable change from the first sketch: the initial design gave `Scheduler` a direct `pet` attribute set at construction time. After reviewing the skeleton, it was clearer that `generate_plan(pet)` should accept the pet as a parameter instead. This makes the `Scheduler` reusable across multiple pets belonging to the same owner without needing a new instance, which is a better fit for an owner who has more than one pet. The `owner` stays on the constructor because the time budget is truly an owner-level constraint that doesn't change per call.

A second small change: `Task` was initially a plain class. Switching to a Python `@dataclass` eliminated boilerplate `__init__` and `__repr__` code and made the intent (a simple value-holding object) clearer — exactly what Copilot / AI review recommended.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
