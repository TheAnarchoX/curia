#!/usr/bin/env bash
# Bootstrap GitHub project management: milestones, labels, and project.
# Requires: gh CLI authenticated with repo scope.
#
# Usage:
#   ./scripts/bootstrap-github.sh            # create milestones + labels
#   ./scripts/bootstrap-github.sh --dry-run  # preview commands without running

set -euo pipefail

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

run() {
  if $DRY_RUN; then
    echo "[dry-run] $*"
  else
    echo "→ $*"
    "$@"
  fi
}

echo "=== Curia GitHub Bootstrap ==="
echo ""

# ---- Milestones ----
echo "--- Creating Milestones ---"
run gh milestone create "M2: iBabs Live Integration" \
  --description "End-to-end data flow from iBabs portals to the database" 2>/dev/null || true

run gh milestone create "M3: API & Frontend MVP" \
  --description "Functional REST API and basic web dashboard" 2>/dev/null || true

run gh milestone create "M4: Analytics & Promise Tracking" \
  --description "Derive insights from raw political data" 2>/dev/null || true

run gh milestone create "M5: Multi-Source & Public Dashboard" \
  --description "Expand beyond iBabs and create a public-facing product" 2>/dev/null || true

echo ""

# ---- Labels ----
echo "--- Creating Labels ---"

# Architecture layers
for layer in connectors ingestion domain api worker web infra; do
  run gh label create "layer:${layer}" --color "1d76db" --force 2>/dev/null || true
done

# Complexity
run gh label create "size:small" --color "0e8a16" --force 2>/dev/null || true
run gh label create "size:medium" --color "fbca04" --force 2>/dev/null || true
run gh label create "size:large" --color "d93f0b" --force 2>/dev/null || true

# Agent suitability
run gh label create "agent:excellent" --color "7057ff" --description "Clear scope, well-defined patterns" --force 2>/dev/null || true
run gh label create "agent:good" --color "7057ff" --description "Mostly automatable, may need review" --force 2>/dev/null || true
run gh label create "agent:mixed" --color "7057ff" --description "Needs human judgment + agent execution" --force 2>/dev/null || true
run gh label create "agent:human-only" --color "7057ff" --description "Requires domain expertise" --force 2>/dev/null || true

# Type labels (ensure defaults)
run gh label create "task" --color "0075ca" --force 2>/dev/null || true
run gh label create "documentation" --color "0075ca" --force 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Next steps:"
echo "  1. Create a GitHub Project (v2) at: https://github.com/TheAnarchoX/Curia/projects"
echo "  2. Add columns: Backlog → Ready → In Progress → In Review → Done"
echo "  3. Create issues using the templates and assign to milestones"
echo "  4. See docs/project-management/agentic-workflow.md for the full workflow guide"
