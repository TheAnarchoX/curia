# Curia — Product & Architecture Specification

> **Version 0.1** · Living document

---

## 1. Product Vision

Curia aims to be the **open-source political intelligence platform for the
Netherlands**, starting at the municipal level. Dutch municipal councils publish
meeting agendas, votes, motions, and documents through various portals, but the
data is fragmented, unstandardised, and difficult to analyse at scale.

Curia collects that data, normalises it into a unified domain model, and makes
it available through a developer-friendly API and a public web interface. The
long-term goal is to make local politics as transparent and accessible as
national politics — enabling journalists, researchers, watchdog organisations,
and engaged citizens to track what their representatives say, promise, and vote
on.

---

## 2. Scope & Phases

### Phase 1 — Municipal Council Data (current)

Ingest data from **iBabs**, the portal software used by hundreds of Dutch
municipalities. Target entities:

- Institutions and governing bodies
- Politicians and party memberships
- Meetings, agenda items, debate segments
- Motions, amendments, written questions
- Votes and decisions
- Attached documents

Deliver a REST API and foundational web interface.

### Phase 2 — Additional Sources

Expand the connector library:

- **OpenRaadsinformatie** (ORI) — open data aggregator for municipal councils
- **Tweede Kamer Open Data** — Dutch House of Representatives
- **Debat Direct** — Parliamentary debate transcripts
- **Eerste Kamer** — Senate data
- **News feeds** — press releases and local news

### Phase 3 — Analytics & Public Dashboard

Build higher-order features on top of the normalised data:

- Voting pattern analysis and coalition detection
- Promise tracking (link promises to votes and outcomes)
- Attendance and activity metrics
- Trend detection across municipalities
- Public-facing dashboard with search, filters, and visualisations

---

## 3. Architecture

### Layer Diagram

```
┌───────────────────────────────────────────────────────────┐
│                      Data Sources                         │
│   iBabs portals · ORI · Tweede Kamer · News · ...        │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                      Connectors                           │
│   packages/connectors/ibabs   (+ future connectors)       │
│   Responsibility: source-specific crawling & HTML parsing │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                      Ingestion                            │
│   packages/ingestion                                      │
│   Responsibility: HTTP client, rate limiting, retries,    │
│   SourceConnector interface, crawl orchestration          │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                       Domain                              │
│   packages/domain                                         │
│   Responsibility: Pydantic value objects, SQLAlchemy ORM, │
│   database session management, data lineage tracking      │
└────────────┬─────────────────────────────┬────────────────┘
             │                             │
┌────────────▼────────────┐   ┌────────────▼────────────────┐
│          API            │   │          Worker              │
│   apps/api (FastAPI)    │   │   apps/worker (Celery)       │
│   REST endpoints,       │   │   Crawl, extract, normalise, │
│   search, pagination    │   │   analytics, identity res.   │
└────────────┬────────────┘   └─────────────────────────────┘
             │
┌────────────▼────────────┐
│          Web            │
│   apps/web (Next.js)    │
│   Public dashboard,     │
│   search, visualisation │
└─────────────────────────┘
```

### Layer Responsibilities

| Layer | Package | Responsibility |
|-------|---------|----------------|
| **Connectors** | `packages/connectors/*` | Source-specific logic: URL discovery, HTML/API parsing, mapping raw data to intermediate models |
| **Ingestion** | `packages/ingestion` | Source-agnostic crawling framework: async HTTP client, rate limiter, retry policies, `SourceConnector` interface |
| **Domain** | `packages/domain` | Canonical data model (Pydantic v2), SQLAlchemy 2.x ORM, DB session helpers, data lineage & assertion tracking |
| **API** | `apps/api` | REST interface: CRUD endpoints, search, pagination, response schemas, CORS, auth (future) |
| **Worker** | `apps/worker` | Async task execution: crawl orchestration, data extraction, normalisation, identity resolution, analytics |
| **Web** | `apps/web` | User-facing frontend: search, dashboards, entity pages, visualisations |

### Data Flow

```
1. Worker schedules a crawl task for a source (e.g. iBabs portal X).
2. Connector discovers seed URLs via the SourceConnector interface.
3. Ingestion client fetches pages with rate limiting and retries.
4. Connector parsers extract structured data from HTML.
5. Mapper converts connector models → domain value objects.
6. Worker writes domain objects to PostgreSQL via the ORM.
7. Worker runs normalisation & identity resolution passes.
8. Worker computes analytics / metrics.
9. API serves the normalised data to the Web frontend and external consumers.
```

---

## 4. Domain Model

### Entity Map

```
Institution ──────< GoverningBody
     │
     └──< Meeting ──────< AgendaItem ──────< DebateSegment
              │                │
              │                ├──< Motion ──────< Amendment
              │                │       └──< Vote
              │                ├──< Question
              │                └──< Decision
              │
              └──< Document

Party ──────< Politician (via Mandate)
                  │
                  ├──< Vote
                  ├──< Promise
                  └──< Metric

Source ──────< SourceRecord ──────< ExtractionRun ──────< Assertion ──< Evidence

IdentityCandidate ──< IdentityReview

Topic (tagging across motions, questions, promises)
```

### Key Entities

