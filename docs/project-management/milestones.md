# Curia — Milestones & Roadmap

This document defines the concrete milestones for the Curia project.
Use these when creating GitHub Milestones via the UI or `gh` CLI.

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
- [x] Database: Alembic migrations, Docker Compose
- [x] CI: GitHub Actions (lint, typecheck, test, web build)
- [x] Documentation: README, SPEC.md

---

## M2: iBabs Live Integration

**Goal**: End-to-end data flow from iBabs portals to the database.

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

## M3: API & Frontend MVP

**Goal**: Functional REST API and basic web dashboard.

**Key Deliverables**:
- [ ] API endpoints return real data from the database
- [ ] Pagination, filtering, sorting on list endpoints
- [ ] Search endpoint (full-text via PostgreSQL)
- [ ] Next.js frontend with basic pages:
  - Dashboard overview
  - Meeting list + detail
  - Politician list + detail
  - Party list + detail
  - Motion/vote explorer
- [ ] OpenAPI docs polished and accurate
- [ ] API authentication (API key or OAuth)
- [ ] Error handling and validation

**Acceptance**:
- A user can browse meetings, politicians, and votes in the web UI
- API documentation is complete and usable

---

## M4: Analytics & Promise Tracking

**Goal**: Derive insights from raw political data.

**Key Deliverables**:
- [ ] Voting pattern analytics (per politician, per party)
- [ ] Attendance tracking
- [ ] Promise extraction from motions/documents
- [ ] Promise fulfillment tracking
- [ ] Speaking time analysis
- [ ] Party alignment / coalition analysis
- [ ] Metrics API endpoints
- [ ] Analytics dashboard in web UI

**Acceptance**:
- Users can see voting patterns and trends
- Promise tracking shows measurable progress

---

## M5: Multi-Source & Public Dashboard

**Goal**: Expand beyond iBabs and create a public-facing product.

**Key Deliverables**:
- [ ] Additional connectors (OpenRaadsinformatie, Tweede Kamer API)
- [ ] Cross-source entity resolution
- [ ] Public dashboard with embeddable widgets
- [ ] Notifications / alerts for tracked topics
- [ ] Data export (CSV, JSON)
- [ ] Performance optimization and caching
- [ ] Deployment documentation

---

## Creating Milestones via CLI

```bash
# Create all milestones
gh milestone create "M1: Foundation" --description "Production-grade monorepo scaffolding" --state closed
gh milestone create "M2: iBabs Live Integration" --description "End-to-end data flow from iBabs to database"
gh milestone create "M3: API & Frontend MVP" --description "Functional REST API and basic web dashboard"
gh milestone create "M4: Analytics & Promise Tracking" --description "Derive insights from political data"
gh milestone create "M5: Multi-Source & Public Dashboard" --description "Expand sources and create public product"
```
