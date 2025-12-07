# AI-Driven Personalized Security Awareness Training System
## Project Checklist & Research Objectives

---

## IEEE Paper: Research Breakthrough

### Paper Title (Proposed)
**"Context-Aware AI for Personalized Cybersecurity Training: A Zero-Trust Approach"**

### The Problem We Solve
Traditional Security Awareness Training fails because:
1.  **One-Size-Fits-All**: A Data Engineer on GCP gets the same "Phishing 101" training as a Frontend Developer on AWS.
2.  **Static Content**: Training modules are created once and never adapt to the employee's evolving risk profile.
3.  **Untrusted Data Sources**: In Federated Learning models, there's no guarantee the training data isn't poisoned or the source isn't spoofed.

### Our Breakthrough (The Contribution)
We propose a **Context-Aware Personalization Engine** that:

1.  **Employee Identity from HR (Workday)**: The `workday_id` is the **Primary Key**. All metadata (Git, Jira, IAM) is linked to this ID, ensuring Joe's data is tied to Joe's training—never leaked to Bob.

2.  **Continuous Risk Monitoring**: The system continuously ingests behavioral signals and maintains an up-to-date Risk Profile (0.0 - 1.0) per employee.

3.  **Risk-Driven Training Frequency**: Unlike static annual training, the Risk Score determines HOW OFTEN an employee receives training:
    | Risk Score | Training Frequency |
    |------------|-------------------|
    | 0.0 - 0.3 (Low) | Quarterly |
    | 0.4 - 0.6 (Medium) | Monthly |
    | 0.7 - 1.0 (Critical) | Every Sprint / Urgent |

4.  **LMS Dynamically Updated**: The LMS system (tied to `workday_id`) generates personalized training content via LLM based on the specific risk context AND schedules it according to the frequency tier.

5.  **Zero-Trust Data Provenance (SPIFFE)**: Uses Workload Identity (SVIDs) to guarantee the data feeding the AI is authentic—not spoofed or poisoned.

### Why NOT Federated Learning?
| Federated Learning | Our Approach (Centralized RAG) |
|--------------------|-------------------------------|
| Risk of Model Poisoning | No model training on user data |
| Catastrophic Forgetting | Context injected at inference time |
| Can't verify data source | SPIFFE SVIDs prove data origin |

---

## Project Implementation Checklist

### Phase 1: Infrastructure ✅
- [x] Docker/Kubernetes Setup
- [x] SPIRE Server & Agent Configuration
- [x] Automated SPIRE Workload Registration
- [x] PostgreSQL Database Schema (Users, Risks, Events)
- [x] Dockerfile & Build Script

### Phase 2: Core Engine ✅
- [x] `SPIFFEMTLSHandler` (Certificate Management)
- [x] `BaseSPIFFEAgent` (Service Base Class)
- [x] `Database` Utility (Connection Pooling, Repositories)
- [x] Init Containers for SPIRE Dependency Ordering

### Phase 3: Data Collectors (Simulated) ✅
- [x] Git Collector (Secrets, Force Push, Vulnerabilities)
- [x] Jira Collector (Overdue Security Tickets)
- [x] IAM Collector (AWS/GCP/Azure Privilege Escalation)
- [x] SIEM Collector (Phishing Clicks)

### Phase 4: Intelligence Layer ✅
- [x] Risk Scoring Engine (0-1 Normalization)
- [x] Training Recommender
- [x] LLM Gateway (Gemini 2.5-flash Integration via mTLS)

### Phase 5: Presentation Layer ✅
- [x] Streamlit LMS Dashboard
- [x] User Selector (Switch between users)
- [x] Dynamic Training Modules (Personalized per risk profile)
- [x] mTLS Integration for LLM Calls

### Phase 6: Central Metadata Database & Simulation ✅
- [x] Create User Seeder (50 users, 8 job profiles)
- [x] Historical Data Generator (30 days of events)
- [x] Multi-CSP IAM Events (AWS/GCP/Azure)
- [x] Multi-SIEM Alerts (Splunk/Sentinel/CrowdStrike)
- [x] `run-simulation.sh` (with local fallback)

### Phase 7: Kubernetes Deployment ✅
- [x] Helm Chart: SPIRE Server/Agent
- [x] Helm Chart: SPIRE Registration Job (Auto-discovery)
- [x] Helm Chart: Wait-for-SPIRE RBAC
- [x] Helm Chart: Collectors (Shared Template)
- [x] Helm Chart: Risk Engine
- [x] Helm Chart: LLM Gateway
- [x] Helm Chart: LMS Dashboard
- [x] Helm Chart: PostgreSQL Database (PVC + Service)
- [x] Helm Chart: Secrets (DB password, Gemini API)

### Phase 8: Verification ✅
- [x] Unit Tests (SPIFFEMTLSHandler)
- [x] End-to-End mTLS Verification
- [x] LMS → LLM Gateway → Gemini Integration Working
- [x] User Selection and Personalized Training Verified
- [ ] Dashboard Screenshots for Paper (Final)

---

## Documentation ✅

| Document | Status | Purpose |
|----------|--------|---------|
| README.md | ✅ Updated | Project overview and quick start |
| DEPLOYMENT_ARCHITECTURE.md | ✅ Updated | Complete K8s architecture |
| LESSONS_LEARNED.md | ✅ Created | Challenges & solutions |
| SYNTHETIC_DATA_SPEC.md | ✅ Complete | Data generation specs |
| walkthrough.md | ✅ Updated | Step-by-step deployment |

---

## Key Achievements

1. **Full mTLS Implementation**: All internal services communicate via SPIFFE X.509-SVIDs
2. **Automated SPIRE Registration**: Dynamic agent ID discovery and workload registration
3. **LLM Gateway**: Centralized AI access with API key isolation
4. **Personalized Training**: Risk-based module recommendations using Gemini 2.5-flash
5. **User Selection**: Dashboard allows switching between users for demo purposes

---

## Next Steps (For Paper)
1. Capture final Dashboard Screenshots
2. Run complete simulation for 30-day data generation
3. Document performance metrics
4. Submit IEEE paper
