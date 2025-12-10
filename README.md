# AI-Driven Personalized Security Awareness Training System

A zero-trust AI-driven system that aggregates user behavior data from enterprise sources, calculates dynamic risk profiles, and generates personalized security training using mTLS/SPIFFE authentication.

## 🏆 Key Features

- **Zero-Trust Architecture**: All internal communication secured with mTLS using SPIFFE X.509-SVIDs
- **Dynamic Risk Assessment**: Real-time risk scoring based on Git, IAM, and SIEM activity
- **AI-Personalized Training**: Gemini-powered training modules tailored to individual risk profiles
- **User Selection**: Dashboard allows switching between users to view personalized content

## 🏗 Architecture

```
┌─────────────┐       mTLS          ┌─────────────┐      HTTPS      ┌──────────┐
│    LMS      │ ─────────────────► │ LLM Gateway │ ──────────────► │  Gemini  │
│  (SPIFFE)   │  SPIFFE X.509      │  (SPIFFE)   │   API Key       │   API    │
└─────────────┘                     └─────────────┘                 └──────────┘

┌──────────────┐       mTLS         ┌─────────────┐       SQL       ┌──────────┐
│  Collectors  │ ─────────────────► │ Risk Scorer │ ──────────────► │ Postgres │
│  (SPIFFE)    │  SPIFFE X.509      │  (SPIFFE)   │                 │    DB    │
└──────────────┘                    └─────────────┘                 └──────────┘
```

## 🔬 Research Design

### Why SPIFFE & Centralized Context?

1. **Identity Provenance**: SPIFFE SVIDs mathematically guarantee data comes from authorized collectors
2. **Zero-Trust Security**: Every service authenticates with cryptographic identity
3. **Context Isolation**: Centralized LLM Gateway prevents data leakage between users

### Risk Scoring Model

| Risk Score | Level | Training Frequency |
|------------|-------|-------------------|
| 0.0 - 0.3 | Low | Quarterly |
| 0.4 - 0.6 | Medium | Monthly |
| 0.7 - 1.0 | Critical | Every Sprint |

## 📁 Project Structure

```
personalized-cyber/
├── src/
│   ├── base/spiffe_agent.py     # mTLS + BaseSPIFFEAgent class
│   ├── collectors/              # Git, Jira, IAM, SIEM collectors
│   ├── engine/risk_scorer.py    # Risk calculation engine
│   ├── gateway/llm_gateway.py   # Gemini API gateway (mTLS)
│   └── lms/app.py               # Streamlit dashboard
├── helm/security-training/      # Kubernetes deployment
├── database/schema.sql          # PostgreSQL schema
└── scripts/                     # Build and deployment scripts
```

## 🚀 Quick Start

### Prerequisites
- Docker Desktop with Kubernetes enabled
- Helm 3.x
- Gemini API key

### Deploy

```bash
# 1. Build Docker image
docker build -t security-training-app:latest .

# 2. Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"

# 3. Deploy with Helm
helm install security-system ./helm/security-training \
  --set global.geminiApiKey=$GEMINI_API_KEY

# 4. Wait for pods to be ready
kubectl get pods -n security-training -w

# 5. Port forward to access LMS
kubectl port-forward svc/lms 8080:8080 -n security-training

# 6. Open browser
open http://localhost:8080
```

The system automatically:
1. Creates PostgreSQL database with PVC (persistent storage)
2. Seeds 50 users with IEEE paper role distribution (12 Backend Devs, 4 DevSecOps, 3 Security Analysts, etc.)
3. Generates 30 days of behavioral events (Git, Jira, IAM, SIEM)
4. Calculates risk scores using the threshold-normalized formula

## 🔬 IEEE Paper Reproducibility

This system is designed for reproducible research. On fresh deployment:

### Automated Data Seeding
The `ieee-data-seeder` Kubernetes Job runs automatically after Helm install and generates:

| Data Type | Count | Description |
|-----------|-------|-------------|
| Users | 50 | 8 role types (Backend Dev, DevSecOps, Security Analyst, etc.) |
| Git Events | ~15,000 | Commits, force pushes, secret detection |
| IAM Events | ~3,500 | AWS/GCP/Azure privileged actions |
| SIEM Alerts | ~200 | Phishing, malware, policy violations |
| Jira Events | ~900 | Security tickets, overdue tasks |
| Training Records | ~200 | Module completions with scores |

### Reproducible Random Seeds
Data generation uses fixed seeds (`Faker.seed(42)`, `random.seed(42)`) ensuring identical datasets across deployments.

### Expected Risk Distribution
After seeding:
- **High Risk (≥0.7)**: ~28 users (Backend Devs, DevOps, Data Engineers)
- **Medium Risk (0.3-0.7)**: ~15 users (Frontend, Data Analysts)
- **Low Risk (<0.3)**: ~7 users (DevSecOps, Security Analysts - control group)

### Re-seeding Data
```bash
# Delete the job and PVC to reseed
kubectl delete job ieee-data-seeder -n security-training
kubectl delete pvc postgres-pvc -n security-training
helm upgrade security-system ./helm/security-training
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [DEPLOYMENT_ARCHITECTURE.md](./DEPLOYMENT_ARCHITECTURE.md) | Complete Kubernetes architecture |
| [LESSONS_LEARNED.md](./LESSONS_LEARNED.md) | Challenges & solutions (SPIRE, mTLS, Gemini) |
| [SYNTHETIC_DATA_SPEC.md](./SYNTHETIC_DATA_SPEC.md) | Simulation data specifications |
| [PROJECT_CHECKLIST.md](./PROJECT_CHECKLIST.md) | Implementation status |

## 🔧 Development

### Local Testing
```bash
# Setup development environment
./scripts/setup-dev.sh

# Run with Docker Compose (local dev only)
docker-compose up -d
```

### Rebuild After Changes
```bash
docker build -t security-training-app:latest .
kubectl delete pod -n security-training -l app=lms
kubectl delete pod -n security-training -l app=llm-gateway
```

## 🛡 Security Features

- **mTLS Authentication**: All services use SPIFFE X.509 certificates
- **API Key Isolation**: Only LLM Gateway has access to Gemini API key
- **SPIRE Integration**: Automated workload registration and certificate rotation
- **Zero-Trust**: No implicit trust between services

## 📊 LMS Dashboard Features

1. **User Selection**: Switch between users to view their risk profiles
2. **Risk Dashboard**: View overall, Git, and IAM risk scores
3. **Personalized Training**: AI-generated modules based on risk profile
4. **Team View**: Organization-wide risk overview

## 📝 License

MIT License - See LICENSE file for details.
