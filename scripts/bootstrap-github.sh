#!/usr/bin/env bash
# Bootstrap GitHub project management: milestones, labels, and backlog issues.
# Requires: gh CLI authenticated with repo scope.
#
# Usage:
#   ./scripts/bootstrap-github.sh                     # full bootstrap
#   ./scripts/bootstrap-github.sh --dry-run           # preview commands
#   ./scripts/bootstrap-github.sh --milestones-only   # only milestones + labels
#   ./scripts/bootstrap-github.sh --issues-only       # only backlog issues (+ project sync)
#   ./scripts/bootstrap-github.sh --no-project        # skip GitHub Project v2 setup
#
# Optional env vars:
#   PROJECT_TITLE="Curia Roadmap"                    # GitHub Project v2 title
#   PROJECT_PHASE_FIELD="Phase"                      # single-select field used as board columns

set -euo pipefail

DRY_RUN=false
MILESTONES=true
ISSUES=true
PROJECT=true
PROJECT_TITLE="${PROJECT_TITLE:-Curia Roadmap}"
PROJECT_PHASE_FIELD="${PROJECT_PHASE_FIELD:-Phase}"
PROJECT_PHASE_OPTIONS="Backlog,Ready,In Progress,In Review,Done"

REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
OWNER="${REPO%/*}"

declare -a ISSUE_NUMBERS=()
PROJECT_NUMBER=""
PROJECT_ID=""
PHASE_FIELD_ID=""
BACKLOG_OPTION_ID=""

for arg in "$@"; do
  case "$arg" in
    --dry-run)         DRY_RUN=true ;;
    --milestones-only) ISSUES=false; PROJECT=false ;;
    --issues-only)     MILESTONES=false ;;
    --no-project)      PROJECT=false ;;
    --project-only)    MILESTONES=false; ISSUES=false; PROJECT=true ;;
  esac
done

run() {
  if $DRY_RUN; then
    echo "[dry-run] $*"
  else
    echo "→ $*"
    "$@"
  fi
}

echo "=== Curia GitHub Bootstrap ==="
echo "  REPO=$REPO"
echo "  DRY_RUN=$DRY_RUN  MILESTONES=$MILESTONES  ISSUES=$ISSUES  PROJECT=$PROJECT"
echo ""

jq_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf "%s" "$s"
}

milestone_number_by_title() {
  local title="$1"
  local escaped_title
  escaped_title="$(jq_escape "$title")"
  {
    gh api --method GET --paginate "repos/$REPO/milestones?state=open&per_page=100" \
      --jq ".[] | select(.title==\"$escaped_title\") | .number" 2>/dev/null || true
    gh api --method GET --paginate "repos/$REPO/milestones?state=closed&per_page=100" \
      --jq ".[] | select(.title==\"$escaped_title\") | .number" 2>/dev/null || true
  } | head -n1
}

ensure_milestone() {
  local title="$1"
  local description="$2"
  local number
  number="$(milestone_number_by_title "$title")"

  if [[ -n "$number" ]]; then
    if $DRY_RUN; then
      echo "[dry-run] gh api --method PATCH repos/$REPO/milestones/$number -f title='$title' -f description='<...>'"
    else
      echo "→ Updating milestone: $title"
      gh api --method PATCH "repos/$REPO/milestones/$number" \
        -f title="$title" \
        -f description="$description" >/dev/null
    fi
  else
    if $DRY_RUN; then
      echo "[dry-run] gh api --method POST repos/$REPO/milestones -f title='$title' -f description='<...>'"
    else
      echo "→ Creating milestone: $title"
      gh api --method POST "repos/$REPO/milestones" \
        -f title="$title" \
        -f description="$description" >/dev/null
    fi
  fi
}

ensure_label() {
  local name="$1"
  local color="$2"
  local description="${3:-}"
  if [[ -n "$description" ]]; then
    run gh label create "$name" --color "$color" --description "$description" --force
  else
    run gh label create "$name" --color "$color" --force
  fi
}

issue_number_by_title() {
  local title="$1"
  local escaped_title
  escaped_title="$(jq_escape "$title")"
  gh api --method GET --paginate "repos/$REPO/issues?state=all&per_page=100" \
    --jq ".[] | select(.pull_request|not) | select(.title==\"$escaped_title\") | .number" 2>/dev/null | head -n1 || true
}

# ====================================================================
# MILESTONES & LABELS
# ====================================================================
if $MILESTONES; then

echo "--- Creating Milestones ---"
ensure_milestone "M2: iBabs Live Integration" \
  "Prove end-to-end pipeline with municipal council data"
ensure_milestone "M3: Tweede Kamer Integration" \
  "Connect to national parliament OData API - richest Dutch political data source"
ensure_milestone "M4: API & Frontend MVP" \
  "Functional REST API and basic web dashboard with real data"
ensure_milestone "M5: Additional Data Sources" \
  "OpenRaadsinformatie, Kiesraad elections, Eerste Kamer, Woogle/WOO"
ensure_milestone "M6: Analytics & Promise Tracking" \
  "Derive insights from political data at all levels"
ensure_milestone "M7: Public Dashboard & Platform" \
  "Polished public-facing product for citizens, journalists, researchers"
echo ""

echo "--- Creating Labels ---"
for layer in connectors ingestion domain api worker web infra; do
  ensure_label "layer:${layer}" "1d76db" "Work touching the ${layer} layer"