| Entity | Description |
|--------|-------------|
| **Institution** | A municipality or political body (e.g. "Gemeente Amsterdam") |
| **GoverningBody** | Sub-body of an institution (e.g. "Gemeenteraad", "College van B&W") |
| **Party** | Political party with optional national affiliation |
| **Politician** | Individual elected official; linked to parties via time-bounded Mandates |
| **Meeting** | A scheduled or completed council meeting |
| **AgendaItem** | An item on a meeting's agenda |
| **DebateSegment** | A segment of debate within an agenda item |
| **Motion** | A formal proposal put to a vote |
| **Amendment** | A proposed change to a motion |
| **Vote** | A single politician's vote on a motion (for / against / abstain) |
| **Decision** | The outcome of a vote or deliberation |
| **Question** | A written question from a politician to the executive |
| **Promise** | A political promise extracted from speeches or manifestos |
| **Document** | An attached document (PDF, agenda, report) |
| **Topic** | A tag / category used to classify motions, questions, and promises |
| **Metric** | A computed analytical measure (e.g. attendance rate, voting loyalty) |
| **Source** | An external data source (e.g. a specific iBabs portal) |
| **SourceRecord** | A raw record fetched from a source |
| **ExtractionRun** | A processing run that produces assertions from source records |
| **Assertion** | A claimed fact derived from a source, with confidence score |
| **Evidence** | Supporting evidence linking an assertion to its source record |
| **IdentityCandidate** | A potential entity match for deduplication |
| **IdentityReview** | Human or automated review of an identity candidate |

All entities use **UUID primary keys** and carry `created_at` / `updated_at`
timestamps.

---

## 5. Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Language (backend) | Python 3.12+ | Type-annotated throughout |
| API framework | FastAPI | Async, OpenAPI-documented |
| Task queue | Celery 5.x + Redis | Broker & result backend |
| ORM | SQLAlchemy 2.x (async) | Mapped dataclasses, asyncpg driver |
| Validation | Pydantic v2 | Domain models and API schemas |
| Database | PostgreSQL 15 | JSONB, arrays, full-text search |
| Cache / Queue | Redis 7 | Celery broker, future caching |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS | App Router |
| HTML parsing | BeautifulSoup 4 + lxml | Connector parsers |
| HTTP client | httpx | Async with retry & rate limiting |
| Migrations | Alembic | Async-aware, autogenerate support |
| Package management | uv (workspace) | Fast, lockfile-based |
| Linting | ruff | Linting + formatting |
| Type checking | mypy | Strict mode |
| Testing | pytest | async, markers for slow/integration |
| CI | GitHub Actions | lint → typecheck → test → web-lint |
| Containers | Docker Compose | Local dev & deployment |

---

## 6. Operating Principles

### Open Source, Dutch-First

Curia is MIT-licensed and community-driven. The initial focus is the Dutch
political landscape, but the domain model and connector architecture are
designed to be **internationalisation-ready** — the same patterns apply to any
parliamentary system.

### Agent-Friendly Development

The codebase is designed for **AI-assisted development**:

- Clear, typed interfaces between layers (no magic, no implicit state).
- Small, focused modules that fit within an LLM context window.
- Comprehensive docstrings and type annotations as machine-readable documentation.
- A `SourceConnector` plugin interface that lets agents scaffold new connectors
  from a template.

### Type-Safe and Test-Driven

- All public APIs are fully type-annotated.
- Pydantic v2 for runtime validation at every boundary.
- mypy in strict mode across the workspace.
- pytest with async support; `slow` and `integration` markers for selective runs.

### Human-Orchestrated, Agent-Driven

Development follows a **human-orchestrated, agent-driven workflow**:

- Milestones and issues are managed by humans via GitHub Projects.
- Implementation is primarily agent-driven (GitHub Copilot, Codex, etc.).
- PRs are validated by CI and reviewed by humans before merge.
- Specifications and architecture decisions are documented in this file and in
  issues, providing context for both human and AI contributors.

---

## 7. Roadmap

### M1 — Foundation ✅

> Monorepo skeleton, domain model, database schema, CI pipeline.

- [x] uv workspace with apps + packages
- [x] Domain models (Pydantic) and ORM (SQLAlchemy)
- [x] Initial Alembic migration (full schema)
- [x] FastAPI app with v1 endpoint stubs
- [x] Celery worker with task structure
- [x] Next.js scaffold
- [x] Docker Compose (Postgres, Redis, app services)
- [x] GitHub Actions CI (lint, typecheck, test, web-lint)
- [x] Makefile for common dev tasks

### M2 — iBabs Integration

> Live crawling and parsing of iBabs municipal portals.

- [ ] iBabs connector: full crawl of meeting lists, details, documents
- [ ] Parser coverage: all major page types (meetings, members, parties, votes)
- [ ] Checkpoint / resumable crawling
- [ ] Source record storage and extraction run tracking
- [ ] Worker task: end-to-end crawl → parse → store pipeline
- [ ] Integration tests against fixture data

### M3 — API + Frontend MVP

> Functional API and basic web interface.

- [ ] API endpoints: full CRUD with filtering, sorting, pagination
- [ ] Search: full-text search across entities
- [ ] Authentication and API keys
- [ ] Web: institution browser, meeting viewer, politician profiles
- [ ] Web: search interface with faceted filters
- [ ] API documentation and interactive explorer

### M4 — Analytics + Promise Tracking

> Higher-order intelligence on top of the raw data.

- [ ] Voting pattern analysis (loyalty, coalition alignment)
- [ ] Attendance and activity metrics
- [ ] Promise extraction from meeting transcripts
- [ ] Promise ↔ vote linking
- [ ] Trend detection across time and municipalities
- [ ] Metrics API and dashboard widgets

### M5 — Multi-Source + Public Dashboard

> Expand beyond iBabs; launch public-facing interface.

- [ ] OpenRaadsinformatie connector
- [ ] Tweede Kamer Open Data connector
- [ ] News / press release ingestion
- [ ] Identity resolution across sources
- [ ] Public dashboard with municipality comparison
- [ ] Embeddable widgets for media and civic organisations
- [ ] API rate limiting and usage analytics
