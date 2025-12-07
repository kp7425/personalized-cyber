# Deployment Architecture

## Overview

This document describes the zero-trust security training platform architecture deployed on Kubernetes with full mTLS using SPIFFE/SPIRE.

---

## System Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │              Kubernetes Cluster              │
                          │                                             │
┌──────────┐   mTLS      │  ┌─────────────┐         ┌─────────────┐   │
│   User   │ ◄──────────────│    LMS      │──mTLS──►│ LLM Gateway │   │
│ Browser  │             │  │  (SPIFFE)   │         │  (SPIFFE)   │   │
└──────────┘             │  └─────────────┘         └──────┬──────┘   │
                          │         │                       │          │
                          │         │                       │ HTTPS    │
                          │         ▼                       ▼          │
                          │  ┌─────────────┐         ┌──────────────┐  │
                          │  │  PostgreSQL │         │  Gemini API  │  │
                          │  │  (Database) │         │   (Google)   │  │
                          │  └─────────────┘         └──────────────┘  │
                          │                                             │
                          │  ┌─────────────┐   mTLS  ┌─────────────┐   │
                          │  │ Collectors  │◄───────►│ Risk Scorer │   │
                          │  │  (SPIFFE)   │         │  (SPIFFE)   │   │
                          │  └─────────────┘         └─────────────┘   │
                          │                                             │
                          │  ┌─────────────────────────────────────┐   │
                          │  │         SPIRE (Trust Domain)         │   │
                          │  │  ┌──────────┐      ┌──────────┐      │   │
                          │  │  │  Server  │◄────►│  Agent   │      │   │
                          │  │  └──────────┘      └──────────┘      │   │
                          │  └─────────────────────────────────────┘   │
                          └─────────────────────────────────────────────┘
```

---

## Components

### SPIRE Infrastructure
| Component | Type | Purpose |
|-----------|------|---------|
| spire-server | StatefulSet | Issues and manages SPIFFE identities |
| spire-agent | DaemonSet | Provides X.509 certificates to workloads |
| spire-register-workloads | Job | Automates workload registration |

### Core Services
| Service | Port | SPIFFE ID | Purpose |
|---------|------|-----------|---------|
| LMS | 8080 | spiffe://.../lms | Streamlit dashboard |
| LLM Gateway | 8520 | spiffe://.../llm-gateway | Gemini API proxy |
| Risk Scorer | 8510 | spiffe://.../risk-scorer | Risk calculation engine |
| Git Collector | 8501 | spiffe://.../git-collector | Git activity collection |
| Jira Collector | 8502 | spiffe://.../jira-collector | Jira activity collection |
| IAM Collector | 8503 | spiffe://.../iam-collector | IAM events collection |
| SIEM Collector | 8504 | spiffe://.../siem-collector | Security events collection |

### Database
| Component | Purpose |
|-----------|---------|
| PostgreSQL | User data, risk profiles, training records |

---

## mTLS Communication Flow

### LMS → LLM Gateway
```
1. LMS initializes SPIFFEMTLSHandler (gets X.509-SVID from SPIRE Agent)
2. LMS makes HTTPS request to llm-gateway-svc:8520
3. Gateway validates LMS certificate against allowed_callers
4. Gateway calls Gemini API with internal API key
5. Response returned via mTLS
```

### Collectors → Risk Scorer
```
1. Collector POSTs behavioral data to risk-scorer-svc:8510
2. Risk Scorer validates collector certificate
3. Data processed and risk scores calculated
4. Results stored in PostgreSQL
```

---

## Kubernetes Resources

| Template | Creates | Purpose |
|----------|---------|---------|
| `spire/server.yaml` | StatefulSet, Service, ConfigMap, ClusterRole | SPIRE server |
| `spire/agent.yaml` | DaemonSet, ConfigMap, ClusterRole | SPIRE agent |
| `spire/registration-job.yaml` | Job | Auto-registers workloads |
| `database/postgres.yaml` | Deployment, Service, PVC, ConfigMap | PostgreSQL |
| `collectors/deployment.yaml` | 4x Deployments | Data collectors |
| `engine/deployment.yaml` | Deployment, Service | Risk scorer |
| `gateway/deployment.yaml` | Deployment, Service | LLM gateway |
| `lms/deployment.yaml` | Deployment, Service | Dashboard |
| `secrets.yaml` | Secrets | API keys, DB credentials |

---

## Environment Variables

### All Services
```yaml
- SPIFFE_ENDPOINT_SOCKET: unix:///opt/spire/sockets/agent.sock
- TRUST_DOMAIN: security-training.example.org
```

### Database Access
```yaml
- DB_HOST: postgres-svc
- DB_PORT: "5432"
- DB_NAME: security_training
```

### LLM Gateway
```yaml
- LLM_BACKEND: gemini
- GEMINI_MODEL: gemini-2.5-flash
- GEMINI_API_KEY: (from secret)
```

---

## Deployment Steps

```bash
# 1. Build Docker image
docker build -t security-training-app:latest .

# 2. Deploy with Helm
helm install security-system ./helm/security-training \
  --set global.geminiApiKey=$GEMINI_API_KEY

# 3. Wait for pods
kubectl get pods -n security-training -w

# 4. Port forward to access LMS
kubectl port-forward svc/lms 8080:8080 -n security-training

# 5. Open browser
open http://localhost:8080
```

---

## Project Structure

```
personalized-cyber/
├── src/
│   ├── base/
│   │   ├── spiffe_agent.py      # mTLS + BaseSPIFFEAgent class
│   │   └── database.py          # PostgreSQL connection
│   ├── collectors/              # Git, Jira, IAM, SIEM collectors
│   ├── engine/risk_scorer.py    # Risk calculation
│   ├── gateway/llm_gateway.py   # Gemini API gateway
│   └── lms/app.py               # Streamlit dashboard
│
├── helm/security-training/
│   ├── templates/
│   │   ├── spire/               # SPIRE server + agent + registration
│   │   ├── database/            # PostgreSQL
│   │   ├── collectors/          # Data collectors
│   │   ├── engine/              # Risk scorer
│   │   ├── gateway/             # LLM gateway
│   │   └── lms/                 # Dashboard
│   └── values.yaml              # Configuration
│
├── LESSONS_LEARNED.md           # Implementation challenges & solutions
├── DEPLOYMENT_ARCHITECTURE.md   # This document
└── SYNTHETIC_DATA_SPEC.md       # Data generation specifications
```

---

## Security Features

1. **Zero-Trust Architecture**: Every service authenticates with SPIFFE X.509 certificates
2. **mTLS Everywhere**: All internal communication is encrypted and authenticated
3. **API Key Isolation**: Only LLM Gateway has access to Gemini API key
4. **Personalized Training**: Content tailored to individual risk profiles
5. **Audit Trail**: All risk assessments and training completions logged

---

## Troubleshooting

### SPIRE Issues
```bash
# Check SPIRE server
kubectl logs -n security-training deploy/spire-server

# Check SPIRE agent
kubectl logs -n security-training daemonset/spire-agent

# View registered entries
kubectl exec -n security-training deploy/spire-server -- \
  /opt/spire/bin/spire-server entry show
```

### mTLS Issues
```bash
# Check if certificates are being fetched
kubectl logs -n security-training -l app=lms | grep -i spiffe

# Check LLM Gateway
kubectl logs -n security-training -l app=llm-gateway
```

See `LESSONS_LEARNED.md` for detailed troubleshooting scenarios.