done
ensure_label "size:small" "0e8a16" "Small scoped task"
ensure_label "size:medium" "fbca04" "Medium scoped task"
ensure_label "size:large" "d93f0b" "Large scoped task"
ensure_label "agent:excellent" "7057ff" "Clear scope, well-defined patterns"
ensure_label "agent:good" "7057ff" "Mostly automatable, may need review"
ensure_label "agent:mixed" "7057ff" "Needs human judgment + agent execution"
ensure_label "agent:human-only" "7057ff" "Requires domain expertise"
ensure_label "task" "0075ca" "General implementation task"
ensure_label "documentation" "0075ca" "Documentation updates"
ensure_label "source:ibabs" "c5def5" "Issue for iBabs source"
ensure_label "source:tweedekamer" "c5def5" "Issue for Tweede Kamer source"
ensure_label "source:openraadsinformatie" "c5def5" "Issue for OpenRaadsinformatie source"
ensure_label "source:kiesraad" "c5def5" "Issue for Kiesraad source"
ensure_label "source:eerstekamer" "c5def5" "Issue for Eerste Kamer source"
ensure_label "source:woogle" "c5def5" "Issue for Woogle/WOO source"
echo ""

fi # MILESTONES


# ====================================================================
# BACKLOG ISSUES — a rich worklog for agent-driven development
# ====================================================================
if $ISSUES; then

echo "--- Creating Backlog Issues ---"
echo ""

# Helper: create an issue without duplicates (idempotent by exact title)
issue() {
  local title="$1" milestone="$2" labels="$3"
  shift 3
  local body="$*"
  local existing_number
  existing_number="$(issue_number_by_title "$title")"

  if [[ -n "$existing_number" ]]; then
    echo "→ Exists: #$existing_number $title"
    ISSUE_NUMBERS+=("$existing_number")
    return 0
  fi

  if $DRY_RUN; then
    echo "[dry-run] gh issue create --title '$title' --milestone '$milestone' --label '$labels'"
  else
    echo "→ Creating: $title"
    local created_url
    created_url="$(gh issue create \
      --title "$title" \
      --milestone "$milestone" \
      --label "$labels" \
      --body "$body")"
    ISSUE_NUMBERS+=("${created_url##*/}")
  fi
}

project_enabled() {
  if ! $PROJECT; then
    return 1
  fi

  if $DRY_RUN; then
    return 0
  fi

  if gh project list --owner "$OWNER" --format json >/dev/null 2>&1; then
    return 0
  fi

  echo "! Skipping project setup: current gh token cannot access GitHub Projects."
  echo "! Run: gh auth refresh -s project"
  PROJECT=false
  return 1
}

project_number_by_title() {
  local title="$1"
  local escaped_title
  escaped_title="$(jq_escape "$title")"
  gh project list --owner "$OWNER" --format json \
    --jq "(.projects // .)[]? | select(.title==\"$escaped_title\") | .number" 2>/dev/null | head -n1 || true
}

ensure_project() {
  if ! project_enabled; then
    return 1
  fi

  if $DRY_RUN; then
    echo "[dry-run] ensure project '$PROJECT_TITLE' for owner '$OWNER'"
    return 0
  fi

  PROJECT_NUMBER="$(project_number_by_title "$PROJECT_TITLE")"
  if [[ -z "$PROJECT_NUMBER" ]]; then
    echo "→ Creating project: $PROJECT_TITLE"
    PROJECT_NUMBER="$(gh project create --owner "$OWNER" --title "$PROJECT_TITLE" --format json --jq '.number')"
  else
    echo "→ Reusing project #$PROJECT_NUMBER: $PROJECT_TITLE"
  fi

  PROJECT_ID="$(gh project view "$PROJECT_NUMBER" --owner "$OWNER" --format json --jq '.id')"
}

