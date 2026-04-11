# Curia — Agentic Workflow Guide

How we manage work in Curia: **human-orchestrated, agent-driven**.

---

## Philosophy

Curia is designed for a hybrid workflow where:

1. **Humans** set direction, define milestones, write issues, and review results
2. **AI agents** (GitHub Copilot, coding agents) execute well-defined tasks
3. **GitHub** is the single source of truth — everything lives in issues, PRs, and projects

This means:
- Issues are written to be **agent-friendly** (clear scope, file hints, acceptance criteria)
- PRs follow a **template** with checklists that both humans and agents can verify
- Milestones provide **concrete goals** that decompose into actionable tasks
- Projects provide **kanban boards** for visual progress tracking

---

## Workflow

### 1. Plan (Human)

```
Human creates Milestone → decomposes into Issues → assigns to Project board
```

- Use `docs/project-management/milestones.md` as the source of truth for milestone scope
- Create issues using the GitHub issue templates (Feature, Bug, Task)
- Add "Agent Implementation Notes" with file paths, patterns, and constraints
- Tag issues with complexity and agent-suitability labels

### 2. Execute (Agent or Human)

```
Pick issue from Project board → Create branch → Implement → PR → Review
```

**For agents (GitHub Copilot)**:
- Point the agent at the issue: "Fix #42" or "Implement the feature described in #42"
- The agent reads the issue, creates a branch, implements, and opens a PR
- Agent follows the PR template and checklist

**For humans**:
- Same flow, but you write the code yourself
- Use `gh issue develop <number>` to create a linked branch

### 3. Review (Human)

```
Human reviews PR → requests changes or approves → merge
```

- Every PR gets human review, regardless of author
- CI must pass (lint, typecheck, test, web build)
- Changes must match the issue's acceptance criteria

### 4. Ship (Automated)

```
Merge to main → CI runs → milestone progress updates
```

---

## GitHub Setup

### Milestones

Create milestones that match `docs/project-management/milestones.md`:

```bash
# Bootstrap milestones (run once)
gh milestone create "M2: iBabs Live Integration" \
  --description "End-to-end data flow from iBabs portals to the database"

gh milestone create "M3: API & Frontend MVP" \
  --description "Functional REST API and basic web dashboard"

gh milestone create "M4: Analytics & Promise Tracking" \
  --description "Derive insights from raw political data"

gh milestone create "M5: Multi-Source & Public Dashboard" \
  --description "Expand beyond iBabs and create a public-facing product"
```

### Projects

Create a GitHub Project (v2) for the active milestone:

```bash
# Create project via GitHub UI: github.com/TheAnarchoX/Curia/projects
# Or use the gh CLI with the GitHub Projects extension
```

Recommended columns:
- **Backlog** — issues defined but not yet prioritized
- **Ready** — issues fully specified and ready to work on
- **In Progress** — actively being worked on
- **In Review** — PR open, awaiting review
- **Done** — merged to main

### Labels

Recommended label set for efficient triage:

```bash
# Architecture layers
gh label create "layer:connectors" --color "1d76db"
gh label create "layer:ingestion" --color "1d76db"
gh label create "layer:domain" --color "1d76db"
gh label create "layer:api" --color "1d76db"
gh label create "layer:worker" --color "1d76db"
gh label create "layer:web" --color "1d76db"
gh label create "layer:infra" --color "1d76db"

# Complexity
gh label create "size:small" --color "0e8a16"
gh label create "size:medium" --color "fbca04"
gh label create "size:large" --color "d93f0b"

# Agent suitability
gh label create "agent:excellent" --color "7057ff"
gh label create "agent:good" --color "7057ff"
gh label create "agent:mixed" --color "7057ff"
gh label create "agent:human-only" --color "7057ff"

# Type
gh label create "enhancement" --color "a2eeef"
gh label create "bug" --color "d73a4a"
gh label create "task" --color "0075ca"
gh label create "documentation" --color "0075ca"
```

---

## Writing Agent-Friendly Issues

The key to effective agent-driven development is well-written issues. Here's a template:

### Good Example

```markdown
## Task: Add GET /api/v1/meetings/{id}/agenda-items endpoint

### Description
Add a nested endpoint that returns agenda items for a specific meeting,
including related documents and speaker events.

### Acceptance Criteria
- [ ] GET /api/v1/meetings/{id}/agenda-items returns paginated list
- [ ] Response uses AgendaItemResponse schema
- [ ] Includes document_links and speaker_events in response
- [ ] 404 if meeting not found
- [ ] Unit test with mock data
- [ ] Type checks pass

### Agent Implementation Notes
**Files to modify:**
- `apps/api/app/routers/v1/meetings.py` — add new route
- `apps/api/app/schemas/responses.py` — ensure AgendaItemResponse exists

**Pattern to follow:**
- See `apps/api/app/routers/v1/politicians.py` for single-entity endpoint
- Use `apps/api/app/dependencies.py:get_db` for database session

**Constraints:**
- Use async/await for all DB operations
- Return 404 with `{"detail": "Meeting not found"}` on missing entity
```

### Bad Example

```markdown
Add agenda items to meetings API
```

The difference: agents need **file paths**, **patterns to follow**, and **testable criteria**.

---

## Using gh CLI for Workflow

Common commands for managing work:

```bash
# List open issues for a milestone
gh issue list --milestone "M2: iBabs Live Integration"

# Create a task issue
gh issue create --template task.yml --milestone "M2: iBabs Live Integration"

# Start working on an issue (creates linked branch)
gh issue develop 42

# Create PR linked to issue
gh pr create --fill --milestone "M2: iBabs Live Integration"

# Assign issue to Copilot agent
# (done via GitHub UI or @copilot mention in issue)

# View project board
gh project view --web
```

---

## Agentic Development Tips

1. **One issue, one PR**: Keep scope tight for faster review cycles
2. **Include test fixtures**: When issues involve parsing, include sample HTML/data
3. **Link everything**: Issues → Milestones → Projects → PRs
4. **Review promptly**: Agents work fast; don't let PRs pile up
5. **Iterate**: If an agent's first attempt isn't perfect, comment with specific feedback and let it iterate
