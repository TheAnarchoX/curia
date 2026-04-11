# Infrastructure & Deployment Architecture

> Companion to [SPEC.md § 8](../../SPEC.md). This document expands on the
> infrastructure strategy with concrete configuration examples, cost estimates,
> and decision frameworks.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Caddy Reverse Proxy](#2-caddy-reverse-proxy)
3. [Terraform Resource Planning](#3-terraform-resource-planning)
4. [Docker Compose Production Overlay](#4-docker-compose-production-overlay)
5. [CI/CD Pipeline](#5-cicd-pipeline)
6. [Monitoring Stack](#6-monitoring-stack)
7. [Backup Strategy](#7-backup-strategy)
8. [Cost Estimates](#8-cost-estimates)
9. [When to Move from Docker Compose to Kubernetes](#9-when-to-move-from-docker-compose-to-kubernetes)

---

## 1. Architecture Overview

```
                          Internet
                             │
                    ┌────────▼────────┐
                    │   Cloudflare    │
                    │  DNS · CDN · WAF│
                    └────────┬────────┘
                             │ HTTPS (proxied)
               ┌─────────────▼─────────────────────────┐
               │  Hetzner Cloud VPC  (eu-central, fsn1) │
               │                                        │
               │  ┌──────────────────────────────────┐  │
               │  │  Caddy  (reverse proxy, auto TLS)│  │
               │  │  :80 → redirect → :443           │  │
               │  └──────┬──────────────┬────────────┘  │
               │         │              │               │
               │  ┌──────▼──────┐ ┌─────▼───────────┐  │
               │  │   Next.js   │ │   FastAPI        │  │
               │  │   :3000     │ │   :8000          │  │
               │  └─────────────┘ └──────┬───────────┘  │
               │                         │              │
               │                  ┌──────▼───────────┐  │
               │                  │  Celery Workers   │  │
               │                  └──────┬───────────┘  │
               │                         │              │
               │  ┌──────────────────────▼───────────┐  │
               │  │  PostgreSQL :5432 · Redis :6379   │  │
               │  └──────────────────────────────────┘  │
               └────────────────────────────────────────┘
```

**Key principles:**

- All traffic enters through Cloudflare; the Hetzner server's IP is not exposed
  publicly.
- Caddy handles TLS termination (certificates from Let's Encrypt or Cloudflare
  origin certs).
- Services communicate over Docker's internal network (never exposed to the
  host).
- PostgreSQL and Redis are not publicly accessible — only reachable within the
  VPC / Docker network.

---

## 2. Caddy Reverse Proxy

### Why Caddy

- **Automatic HTTPS** — obtains and renews Let's Encrypt certificates with zero
  configuration.
- **Simple Caddyfile** — far less boilerplate than Nginx or Traefik.
- **HTTP/3** — built-in QUIC support.
- **Health checks** — native upstream health checking.

### Example Caddyfile

```caddyfile
{
    # Global options
    email admin@curia.nl
    acme_ca https://acme-v02.api.letsencrypt.org/directory
}

curia.nl {
    # Frontend — Next.js
    handle /* {
        reverse_proxy nextjs:3000
    }

    # API — FastAPI
    handle /api/* {
        reverse_proxy api:8000
    }

    # OpenAPI docs
    handle /docs {
        reverse_proxy api:8000
    }
    handle /redoc {
        reverse_proxy api:8000
    }
    handle /openapi.json {
        reverse_proxy api:8000
    }

    # Static asset caching headers (Cloudflare will respect these)
    header /_next/static/* Cache-Control "public, max-age=31536000, immutable"

    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
    }

    # Access log
    log {
        output file /var/log/caddy/access.log
        format json
    }
}
```

### Cloudflare Integration

When using Cloudflare in **Full (Strict)** SSL mode:

1. Generate a Cloudflare Origin Certificate in the dashboard.
2. Mount the cert/key into the Caddy container.
3. Use `tls /etc/caddy/origin.pem /etc/caddy/origin-key.pem` in the Caddyfile
   instead of ACME.

Alternatively, keep Caddy's ACME with Cloudflare DNS challenge using the
`caddy-dns/cloudflare` plugin if you want Caddy to manage its own certificates.

---

## 3. Terraform Resource Planning

### Directory Structure

```
infra/
  terraform/
    main.tf              # Root module — wires environments to modules
    variables.tf         # Shared variable declarations
    outputs.tf           # Root outputs
    versions.tf          # Required providers and versions
    environments/
      staging/
        main.tf          # Module calls with staging values
        terraform.tfvars # Staging-specific variables
        backend.tf       # Remote state config (staging bucket)
      production/
        main.tf          # Module calls with production values
        terraform.tfvars # Production-specific variables
        backend.tf       # Remote state config (production bucket)
    modules/
      hetzner-server/
        main.tf          # hcloud_server, hcloud_firewall, hcloud_ssh_key
        variables.tf
        outputs.tf
      cloudflare-dns/
        main.tf          # cloudflare_record (A, AAAA, CNAME)
        variables.tf
        outputs.tf
      postgres/
        main.tf          # Database provisioning (managed or self-hosted)
        variables.tf
        outputs.tf
      caddy/
        main.tf          # Caddy configuration file provisioning
        variables.tf
        outputs.tf
```

### Hetzner Resources (Stage 1)

```hcl
# modules/hetzner-server/main.tf

resource "hcloud_ssh_key" "deploy" {
  name       = "curia-deploy"
  public_key = var.ssh_public_key
}

resource "hcloud_firewall" "web" {
  name = "curia-web"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = var.ssh_allowed_ips
  }
}

resource "hcloud_server" "app" {
  name        = "curia-${var.environment}"
  server_type = var.server_type   # "cx32" for staging, "cx42" for prod
  image       = "ubuntu-24.04"
  location    = "fsn1"            # Falkenstein, Germany (EU)

  ssh_keys    = [hcloud_ssh_key.deploy.id]
  firewall_ids = [hcloud_firewall.web.id]

  labels = {
    project     = "curia"
    environment = var.environment
  }

  user_data = file("${path.module}/cloud-init.yml")
}
```

### Cloudflare DNS

```hcl
# modules/cloudflare-dns/main.tf

resource "cloudflare_record" "root" {
  zone_id = var.cloudflare_zone_id
  name    = "@"
  content = var.server_ipv4
  type    = "A"
  proxied = true    # Traffic routes through Cloudflare CDN
}

resource "cloudflare_record" "www" {
  zone_id = var.cloudflare_zone_id
  name    = "www"
  content = var.domain
  type    = "CNAME"
  proxied = true
}

resource "cloudflare_record" "staging" {
  zone_id = var.cloudflare_zone_id
  name    = "staging"
  content = var.staging_server_ipv4
  type    = "A"
  proxied = true
}
```

### Remote State

Terraform state is stored in Hetzner Object Storage (S3-compatible) or
Terraform Cloud:

```hcl
# environments/production/backend.tf

terraform {
  backend "s3" {
    bucket   = "curia-terraform-state"
    key      = "production/terraform.tfstate"
    region   = "eu-central"
    endpoint = "https://fsn1.your-objectstorage.com"  # Replace with actual Hetzner S3 endpoint

    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
  }
}
```

---

## 4. Docker Compose Production Overlay

The project uses a **base + overlay** pattern. The base `docker-compose.yml`
defines all services for local development. A production overlay adds
production-specific settings.

### docker-compose.prod.yml

```yaml
# Production overlay — use with:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"   # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api
      - nextjs

  api:
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql+asyncpg://curia:${DB_PASSWORD}@postgres:5432/curia
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    deploy:
      resources:
        limits:
          memory: 1G

  worker:
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql+asyncpg://curia:${DB_PASSWORD}@postgres:5432/curia
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    deploy:
      resources:
        limits:
          memory: 2G

  nextjs:
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://curia.nl/api
    deploy:
      resources:
        limits:
          memory: 512M

  postgres:
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    deploy:
      resources:
        limits:
          memory: 2G
    # Not exposed to host — only accessible via Docker network
    ports: !reset []

  redis:
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    ports: !reset []

volumes:
  caddy_data:
  caddy_config:
  postgres_data:
  redis_data:
```

### Deployment Command

```bash
# On the server, after pulling the latest images:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --pull always
```

---

## 5. CI/CD Pipeline

### Pipeline Overview

```
Push to main
     │
     ▼
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐
│  Lint &      │───▶│  Build Docker │───▶│  Push to GHCR  │───▶│  Deploy via │
│  Typecheck   │    │  images       │    │  (GitHub       │    │  SSH        │
│  & Test      │    │               │    │   Container    │    │             │
│              │    │               │    │   Registry)    │    │             │
└─────────────┘    └──────────────┘    └───────────────┘    └─────────────┘
```

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml  (conceptual — implement when ready)

name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    # Existing CI job (lint, typecheck, test)
    uses: ./.github/workflows/ci.yml

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push API image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: apps/api/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/api:latest

      - name: Build and push worker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: apps/worker/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/worker:latest

      - name: Build and push web image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: apps/web/Dockerfile
          push: true
          tags: ghcr.io/${{ github.repository }}/web:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: deploy
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/curia
            docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
            docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
            docker image prune -f
```

### Staging Deployments

Pull requests deploy to a staging environment automatically. The staging
workflow mirrors production but targets `staging.curia.nl`.

---

## 6. Monitoring Stack

### Recommended Approach by Stage

| Stage | Monitoring | Why |
|-------|-----------|-----|
| Stage 1 (single server) | **Uptime Kuma** + Docker log driver | Minimal overhead, simple alerting |
| Stage 2 (multi-service) | **Prometheus + Grafana + Loki** | Multi-server visibility, log aggregation |
| Stage 3 (k8s) | Prometheus Operator + Grafana + Loki | Kubernetes-native, autoscaled |

### Stage 1: Uptime Kuma + Loki

```yaml
# Add to docker-compose.prod.yml for Stage 1 monitoring

services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    volumes:
      - uptime_kuma_data:/app/data
    ports:
      - "3001:3001"
    # Protected behind Caddy with basic auth

  loki:
    image: grafana/loki:2.9.0
    restart: unless-stopped
    volumes:
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml

volumes:
  uptime_kuma_data:
  loki_data:
```

**Uptime Kuma** monitors:

- `https://curia.nl` — frontend availability
- `https://curia.nl/api/v1/health` — API health endpoint
- PostgreSQL and Redis connectivity (TCP checks)
- SSL certificate expiry

**Loki** collects container logs via the Docker logging driver, providing
centralised log search without the overhead of Elasticsearch.

### Stage 2: Prometheus + Grafana

Add Prometheus for metrics collection, Grafana for dashboards:

- **FastAPI metrics**: expose via `prometheus-fastapi-instrumentator`
- **PostgreSQL metrics**: `postgres_exporter`
- **Redis metrics**: `redis_exporter`
- **Node metrics**: `node_exporter` for server-level CPU/memory/disk
- **Celery metrics**: `celery-exporter` for task success/failure rates

Key alerts:

- API response time P95 > 500ms
- Error rate > 1%
- Disk usage > 80%
- PostgreSQL connection pool exhaustion
- Celery task queue depth > 100
- SSL certificate expiry < 14 days

---

## 7. Backup Strategy

### PostgreSQL Backups

```bash
#!/usr/bin/env bash
# scripts/backup-postgres.sh
# Run daily via cron: 0 3 * * * /opt/curia/scripts/backup-postgres.sh

set -euo pipefail

BACKUP_DIR="/opt/curia/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/curia_${TIMESTAMP}.sql.gz"

# Create backup directory if needed
mkdir -p "${BACKUP_DIR}"

# Dump and compress
docker compose exec -T postgres pg_dump -U curia curia | gzip > "${BACKUP_FILE}"

# Upload to Hetzner Object Storage (S3-compatible)
aws s3 cp "${BACKUP_FILE}" \
  s3://curia-backups/postgres/${TIMESTAMP}.sql.gz \
  --endpoint-url https://fsn1.your-objectstorage.com

# Retain local backups for 7 days
find "${BACKUP_DIR}" -name "curia_*.sql.gz" -mtime +7 -delete
```

### Backup Schedule

| What | How | Frequency | Retention |
|------|-----|-----------|-----------|
| PostgreSQL full dump | `pg_dump` → gzip → Hetzner Object Storage | Daily at 03:00 UTC | 30 days |
| PostgreSQL WAL archiving | Continuous archiving (Stage 2+) | Continuous | 7 days |
| Redis RDB snapshot | Automatic (appendonly + RDB) | Hourly | 7 days on disk |
| Docker volumes | `tar` → Hetzner Object Storage | Weekly | 4 weeks |
| Terraform state | Remote backend (auto-versioned) | Every apply | All versions |

### Restore Procedure

```bash
# Restore from a specific backup
gunzip -c curia_20250101_030000.sql.gz | \
  docker compose exec -T postgres psql -U curia curia
```

---

## 8. Cost Estimates

### Stage 1 — Single Server (MVP)

| Resource | Spec | Monthly Cost |
|----------|------|-------------|
| Hetzner CX32 | 4 vCPU, 8 GB RAM, 80 GB SSD | ~€8 |
| Hetzner CX42 (if needed) | 8 vCPU, 16 GB RAM, 160 GB SSD | ~€15 |
| Cloudflare | Free tier (DNS, CDN, basic WAF) | €0 |
| Domain (curia.nl) | .nl registration | ~€8/year |
| Hetzner Object Storage | 100 GB for backups | ~€3 |
| **Total (CX32)** | | **~€11/month** |
| **Total (CX42)** | | **~€18/month** |

### Stage 2 — Multi-Service

| Resource | Spec | Monthly Cost |
|----------|------|-------------|
| Hetzner CX42 × 2 | API + workers | ~€30 |
| Hetzner managed PostgreSQL (CPX21) | 3 vCPU, 4 GB | ~€15 |
| Hetzner Load Balancer | LB11 | ~€6 |
| Hetzner Object Storage | 500 GB | ~€12 |
| Cloudflare | Free tier | €0 |
| **Total** | | **~€63/month** |

### Stage 3 — Kubernetes

| Resource | Spec | Monthly Cost |
|----------|------|-------------|
| k3s nodes × 3–5 | CX32–CX42 | ~€40–€75 |
| Managed PostgreSQL | CPX31 | ~€25 |
| Load Balancer | LB11 | ~€6 |
| Object Storage | 1 TB | ~€24 |
| Monitoring (Grafana Cloud or self-hosted) | — | €0–€30 |
| **Total** | | **~€95–€160/month** |

> **Comparison:** equivalent AWS infrastructure for Stage 1 would cost
> ~€60–€100/month. Hetzner saves 5–10× on compute while remaining fully
> GDPR-compliant.

---

## 9. When to Move from Docker Compose to Kubernetes

### Decision Framework

Docker Compose is the right choice when:

- ✅ Single server handles the load
- ✅ Team is small (1–3 developers)
- ✅ Deploys happen infrequently (a few times per week)
- ✅ No need for zero-downtime deployments
- ✅ Fewer than ~5 service replicas

Consider Kubernetes (k3s) when **two or more** of these are true:

- ⚠️ You need horizontal auto-scaling (traffic spikes)
- ⚠️ You have >10 service replicas across multiple nodes
- ⚠️ You need blue-green or canary deployments
- ⚠️ Multiple teams are deploying independently
- ⚠️ You need built-in service discovery and load balancing across many services

### Migration Path

```
Docker Compose (single server)
        │
        ▼  Traffic exceeds single server capacity
Docker Compose (multi-server with Hetzner LB)
        │
        ▼  Need auto-scaling, complex orchestration
k3s on Hetzner Cloud
        │
        ▼  Enterprise scale (unlikely near-term)
Managed Kubernetes
```

### What to Prepare Now

Even while using Docker Compose, these practices make a future migration
smoother:

1. **Health checks** on all services (already required by Compose `healthcheck`).
2. **Environment variables** for all configuration (12-factor app).
3. **Stateless services** — no local file storage in API or workers.
4. **Container images in a registry** (GHCR) — not built on the server.
5. **Terraform managing infrastructure** — adding k8s nodes is just a module
   change.

---

## References

- [Hetzner Cloud pricing](https://www.hetzner.com/cloud/)
- [Caddy documentation](https://caddyserver.com/docs/)
- [Cloudflare DNS setup](https://developers.cloudflare.com/dns/)
- [Terraform Hetzner provider](https://registry.terraform.io/providers/hetznercloud/hcloud/latest)
- [Docker Compose production guide](https://docs.docker.com/compose/production/)
