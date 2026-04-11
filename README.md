# Curia

**Open-source Dutch political intelligence — making municipal politics transparent and accessible.**

---

## What is Curia?

Curia is an open-source platform that ingests, normalises, and surfaces data
from Dutch municipal council systems. It turns scattered meeting agendas,
motions, votes, and documents into a structured, searchable knowledge base that
journalists, researchers, and engaged citizens can query through a clean API and
web interface.

The project starts with **iBabs** — the portal software used by hundreds of
Dutch municipalities — and is designed to expand to additional sources such as
OpenRaadsinformatie, parliamentary APIs, and news feeds. A pluggable connector
architecture makes it straightforward to add new data sources without touching
the core domain.

Curia is built as a **uv workspace monorepo**: a FastAPI REST API, a Celery
background worker, a Next.js frontend, and a set of shared Python packages for
the domain model, ingestion framework, and source-specific connectors.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Monorepo                         │
│                                                         │
│  apps/                                                  │
│  ├── api/          FastAPI REST API (port 8000)         │
│  ├── worker/       Celery background tasks              │
│  └── web/          Next.js frontend  (port 3000)        │
│                                                         │
│  packages/                                              │
│  ├── domain/       Pydantic v2 models + SQLAlchemy ORM  │
│  ├── ingestion/    Crawling & parsing framework         │
│  └── connectors/                                        │
│      └── ibabs/    iBabs municipal portal connector     │
│                                                         │
│  infra/            Dockerfiles (api, worker, web)       │
│  migrations/       Alembic database migrations          │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL 15          Redis 7                         │
└─────────────────────────────────────────────────────────┘
```

Data flows **left → right**:

```
iBabs portals ─► Connector ─► Ingestion ─► Domain/DB ─► API ─► Web
                 (crawl)      (parse)      (store)     (serve)
```

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| [uv](https://docs.astral.sh/uv/) | latest |
| Node.js | 20+ |
| Docker & Docker Compose | latest |

### 1. Clone and install

```bash
git clone https://github.com/<your-org>/Curia.git
cd Curia
cp .env.example .env          # adjust if needed
make install                  # uv sync --all-packages
```

### 2. Start data stores

```bash
make db-up                    # docker compose up -d postgres redis
```

### 3. Run database migrations

```bash
make migrate                  # alembic upgrade head
```

### 4. Start services

```bash
# In separate terminals:
make run-api                  # FastAPI on http://localhost:8000
make run-worker               # Celery worker
make run-web                  # Next.js on http://localhost:3000
```

Or bring up the full stack via Docker:

```bash
make docker-up                # builds & starts all containers
```

---

## Development

### Code quality

```bash
make lint                     # ruff check + format check
make format                   # auto-fix lint issues + format
make typecheck                # mypy
make test                     # pytest
```

### Adding a new connector

1. Create a new package under `packages/connectors/<name>/`.
2. Implement the `SourceConnector` interface from `packages/ingestion/`:
   - `get_meta()` — return connector metadata.
   - `discover_pages(config)` — yield seed URLs.
   - `fetch_page(url, config)` — fetch a single page.
   - `parse_page(content)` — parse raw content into domain entities.
3. Add the package to `[tool.uv.workspace] members` in the root `pyproject.toml`.
4. Register the connector in the worker task configuration.

### Useful Make targets

| Command | Description |
|---------|-------------|
| `make install` | Install all workspace packages |
| `make lint` | Lint with ruff |
| `make format` | Auto-format with ruff |
| `make typecheck` | Type-check with mypy |
| `make test` | Run pytest |
| `make run-api` | Start API server (dev) |
| `make run-worker` | Start Celery worker |
| `make run-web` | Start Next.js dev server |
| `make db-up` / `db-down` | Start / stop Postgres & Redis |
| `make migrate` | Run Alembic migrations |
| `make docker-up` / `docker-down` | Full Docker stack up / down |
| `make clean` | Remove caches and build artifacts |

---

## Project Structure

```
Curia/
├── apps/
│   ├── api/                  # FastAPI application
│   │   └── app/
│   │       ├── main.py       # App factory & lifespan
│   │       ├── config.py     # Pydantic Settings
│   │       ├── dependencies.py
│   │       ├── middleware/    # Request logging
│   │       ├── routers/      # Health + v1 endpoints
│   │       └── schemas/      # Response models
│   ├── worker/               # Celery background worker
│   │   └── app/
│   │       ├── celery_app.py # Celery instance
│   │       ├── config.py
│   │       └── tasks/        # crawl, extraction, normalization, analytics …
│   └── web/                  # Next.js 15 + React 19 + Tailwind
├── packages/
│   ├── domain/               # Shared domain layer
│   │   └── curia_domain/
│   │       ├── models/       # Pydantic v2 value objects
│   │       └── db/           # SQLAlchemy 2.x ORM + session helpers
│   ├── ingestion/            # Crawling & parsing framework
│   │   └── curia_ingestion/
│   │       ├── client.py     # Async HTTP client with retries
│   │       ├── interfaces.py # SourceConnector base class
│   │       ├── rate_limiter.py
│   │       └── retry.py
│   └── connectors/
│       └── ibabs/            # iBabs portal connector
│           └── curia_connectors_ibabs/
│               ├── connector.py
│               ├── mapper.py
│               ├── models/
│               └── parsers/  # BeautifulSoup HTML parsers
├── migrations/               # Alembic (PostgreSQL)
│   └── versions/
├── infra/
│   └── docker/               # Dockerfile.api, .worker, .web
├── .github/workflows/        # CI (lint, typecheck, test, web-lint)
├── docker-compose.yml        # Postgres 15, Redis 7, app services
├── pyproject.toml            # uv workspace root
├── Makefile                  # Developer commands
├── alembic.ini
└── .env.example
```

---

## API Endpoints

All endpoints are served under `/api/v1/`:

| Resource | Path | Description |
|----------|------|-------------|
| Health | `/health` | Liveness check |
| Sources | `/api/v1/sources` | Data source management |
| Institutions | `/api/v1/institutions` | Municipal councils, bodies |
| Politicians | `/api/v1/politicians` | Elected officials |
| Parties | `/api/v1/parties` | Political parties |
| Meetings | `/api/v1/meetings` | Council meetings |
| Agenda Items | `/api/v1/agenda-items` | Meeting agenda items |
| Motions | `/api/v1/motions` | Proposed motions |
| Amendments | `/api/v1/amendments` | Motion amendments |
| Votes | `/api/v1/votes` | Voting records |
| Questions | `/api/v1/questions` | Written questions |
| Promises | `/api/v1/promises` | Political promises |
| Documents | `/api/v1/documents` | Attached documents |
| Metrics | `/api/v1/metrics` | Computed analytics |
| Search | `/api/v1/search` | Full-text search |

---

## Contributing

1. Check the [issue tracker](../../issues) for open tasks.
2. Fork the repo, create a feature branch, and open a PR against `main`.
3. Make sure `make lint`, `make typecheck`, and `make test` pass before requesting review.
4. PRs are validated by CI (ruff, mypy, pytest, Next.js build).

---

## License

Curia is released under the [MIT License](LICENSE).
