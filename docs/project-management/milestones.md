# Curia — Milestones & Roadmap

This document defines the concrete milestones for the Curia project.
Curia covers **all levels of Dutch politics** — from municipal councils
to national parliament.  Use these when creating GitHub Milestones via
the UI or `gh` CLI.

---

## M1: Foundation ✅

**Goal**: Production-grade monorepo scaffolding with domain model, API skeleton, worker skeleton, and CI.

**Status**: Complete

**Deliverables**:
- [x] Monorepo structure (uv workspace, hatchling)
- [x] Domain layer: Pydantic v2 models, SQLAlchemy 2.x ORM, enums
- [x] API skeleton: FastAPI with health check and v1 routes
- [x] Worker skeleton: Celery app with task stubs
- [x] Ingestion framework: interfaces, crawl client, parsers
- [x] iBabs connector: models, parsers, mapper
- [x] Stub connectors: Tweede Kamer, OpenRaadsinformatie, Kiesraad, Woogle, Eerste Kamer
- [x] Database: Alembic migrations, Docker Compose
- [x] CI: GitHub Actions (lint, typecheck, test, web build)
- [x] Web: Next.js frontend scaffolded
- [x] Documentation: README, SPEC.md
- [x] Project management: Issue templates, PR template, workflow guide

---

## M2: iBabs Live Integration

**Goal**: Prove the end-to-end pipeline with municipal council data from iBabs.

**Key Deliverables**:
- [ ] Live crawling of iBabs portals (configurable municipality)
- [ ] Parse real HTML from iBabs (validate/fix CSS selectors)
- [ ] Map parsed entities to domain models
- [ ] Persist to PostgreSQL via ORM
- [ ] Celery task chain: crawl → parse → map → persist
- [ ] Incremental sync with checkpoint support
- [ ] Rate limiting and retry logic
- [ ] Integration tests against sample HTML fixtures
- [ ] At least 1 real municipality fully working

**Acceptance**:
- Running `make run-worker` and triggering a sync task populates the DB
- Data is queryable via the API

---

## M3: Tweede Kamer Integration

**Goal**: Connect to the richest Dutch political data source — the national parliament.

**Key Deliverables**:
- [ ] OData v4 client for `gegevensmagazijn.tweedekamer.nl`
- [ ] Sync Persoon (members), Fractie (parties), Commissie (committees)
- [ ] Sync Zaak (legislative cases), Document (bills, motions, amendments)
- [ ] Sync Stemming (votes) with per-member voting records
- [ ] Sync Vergadering (plenary sessions) and Activiteit (activities)
- [ ] OData pagination and `$filter` / `$expand` support
- [ ] Map TK entities to Curia domain models
- [ ] Incremental sync via `@odata.nextLink` and modification dates
- [ ] Domain model extensions for national-level entities (Bill, BillStage)
- [ ] Integration tests against OData fixtures

**Acceptance**:
- Current Tweede Kamer members, parties, and recent votes are in the DB
- API serves national parliamentary data alongside municipal data

---

## M4: API & Frontend MVP

**Goal**: Functional REST API and basic web dashboard showing real data.

**Key Deliverables**:
- [ ] API endpoints return real data from the database
- [ ] Pagination, filtering, sorting on all list endpoints
- [ ] Search endpoint (full-text via PostgreSQL)
- [ ] Next.js frontend with basic pages:
  - Dashboard overview (national + municipal data)
  - Politician list + detail (TK members + council members)
  - Party list + detail
  - Meeting / session browser
  - Motion / vote explorer
  - Bill tracker (Tweede Kamer)
- [ ] OpenAPI docs polished and accurate
- [ ] API authentication (API key or OAuth)
- [ ] Error handling and validation

**Acceptance**:
- A user can browse national and municipal political data in the web UI
- API documentation is complete and usable

---

## M5: Additional Data Sources

**Goal**: Expand data coverage across all levels of Dutch politics.

**Key Deliverables**:
- [ ] OpenRaadsinformatie connector — 300+ municipalities via ElasticSearch API
- [ ] Kiesraad connector — official election results (all elections since 2010)
- [ ] Eerste Kamer connector — Senate member data and legislative proceedings
- [ ] Woogle/WOO connector — government FOI documents
- [ ] Cross-source entity resolution (same politician across sources)
- [ ] Provincial and water board data via OpenRaadsinformatie

**Acceptance**:
- Data from at least 3 sources is unified in the database
- Entity resolution links the same politicians across sources

---

## M6: Analytics & Promise Tracking

**Goal**: Derive insights from raw political data at all levels.

**Key Deliverables**:
- [ ] Voting pattern analytics (per politician, per party, per institution)
- [ ] Attendance tracking (plenary + committee)
- [ ] Promise extraction from motions and coalition agreements
- [ ] Promise fulfillment tracking
- [ ] Speaking time analysis
- [ ] Party alignment / coalition analysis
- [ ] National vs. local voting consistency
- [ ] Metrics API endpoints
- [ ] Analytics dashboard in web UI

**Acceptance**:
- Users can see voting patterns and trends across government levels
- Promise tracking shows measurable progress indicators

---

## M7: Public Dashboard & Platform

**Goal**: Polished public-facing product for citizens, journalists, and researchers.

**Key Deliverables**:
- [ ] Public dashboard with embeddable widgets
- [ ] Notifications / alerts for tracked politicians, topics, or votes
- [ ] Data export (CSV, JSON, API)
- [ ] Performance optimization and caching
- [ ] Deployment documentation and infrastructure-as-code
- [ ] User accounts and saved searches
- [ ] Mobile-responsive frontend

---

## Creating Milestones via CLI

```bash
# Create all milestones (run via bootstrap-github.sh or manually)
gh milestone create "M2: iBabs Live Integration" \
  --description "Prove end-to-end pipeline with municipal council data"
gh milestone create "M3: Tweede Kamer Integration" \
  --description "Connect to national parliament OData API"
gh milestone create "M4: API & Frontend MVP" \
  --description "Functional REST API and basic web dashboard"
gh milestone create "M5: Additional Data Sources" \
  --description "OpenRaadsinformatie, Kiesraad, Eerste Kamer, Woogle"
gh milestone create "M6: Analytics & Promise Tracking" \
  --description "Derive insights from political data at all levels"
gh milestone create "M7: Public Dashboard & Platform" \
  --description "Polished public-facing product"
```