ensure_project_phase_field() {
  if ! $PROJECT; then
    return 1
  fi

  if $DRY_RUN; then
    echo "[dry-run] ensure single-select field '$PROJECT_PHASE_FIELD' with options: $PROJECT_PHASE_OPTIONS"
    return 0
  fi

  local escaped_field
  escaped_field="$(jq_escape "$PROJECT_PHASE_FIELD")"

  PHASE_FIELD_ID="$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json \
    --jq "(.fields // .)[]? | select(.name==\"$escaped_field\") | .id" | head -n1 || true)"

  if [[ -z "$PHASE_FIELD_ID" ]]; then
    echo "→ Creating project field: $PROJECT_PHASE_FIELD"
    PHASE_FIELD_ID="$(gh project field-create "$PROJECT_NUMBER" \
      --owner "$OWNER" \
      --name "$PROJECT_PHASE_FIELD" \
      --data-type SINGLE_SELECT \
      --single-select-options "$PROJECT_PHASE_OPTIONS" \
      --format json \
      --jq '.id')"
  else
    echo "→ Reusing project field: $PROJECT_PHASE_FIELD"
  fi

  BACKLOG_OPTION_ID="$(gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json \
    --jq "(.fields // .)[]? | select(.name==\"$escaped_field\") | .options[]? | select(.name==\"Backlog\") | .id" | head -n1 || true)"

  if [[ -z "$BACKLOG_OPTION_ID" ]]; then
    echo "! Could not find 'Backlog' option in field '$PROJECT_PHASE_FIELD'; items will be added without phase assignment."
  fi
}

add_issue_to_project() {
  local issue_number="$1"
  local issue_url="https://github.com/$REPO/issues/$issue_number"

  if ! $PROJECT; then
    return 0
  fi

  if $DRY_RUN; then
    echo "[dry-run] gh project item-add $PROJECT_NUMBER --owner '$OWNER' --url '$issue_url'"
    return 0
  fi

  local item_id
  item_id="$(gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$issue_url" --format json --jq '.id' 2>/dev/null || true)"

  if [[ -z "$item_id" ]]; then
    item_id="$(gh project item-list "$PROJECT_NUMBER" --owner "$OWNER" --limit 1000 --format json \
      --jq "(.items // .)[]? | select(.content.url==\"$issue_url\") | .id" | head -n1 || true)"
  fi

  if [[ -z "$item_id" ]]; then
    echo "! Could not add or locate issue #$issue_number in project."
    return 0
  fi

  if [[ -n "$PHASE_FIELD_ID" && -n "$BACKLOG_OPTION_ID" ]]; then
    gh project item-edit \
      --id "$item_id" \
      --project-id "$PROJECT_ID" \
      --field-id "$PHASE_FIELD_ID" \
      --single-select-option-id "$BACKLOG_OPTION_ID" >/dev/null 2>&1 || true
  fi
}

# ------------------------------------------------------------------ M2: iBabs
M2="M2: iBabs Live Integration"

issue "iBabs: collect sample HTML fixtures from real municipalities" "$M2" "source:ibabs,size:medium,agent:mixed" \
"## Task
Crawl 2–3 real iBabs municipality portals and save representative HTML pages as test fixtures.

### Acceptance Criteria
- [ ] Fixtures saved in \`tests/fixtures/ibabs/\` (meeting list, meeting detail, member roster, party list, document page)
- [ ] At least 2 different municipalities represented
- [ ] Each fixture has a companion \`.json\` metadata file with source URL and date

### Agent Notes
Use \`httpx\` or \`curl\` to fetch pages. Example portal: https://ibabs.eu (find municipality links).
Store in \`tests/fixtures/ibabs/<municipality>/<page-type>.html\`."

issue "iBabs: validate and fix CSS selectors against real HTML" "$M2" "source:ibabs,layer:connectors,size:medium,agent:good" \
"## Task
Run the existing iBabs parsers against real HTML fixtures and fix any broken CSS selectors.

### Acceptance Criteria
- [ ] All parsers in \`packages/connectors/ibabs/curia_connectors_ibabs/parsers/\` produce valid output from fixtures
- [ ] Unit tests added for each parser using the fixtures
- [ ] Tests pass: \`uv run pytest tests/ -k ibabs\`

### Agent Notes
Key files: \`parsers/meeting_list.py\`, \`parsers/meeting_detail.py\`, \`parsers/member_roster.py\`, \`parsers/agenda_item.py\`
Pattern: each parser has \`can_parse()\` and \`parse()\` methods."

issue "iBabs: implement live crawling with httpx" "$M2" "source:ibabs,layer:connectors,size:medium,agent:excellent" \
"## Task
Implement \`IBabsConnector.crawl_page()\` to actually fetch pages via httpx.

### Acceptance Criteria
- [ ] \`crawl_page()\` fetches URL, returns \`CrawlResult\` with status, content hash, content
- [ ] Respects rate limiting from \`CrawlConfig.rate_limit_rps\`
- [ ] Handles timeouts and HTTP errors gracefully
- [ ] Unit tests with mocked HTTP responses

### Agent Notes
File: \`packages/connectors/ibabs/curia_connectors_ibabs/connector.py\`
Use \`curia_ingestion.client.CrawlClient\` for HTTP calls.
Follow pattern in \`curia_ingestion.interfaces.SourceConnector\`."

issue "iBabs: implement entity mapper to persist to PostgreSQL" "$M2" "source:ibabs,layer:connectors,layer:domain,size:large,agent:good" \
"## Task
Complete the \`IBabsMapper\` to convert parsed iBabs entities into SQLAlchemy ORM objects and persist them.

### Acceptance Criteria
- [ ] Mapper converts Meeting, Politician, Party, Motion, Vote entities
- [ ] Uses async SQLAlchemy session for DB operations
- [ ] Handles upserts (don't duplicate on re-crawl)
- [ ] Integration test with in-memory SQLite or test PostgreSQL

### Agent Notes
Files: \`packages/connectors/ibabs/curia_connectors_ibabs/mapper.py\`, \`packages/domain/curia_domain/db/models.py\`
Pattern: mapper takes \`ParseResult\` → creates/updates ORM objects."

issue "iBabs: Celery task chain (crawl → parse → map → persist)" "$M2" "source:ibabs,layer:worker,size:medium,agent:good" \
"## Task
Wire up the iBabs pipeline as a Celery task chain in the worker app.

### Acceptance Criteria
- [ ] \`source_sync\` task triggers iBabs crawl for a configured municipality
- [ ] Tasks chain: crawl_page → parse → map → persist
- [ ] Checkpoint saved after each successful page
- [ ] Errors logged but don't crash the chain
- [ ] Can be triggered via Celery CLI or API endpoint

### Agent Notes
Files: \`apps/worker/app/tasks/source_sync.py\`, \`apps/worker/app/tasks/crawl.py\`
Follow existing task stubs in \`apps/worker/app/tasks/\`."

issue "iBabs: incremental sync with checkpoint support" "$M2" "source:ibabs,layer:connectors,size:medium,agent:excellent" \
"## Task
Implement checkpoint-based incremental sync so re-runs only fetch new/changed data.

### Acceptance Criteria
- [ ] Checkpoint stores last-synced timestamp and page offsets
- [ ] \`discover_pages()\` uses checkpoint to skip already-synced pages
- [ ] Checkpoint persisted to database between runs
- [ ] Test: run sync twice, second run fetches fewer pages

### Agent Notes
Interface: \`SourceConnector.get_checkpoint()\` / \`set_checkpoint()\`
Checkpoint model should be JSON-serializable dict."

# ------------------------------------------------------------------ M3: Tweede Kamer
M3="M3: Tweede Kamer Integration"

issue "Tweede Kamer: implement OData v4 client" "$M3" "source:tweedekamer,layer:connectors,size:large,agent:good" \
"## Task
Build a reusable OData v4 client for the Tweede Kamer Gegevensmagazijn API.

### Acceptance Criteria
- [ ] Client at \`packages/connectors/tweedekamer/curia_connectors_tweedekamer/odata_client.py\`
- [ ] Supports \`\$filter\`, \`\$select\`, \`\$expand\`, \`\$orderby\`, \`\$top\`, \`\$skip\`
- [ ] Handles \`@odata.nextLink\` pagination automatically
- [ ] Returns typed Pydantic models for each entity set
- [ ] Unit tests with mocked API responses

### Agent Notes
API base: \`https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/\`
No auth required. Returns JSON. CC-0 license.
Entity sets: Persoon, Fractie, Commissie, Zaak, Document, Stemming, Vergadering, etc.
Docs: https://opendata.tweedekamer.nl/documentatie/odata-api"

issue "Tweede Kamer: sync members (Persoon) and parties (Fractie)" "$M3" "source:tweedekamer,layer:connectors,size:medium,agent:excellent" \
"## Task
Implement syncing of Tweede Kamer members and parliamentary groups.

### Acceptance Criteria
- [ ] Fetch all \`Persoon\` entities (current + historical members)
- [ ] Fetch all \`Fractie\` entities (parties/parliamentary groups)
- [ ] Fetch \`FractieZetel\` to link members to parties with date ranges
- [ ] Map to Curia domain: Politician, Party, InstitutionMembership
- [ ] Persist to PostgreSQL
- [ ] Integration test with sample OData responses

### Agent Notes
Connector: \`packages/connectors/tweedekamer/curia_connectors_tweedekamer/connector.py\`
OData entities: \`Persoon\`, \`Fractie\`, \`FractieZetel\`
Domain models: \`Politician\`, \`Party\` in \`packages/domain/curia_domain/models.py\`"

issue "Tweede Kamer: sync votes (Stemming) with per-member records" "$M3" "source:tweedekamer,layer:connectors,size:large,agent:good" \
"## Task
Implement syncing of Tweede Kamer voting records.

### Acceptance Criteria
- [ ] Fetch \`Stemming\` entities with \`\$expand=StemmingsSoort\`
- [ ] Link votes to members (Persoon) and legislative cases (Zaak)
- [ ] Map to Curia domain: Vote, VoteRecord
- [ ] Store individual member votes (voor/tegen/niet deelgenomen)
- [ ] Persist to PostgreSQL with foreign keys
- [ ] Handle large result sets (100k+ voting records)

### Agent Notes
OData: \`Stemming\` entity, linked to \`Persoon\` and \`Zaak\`
Domain: \`Vote\`, \`VoteRecord\` models
This is critical for analytics (M6)."

issue "Tweede Kamer: sync bills and motions (Zaak, Document)" "$M3" "source:tweedekamer,layer:connectors,size:large,agent:good" \
"## Task
Implement syncing of legislative cases, bills, motions, and amendments.

### Acceptance Criteria
- [ ] Fetch \`Zaak\` (legislative cases / dossiers)
- [ ] Fetch \`Document\` with types: wetsvoorstel, motie, amendement, verslag
- [ ] Fetch \`Kamerstukdossier\` for dossier grouping
- [ ] Map to Curia domain: Motion, Amendment, Document + new Bill model
- [ ] Link documents to their parent cases and actors
- [ ] Persist to PostgreSQL

### Agent Notes
OData: \`Zaak\`, \`ZaakActor\`, \`Document\`, \`DocumentActor\`, \`Kamerstukdossier\`
May need to extend domain models for Bill and BillStage entities."

issue "Tweede Kamer: sync committees and sessions" "$M3" "source:tweedekamer,layer:connectors,size:medium,agent:excellent" \
"## Task
Sync committee memberships and plenary/committee session data.

### Acceptance Criteria
- [ ] Fetch \`Commissie\` and \`CommissieLid\` (committees and members)
- [ ] Fetch \`Vergadering\` (plenary sessions)
- [ ] Fetch \`Activiteit\` (activities, hearings)
- [ ] Map to Curia domain: Meeting, AgendaItem, Committee
- [ ] Persist to PostgreSQL

### Agent Notes
OData: \`Commissie\`, \`CommissieLid\`, \`Vergadering\`, \`Activiteit\`, \`Agendapunt\`
Domain: \`Meeting\`, \`AgendaItem\` models already exist."

issue "Domain: add national-level entities (Bill, BillStage, Election, ElectionResult)" "$M3" "layer:domain,size:medium,agent:excellent" \
"## Task
Extend the domain layer with entities specific to national parliament.

### Acceptance Criteria
- [ ] Add Pydantic models: \`BillCreate\`, \`BillResponse\`, \`BillStageCreate\`, \`BillStageResponse\`
- [ ] Add SQLAlchemy ORM models: \`Bill\`, \`BillStage\`
- [ ] Add enums: \`BillStatus\`, \`BillType\`, \`ElectionType\`
- [ ] Alembic migration for new tables
- [ ] All type checks pass

### Agent Notes
Files: \`packages/domain/curia_domain/models.py\`, \`packages/domain/curia_domain/db/models.py\`, \`packages/domain/curia_domain/enums.py\`
Follow existing patterns for Motion/Amendment models."

# ------------------------------------------------------------------ M4: API & Frontend
M4="M4: API & Frontend MVP"

issue "API: implement database-backed GET endpoints for all v1 resources" "$M4" "layer:api,layer:domain,size:large,agent:excellent" \
"## Task
Replace the stub/placeholder v1 API endpoints with real database-backed implementations.

### Acceptance Criteria
- [ ] All v1 routers query PostgreSQL via async SQLAlchemy
- [ ] Pagination with \`limit\`/\`offset\` query params
- [ ] Filtering by key fields (institution, date range, party, etc.)
- [ ] Proper 404 handling for single-entity endpoints
- [ ] Response schemas match the existing \`schemas/responses.py\`
- [ ] At least 1 integration test per endpoint

### Agent Notes
Routers: \`apps/api/app/routers/v1/*.py\`
Schemas: \`apps/api/app/schemas/responses.py\`
DB session: use \`apps/api/app/dependencies.py:get_db\`"

issue "API: add search endpoint with PostgreSQL full-text search" "$M4" "layer:api,size:medium,agent:good" \
"## Task
Implement the search endpoint using PostgreSQL full-text search.

### Acceptance Criteria
- [ ] \`GET /api/v1/search?q=<query>\` returns results across all entity types
- [ ] Uses PostgreSQL \`tsvector\` / \`tsquery\` for Dutch-language search
- [ ] Results ranked by relevance
- [ ] Supports filtering by entity type, date range, institution
- [ ] Pagination support

### Agent Notes
File: \`apps/api/app/routers/v1/search.py\`
Consider adding GIN index on tsvector columns in the migration.
Dutch language config: \`to_tsvector('dutch', ...)\`"

issue "Web: create dashboard page with data overview" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Build the main dashboard page in the Next.js frontend.

### Acceptance Criteria
- [ ] Dashboard at \`/\` shows overview statistics (total meetings, politicians, votes, etc.)
- [ ] Cards linking to key sections (Tweede Kamer, municipalities, parties)
- [ ] Fetches data from the API (\`/api/v1/metrics\`)
- [ ] Responsive design with Tailwind CSS
- [ ] TypeScript types for API responses

### Agent Notes
App: \`apps/web/src/app/page.tsx\`
Use Next.js server components where possible.
API base URL configurable via environment variable."

issue "Web: politician list and detail pages" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Create pages to browse and view politicians.

### Acceptance Criteria
- [ ] \`/politicians\` — paginated list with search, party filter
- [ ] \`/politicians/[id]\` — detail page with voting record, committee memberships
- [ ] Works for both Tweede Kamer members and municipal council members
- [ ] Server-side rendering for SEO

### Agent Notes
Pages: \`apps/web/src/app/politicians/page.tsx\`, \`apps/web/src/app/politicians/[id]/page.tsx\`
API: \`GET /api/v1/politicians\`, \`GET /api/v1/politicians/{id}\`"

issue "Web: meeting/session browser" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Create pages to browse parliamentary sessions and municipal meetings.

### Acceptance Criteria
- [ ] \`/meetings\` — list with date filter, institution filter
- [ ] \`/meetings/[id]\` — detail with agenda items, documents, votes
- [ ] Calendar view option
- [ ] Distinguish national sessions from municipal meetings

### Agent Notes
Pages: \`apps/web/src/app/meetings/\`
API: \`GET /api/v1/meetings\`"

# ------------------------------------------------------------------ M5: Additional Sources
M5="M5: Additional Data Sources"

issue "OpenRaadsinformatie: implement ElasticSearch API client" "$M5" "source:openraadsinformatie,layer:connectors,size:medium,agent:good" \
"## Task
Implement the OpenRaadsinformatie connector to query the ORI ElasticSearch API.

### Acceptance Criteria
- [ ] Query events, motions, vote_events, organizations, persons indices
- [ ] Filter by municipality/organization
- [ ] Handle ES pagination (scroll or search_after)
- [ ] Map ORI entities to Curia domain models
- [ ] Integration tests with mock ES responses

### Agent Notes
Connector: \`packages/connectors/openraadsinformatie/curia_connectors_ori/connector.py\`
API: \`https://api.openraadsinformatie.nl/v1/\`
Docs: https://github.com/openstate/open-raadsinformatie/blob/master/API-docs.md"

issue "Kiesraad: implement election results connector" "$M5" "source:kiesraad,layer:connectors,size:large,agent:mixed" \
"## Task
Build the Kiesraad connector to ingest official Dutch election results.

### Acceptance Criteria
- [ ] Discover election datasets from data.overheid.nl API
- [ ] Download and parse EML (Election Markup Language) XML files
- [ ] Extract: election metadata, party results, candidate results, per-municipality breakdowns
- [ ] Map to Curia domain: Election, ElectionResult, Party, Politician
- [ ] Cover: Tweede Kamer, Eerste Kamer, Provinciale Staten, Gemeenteraad elections
- [ ] Tests with sample EML fixtures

### Agent Notes
Connector: \`packages/connectors/kiesraad/curia_connectors_kiesraad/connector.py\`
Ref: https://github.com/DIRKMJK/kiesraad (Python EML parser)
Data: https://data.overheid.nl (search kiesraad verkiezingsuitslagen)
Domain: will need Election and ElectionResult models."

issue "Eerste Kamer: implement web scraper connector" "$M5" "source:eerstekamer,layer:connectors,size:medium,agent:mixed" \
"## Task
Implement the Eerste Kamer connector using web scraping.

### Acceptance Criteria
- [ ] Scrape current Senate members from eerstekamer.nl/leden
- [ ] Scrape committee memberships
- [ ] Scrape legislative proceedings list
- [ ] Supplement with OpenSanctions API for structured member data
- [ ] Map to Curia domain models
- [ ] Rate limiting and polite crawling

### Agent Notes
Connector: \`packages/connectors/eerstekamer/curia_connectors_eerstekamer/connector.py\`
Uses BeautifulSoup + lxml (already in dependencies).
Be respectful: rate limit to 1 req/sec, include User-Agent header."

issue "Woogle: implement WOO document search connector" "$M5" "source:woogle,layer:connectors,size:medium,agent:mixed" \
"## Task
Implement the Woogle connector for government FOI documents.

### Acceptance Criteria
- [ ] Search Woogle for documents by government body and topic
- [ ] Extract document metadata (title, date, body, category)
- [ ] Link documents to relevant political entities where possible
- [ ] Handle the evolving API surface (no stable REST API yet)

### Agent Notes
Connector: \`packages/connectors/woogle/curia_connectors_woogle/connector.py\`
Woogle: https://woogle.wooverheid.nl
May need to scrape search results initially."

issue "Cross-source entity resolution" "$M5" "layer:domain,layer:ingestion,size:large,agent:mixed" \
"## Task
Implement entity resolution to link the same real-world entities across data sources.

### Acceptance Criteria
- [ ] Match politicians across TK API, iBabs, ORI, Kiesraad (by name, party, dates)
- [ ] Match parties across sources (handle name variations)
- [ ] Confidence scoring for matches
- [ ] Manual override capability for ambiguous matches
- [ ] Resolution results stored in DB

### Agent Notes
This is critical for cross-source analytics.
Consider: fuzzy string matching, date overlap, party membership as signals.
May need a dedicated \`entity_resolution\` module in \`packages/ingestion/\`."

# ------------------------------------------------------------------ Infra / CI
issue "CI: fix mypy type checking errors" "M4: API & Frontend MVP" "layer:infra,size:large,agent:excellent" \
"## Task
Resolve the ~192 mypy errors currently in the codebase.

### Acceptance Criteria
- [ ] \`uv run mypy .\` passes with 0 errors
- [ ] Add type stubs for third-party libraries where needed
- [ ] Add type annotations to untyped functions
- [ ] CI typecheck job passes

### Agent Notes
Current error breakdown: 62 misc, 61 import-untyped, 28 no-untyped-def, 19 type-arg
Config: \`mypy.ini\`
Most import-untyped errors need \`py.typed\` markers or mypy ignore comments."

issue "CI: add pytest test suite with basic smoke tests" "M2: iBabs Live Integration" "layer:infra,size:medium,agent:excellent" \
"## Task
Create a basic test suite that validates the core packages.

### Acceptance Criteria
- [ ] \`tests/\` directory with conftest.py and basic test structure
- [ ] Smoke tests for domain model creation (Pydantic models)
- [ ] Smoke tests for API app creation (\`create_app()\`)
- [ ] Smoke tests for connector instantiation
- [ ] All tests pass in CI without external services
- [ ] \`uv run pytest\` exits 0

### Agent Notes
Test paths configured in \`pyproject.toml\` as \`testpaths = [\"tests\"]\`
Use pytest fixtures for common setup.
Mock external services (DB, Redis) for unit tests."

issue "Infrastructure: Terraform + Hetzner + Cloudflare base setup" "M4: API & Frontend MVP" "layer:infra,size:large,agent:mixed" \
"## Task
Set up the base Terraform infrastructure for staging deployment on Hetzner + Cloudflare.

### Acceptance Criteria
- [ ] Terraform modules in \`infra/terraform/\`: hetzner-server, cloudflare-dns
- [ ] Provisions a Hetzner CX32 VPS with Docker + Caddy
- [ ] Cloudflare DNS records pointing to Hetzner IP
- [ ] Firewall rules: only 80/443 public, SSH via Hetzner firewall
- [ ] Terraform state stored in Hetzner Object Storage (S3-compatible)
- [ ] \`terraform plan\` and \`terraform apply\` work from CI
- [ ] Variables for staging vs. production environments

### Agent Notes
See \`docs/project-management/infrastructure.md\` for full architecture.
Hetzner provider: \`hetznercloud/hcloud\`
Cloudflare provider: \`cloudflare/cloudflare\`
Structure: \`infra/terraform/environments/{staging,production}/\` + \`infra/terraform/modules/\`"

issue "Infrastructure: Caddy reverse proxy configuration" "M4: API & Frontend MVP" "layer:infra,size:medium,agent:excellent" \
"## Task
Create production Caddyfile for reverse proxying all Curia services.

### Acceptance Criteria
- [ ] Caddyfile at \`infra/caddy/Caddyfile\`
- [ ] Routes: \`/\` → Next.js (:3000), \`/api/*\` → FastAPI (:8000)
- [ ] Automatic HTTPS via Cloudflare DNS challenge
- [ ] Security headers (HSTS, CSP, X-Frame-Options)
- [ ] Gzip/Brotli compression
- [ ] Access logging
- [ ] Health check endpoint at \`/health\`

### Agent Notes
Caddy docs: https://caddyserver.com/docs
Use \`tls { dns cloudflare {env.CF_API_TOKEN} }\` for DNS challenge.
See \`docs/project-management/infrastructure.md\` for examples."

issue "Infrastructure: production Docker Compose with Caddy" "M4: API & Frontend MVP" "layer:infra,size:medium,agent:good" \
"## Task
Create a production Docker Compose overlay for deployment on Hetzner.

### Acceptance Criteria
- [ ] \`docker-compose.prod.yml\` extends base compose file
- [ ] Caddy as reverse proxy (replaces dev port mapping)
- [ ] PostgreSQL with persistent volume
- [ ] Redis with AOF persistence
- [ ] Health checks on all services
- [ ] Resource limits (memory, CPU)
- [ ] Log rotation configuration
- [ ] Environment-based configuration (\`.env.production\`)

### Agent Notes
Current \`docker-compose.yml\` is development-only.
Use Caddy Docker image: \`caddy:2-alpine\`
See \`docs/project-management/infrastructure.md\` for overlay design."

issue "Infrastructure: CI/CD pipeline for automated deployments" "M4: API & Frontend MVP" "layer:infra,size:large,agent:good" \
"## Task
Set up GitHub Actions CI/CD that builds, pushes Docker images, and deploys.

### Acceptance Criteria
- [ ] GitHub Actions workflow: \`.github/workflows/deploy.yml\`
- [ ] On merge to main: build Docker images for API, Worker, Web
- [ ] Push images to GitHub Container Registry (GHCR)
- [ ] Deploy to staging via SSH: pull images + docker compose up
- [ ] Manual approval gate for production deploys
- [ ] Rollback capability (previous image tag)
- [ ] Slack/Discord notification on deploy success/failure

### Agent Notes
Use GitHub OIDC for GHCR auth (no PAT needed).
SSH deploy key stored as GitHub secret.
Deploy script: \`scripts/deploy.sh\` on the server."

issue "Infrastructure: PostgreSQL backup to Hetzner Object Storage" "M5: Additional Data Sources" "layer:infra,size:medium,agent:excellent" \
"## Task
Automated PostgreSQL backups with offsite storage.

### Acceptance Criteria
- [ ] Daily pg_dump to Hetzner Object Storage (S3-compatible)
- [ ] Retention: 7 daily, 4 weekly, 3 monthly backups
- [ ] Backup script at \`scripts/backup-db.sh\`
- [ ] Cron job or systemd timer for scheduling
- [ ] Restore script and documented procedure
- [ ] Backup monitoring (alert on failure)

### Agent Notes
Hetzner Object Storage endpoint: \`https://fsn1.your-objectstorage.com\`
Use \`aws s3 cp\` with Hetzner S3 credentials.
Compress with gzip: \`pg_dump | gzip > backup.sql.gz\`"

issue "Infrastructure: monitoring with Uptime Kuma + Loki" "M5: Additional Data Sources" "layer:infra,size:medium,agent:mixed" \
"## Task
Set up basic monitoring and log aggregation.

### Acceptance Criteria
- [ ] Uptime Kuma monitoring all services (API, Web, DB, Redis)
- [ ] Alert on downtime via email/webhook
- [ ] Loki for centralized log collection from Docker containers
- [ ] Grafana dashboard for log search and basic metrics
- [ ] All monitoring services in Docker Compose

### Agent Notes
Uptime Kuma: https://github.com/louislam/uptime-kuma
Loki + Grafana: lightweight alternative to full Prometheus stack.
Add to \`docker-compose.monitoring.yml\` overlay."

# ------------------------------------------------------------------ Frontend Vision
# The frontend is a state-of-the-art data exploration platform, not a basic CRUD UI

issue "Web: design system and component library setup" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Set up a design system foundation for the Curia web app — modern, data-rich, accessible.

### Acceptance Criteria
- [ ] Install and configure shadcn/ui (or Radix UI primitives)
- [ ] Tailwind CSS theme with Curia brand colors and typography
- [ ] Dark mode support (system preference + toggle)
- [ ] Base layout component: sidebar navigation + main content area
- [ ] Typography scale and spacing system
- [ ] Icon set (Lucide)
- [ ] Loading states and skeleton components
- [ ] Storybook or component preview page

### Agent Notes
App: \`apps/web/\`
Use \`npx shadcn@latest init\` to bootstrap.
Design inspiration: data-heavy apps like Linear, Notion, Observable.
Must be information-dense but not cluttered."

issue "Web: API client layer with React Query" "$M4" "layer:web,size:medium,agent:excellent" \
"## Task
Set up the data fetching layer for the frontend.

### Acceptance Criteria
- [ ] Install \`@tanstack/react-query\` for client-side data fetching
- [ ] API client module at \`src/lib/api/\` with typed fetch functions
- [ ] TypeScript types auto-generated from OpenAPI spec (or manually maintained)
- [ ] Query hooks for each API resource (usePoliticians, useMeetings, etc.)
- [ ] Error handling and retry configuration
- [ ] Loading and error state patterns

### Agent Notes
API base URL from \`NEXT_PUBLIC_API_URL\` env var.
Use Next.js server components for initial data, React Query for client interactions.
Consider \`openapi-typescript\` for type generation from OpenAPI spec."

issue "Web: global search with command palette (⌘K)" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Implement a powerful global search experience.

### Acceptance Criteria
- [ ] Command palette opens with ⌘K / Ctrl+K
- [ ] Search across politicians, parties, meetings, motions, documents
- [ ] Instant results as you type (debounced API calls)
- [ ] Keyboard navigation through results
- [ ] Result previews with entity type icons
- [ ] Recent searches saved in localStorage

### Agent Notes
Use \`cmdk\` (https://cmdk.paco.me/) or build on Radix Dialog.
API: \`GET /api/v1/search?q=...\`
Inspiration: GitHub's command palette, Linear's search."

issue "Web: politician profile pages with voting visualisations" "$M4" "layer:web,size:large,agent:good" \
"## Task
Create rich politician profile pages with data visualisations.

### Acceptance Criteria
- [ ] \`/politicians/[id]\` page with:
  - Bio info, photo, party, institution(s)
  - Voting record heatmap (calendar view of votes cast)
  - Party loyalty percentage
  - Committee memberships timeline
  - Recent motions authored/co-signed
  - Speaking activity chart
- [ ] Interactive charts (hover for details, click to filter)
- [ ] Comparison view: side-by-side two politicians
- [ ] Share/embed support for individual charts

### Agent Notes
Charts: use Recharts, Nivo, or D3 + React
Data from multiple API endpoints: \`/politicians/{id}\`, \`/politicians/{id}/votes\`, etc.
Responsive: must work on mobile."

issue "Web: meeting/session detail with timeline view" "$M4" "layer:web,size:large,agent:good" \
"## Task
Create a rich meeting detail page with timeline-based navigation.

### Acceptance Criteria
- [ ] \`/meetings/[id]\` page with:
  - Meeting metadata (date, institution, type)
  - Agenda items as interactive timeline
  - Per-item: speakers, documents, votes, decisions
  - Document viewer (PDF inline or download)
  - Vote outcome visualisation (party-colored bar charts)
- [ ] Collapsible agenda items
- [ ] Jump-to navigation for long meetings
- [ ] Link to source (original iBabs/TK page)

### Agent Notes
Agenda items from \`/api/v1/meetings/{id}/agenda-items\`
Vote data from \`/api/v1/votes?meeting_id={id}\`
Consider virtual scrolling for meetings with 50+ items."

issue "Web: interactive vote explorer with filtering and visualisation" "$M4" "layer:web,size:large,agent:mixed" \
"## Task
Build a vote explorer — the flagship data exploration feature.

### Acceptance Criteria
- [ ] \`/votes\` page with:
  - Filterable table of all votes (date, motion, outcome, institution)
  - Visual breakdown per vote: party-colored stacked bar
  - Filter by: party, politician, date range, institution, outcome
  - Sort by date, margin, participation
- [ ] Drill-down: click vote → see individual member votes
- [ ] Cross-tabulation: party × vote matrix
- [ ] Export filtered results (CSV)
- [ ] URL-encoded filter state (shareable links)

### Agent Notes
Heavy data table: use \`@tanstack/react-table\` for virtualisation.
Charts: party-colored bars, heatmaps.
This is a key differentiator — must feel snappy even with 10k+ rows."

issue "Web: party comparison dashboard" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Create a dashboard for comparing political parties across data dimensions.

### Acceptance Criteria
- [ ] \`/parties\` page listing all parties with key metrics
- [ ] \`/parties/[id]\` detail page with:
  - Member list with photos
  - Voting alignment radar chart
  - Activity metrics (motions filed, questions asked)
  - Coalition/opposition positioning
- [ ] \`/parties/compare\` multi-select comparison view
  - Side-by-side metrics
  - Voting agreement matrix
  - Policy topic overlap

### Agent Notes
Radar charts for multi-dimensional comparison.
Data from: \`/api/v1/parties\`, \`/api/v1/parties/{id}/members\`, \`/api/v1/metrics\`"

issue "Web: document viewer and search" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Build a document browser for political documents (motions, bills, reports).

### Acceptance Criteria
- [ ] \`/documents\` page with faceted search (type, date, author, institution)
- [ ] Document preview with metadata sidebar
- [ ] Full-text search within documents
- [ ] PDF viewer for attached documents
- [ ] Related entities sidebar (linked politicians, meetings, votes)
- [ ] Download/export options

### Agent Notes
API: \`/api/v1/documents\`
PDF viewer: use \`react-pdf\` or browser-native \`<embed>\`
Heavy on search UX — this is where journalists will spend time."

issue "Web: responsive mobile layout" "$M4" "layer:web,size:medium,agent:good" \
"## Task
Ensure the entire web app works well on mobile devices.

### Acceptance Criteria
- [ ] Responsive sidebar → bottom navigation on mobile
- [ ] Tables collapse to card views on small screens
- [ ] Charts resize appropriately
- [ ] Touch-friendly interactions (no hover-only features)
- [ ] Tested on iOS Safari and Android Chrome
- [ ] Lighthouse mobile score > 90

### Agent Notes
Use Tailwind responsive utilities consistently.
Test with Chrome DevTools device emulation.
Priority pages: dashboard, politician profile, meeting detail."

issue "Web: data export and sharing" "$M4" "layer:web,size:small,agent:excellent" \
"## Task
Add data export capabilities throughout the app.

### Acceptance Criteria
- [ ] CSV export button on all data tables
- [ ] JSON export for API consumers
- [ ] Share button generating URL with current filter state
- [ ] Open Graph meta tags for social sharing previews
- [ ] Embed code generator for charts/visualisations

### Agent Notes
CSV generation can be client-side with \`papaparse\`.
URL state: encode filters in query params.
OG tags: Next.js \`generateMetadata\`."

issue "Web: real-time legislative tracker (bills in progress)" "M5: Additional Data Sources" "layer:web,size:large,agent:mixed" \
"## Task
Build a legislative tracker showing bills moving through parliament.

### Acceptance Criteria
- [ ] \`/legislation\` page showing active bills with status pipeline
- [ ] Kanban-style view: Introduced → Committee → Plenary → Decided
- [ ] Bill detail page with full history timeline
- [ ] Related documents, debates, and votes linked
- [ ] Filter by topic, committee, party
- [ ] Notification: subscribe to bill updates

### Agent Notes
Data from Tweede Kamer: \`Zaak\`, \`Document\`, \`Kamerstukdossier\`
Pipeline visualisation: horizontal Kanban or Gantt-like timeline.
Critical for political journalists and lobbyists."

echo ""
echo "=== Backlog Created ==="

fi # ISSUES

if $PROJECT; then
  echo ""
  echo "--- Ensuring GitHub Project board ---"
  ensure_project || true

  if [[ -n "$PROJECT_NUMBER" || "$DRY_RUN" == "true" ]]; then
    ensure_project_phase_field || true

    if [[ "${#ISSUE_NUMBERS[@]}" -gt 0 ]]; then
      echo "→ Syncing ${#ISSUE_NUMBERS[@]} issues into project..."
      for n in "${ISSUE_NUMBERS[@]}"; do
        add_issue_to_project "$n"
      done
    else
      echo "→ No issues collected in this run; skipping project item sync."
    fi
  fi
fi

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Result summary:"
echo "  - Milestones and labels are upserted (safe to run repeatedly)"
echo "  - Issues are created only when exact title does not already exist"
echo "  - Project board is created/reused and issues are linked without duplicates"
echo ""
echo "Recommended next focus: M2 (iBabs) and M3 (Tweede Kamer)"
echo "Workflow guide: docs/project-management/agentic-workflow.md"
