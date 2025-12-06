# Deep Architecture Audit Report

## Files and Their Purposes

### docker-compose.yml
**Purpose**: Local development ONLY
- Runs PostgreSQL database on your laptop
- NOT used in Kubernetes deployment
- Use when testing locally without Docker Desktop Kubernetes

### Dockerfile
**Purpose**: Builds the application Docker image
- Contains ALL Python code (baked in)
- Used by Kubernetes deployments
- Build with: `./scripts/build.sh`

---

## How Services Connect in Kubernetes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER (Docker Desktop)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                │
│  │ SPIRE Server │────▶│ SPIRE Agent  │────▶│   ALL PODS   │                │
│  │  (StatefulSet)│     │  (DaemonSet) │     │ Get SVIDs    │                │
│  └──────────────┘     └──────────────┘     └──────────────┘                │
│                                                                              │
│  ┌──────────────┐                                                            │
│  │  PostgreSQL  │◀────── Service: postgres-svc:5432                         │
│  │    (Pod)     │        All pods connect here via mTLS                     │
│  │  + PVC + CM  │        (K8s internal DNS resolution)                      │
│  └──────────────┘                                                            │
│         ▲                                                                    │
│         │ DB_HOST=postgres-svc                                               │
│         │                                                                    │
│  ┌──────┴───────┬─────────────┬─────────────┬─────────────┐                │
│  │ Git Collector│Jira Collector│IAM Collector│SIEM Collector│               │
│  └──────────────┴─────────────┴─────────────┴─────────────┘                │
│         │                                                                    │
│         ▼ Write Events                                                       │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ Risk Scorer  │────▶│ LLM Gateway  │────▶ External: Gemini API           │
│  └──────────────┘     └──────────────┘                                      │
│         │                      │                                             │
│         ▼                      ▼                                             │
│  ┌──────────────────────────────────┐                                       │
│  │         LMS Dashboard             │◀──── kubectl port-forward 8080       │
│  │        (Streamlit Pod)            │                                       │
│  └──────────────────────────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Database Connectivity (CRITICAL)

**Question**: How do pods connect to the database?

**Answer**: Via Kubernetes Service DNS

```yaml
# In each deployment's env:
- name: DB_HOST
  value: "postgres-svc"  # K8s resolves this to PostgreSQL Pod IP
- name: DB_PORT
  value: "5432"
```

**Flow**:
1. Helm creates PostgreSQL Pod + Service (`postgres-svc`)
2. K8s DNS automatically resolves `postgres-svc` → Pod IP
3. All collectors/engine/LMS use `DB_HOST=postgres-svc`
4. Connection is internal to cluster (no external exposure)

---

## Complete Kubernetes Manifest List

| Template | Creates | Purpose |
|----------|---------|---------|
| `spire/server-*.yaml` | StatefulSet, ConfigMap, Service | SPIRE identity server |
| `spire/agent-*.yaml` | DaemonSet, ConfigMap | SPIFFE agent on each node |
| `database/postgres.yaml` | PVC, ConfigMap, Deployment, Service | PostgreSQL database |
| `collectors/deployment.yaml` | 4x Deployment, 4x Service, 4x SA | Git/Jira/IAM/SIEM collectors |
| `engine/deployment.yaml` | Deployment, Service, SA | Risk Scorer |
| `gateway/deployment.yaml` | Deployment, Service, SA | LLM Gateway |
| `lms/deployment.yaml` | Deployment, Service, SA | Streamlit Dashboard |
| `secrets.yaml` | Secrets | DB password, Gemini API key |

---

## mTLS Verification

**All internal communication uses mTLS**:
- Each pod gets SVID from SPIRE Agent (via Unix socket)
- Server wraps socket with SSL (`verify_mode = CERT_REQUIRED`)
- Client presents certificate on every request
- SPIFFE ID extracted for authorization

**Code location**: `src/base/spiffe_agent.py`

---

## Project Structure (Actual)

```
personalized-cyber/
├── README.md                    # Project overview
├── PROJECT_CHECKLIST.md         # Implementation status
├── DEPLOYMENT_ARCHITECTURE.md   # This audit document
├── LMS_PROJECT_CONTEXT.md       # Original design context
├── walkthrough.md               # Deployment steps
│
├── docker-compose.yml           # LOCAL DEV ONLY
├── Dockerfile                   # Application image
├── requirements.txt             # Python dependencies
│
├── src/
│   ├── base/                    # Shared code
│   │   ├── spiffe_agent.py      # mTLS + Base Agent class
│   │   ├── database.py          # DB connection + repositories
│   │   └── spiffe_handler.py    # Certificate management
│   │
│   ├── collectors/              # Data collectors (SPIFFE Agents)
│   │   ├── git_collector.py
│   │   ├── jira_collector.py
│   │   ├── iam_collector.py
│   │   └── siem_collector.py
│   │
│   ├── engine/                  # Business logic
│   │   ├── risk_scorer.py       # 0-1 Risk calculation
│   │   └── training_recommender.py
│   │
│   ├── gateway/                 # External API wrapper
│   │   └── gateway.py           # Gemini LLM calls
│   │
│   ├── lms/                     # User interface
│   │   └── app.py               # Streamlit dashboard
│   │
│   └── utils/                   # Simulation scripts
│       ├── historical_data_generator.py  # 30 days of fake data
│       └── simulation_seeder.py          # Legacy seeder
│
├── database/
│   └── schema.sql               # PostgreSQL schema
│
├── helm/security-training/      # Kubernetes deployment
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── database/            # PostgreSQL
│       ├── spire/               # Identity infrastructure
│       ├── collectors/          # Data collectors
│       ├── engine/              # Risk scorer
│       ├── gateway/             # LLM gateway
│       ├── lms/                 # Dashboard
│       └── secrets.yaml         # Credentials
│
├── scripts/
│   ├── build.sh                 # Docker build
│   ├── run-simulation.sh        # Generate fake data
│   └── setup-dev.sh             # Local Python env
│
└── tests/
    └── test_spiffe_handler.py   # Unit tests
```
