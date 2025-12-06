# AI-Driven Personalized Security Awareness Training System

An AI-driven system that aggregates user behavior data from multiple enterprise sources, calculates risk profiles, and generates personalized security training.

## Architecture

## Key Innovation: The Context-Aware Personalization Engine

The core contribution of this system is the **Dynamic Risk-Based Personalization Engine**. Unlike static LMS systems, this engine:
1.  **Ingests Real-Time Metadata**: Continuously streams data from Git, Jira, and Cloud IAM.
2.  **Calculates Dynamic Risk**: Updates user risk scores instantly based on behavior (e.g., a committed secret).
3.  **Generates Just-in-Time Content**: Uses Generative AI (Gemini) to create unique training modules tailored to the specific incident.

*Supporting Security Layer*: The system is built on a Zero-Trust foundation using SPIFFE/SPIRE to ensure high-assurance data provenance.

## Research Design Decisions

### Why SPIFFE & Centralized Context? (vs. Federated Learning)
This research proposes a **Context-Aware Retrieval (RAG)** approach over **Federated Learning (FL)** for the following reasons:
1.  **Identity Provenance**: By using SPIFFE (SVIDs), we mathematically guarantee that the data feeding the AI comes from authorized collectors, a critical security requirement often overlooked in FL.
2.  **Centralized Agility**: Updating model weights across distributed employee endpoints (FL) introduces latency and the risk of model poisoning.
3.  **Context isolation**: A centralized LLM Gateway allows us to inject dynamic, user-specific contexts (Git logs + Jira Tickets) at inference time without retraining the model, preventing "Catastrophic Forgetting" or data leakage between users.

## Risk Scoring Model & Identity

Employee identity comes from HR systems (e.g., **Workday**). The `workday_id` is the **Primary Key** linking all behavior data to the correct employee.

### Normalized Risk Score (0.0 - 1.0)
The Risk Score determines **Training Frequency**, not just content:

| Risk Score | Level | Training Frequency |
|------------|-------|-------------------|
| 0.0 - 0.3 | Low | Quarterly |
| 0.4 - 0.6 | Medium | Monthly |
| 0.7 - 1.0 | Critical | Every Sprint / Urgent |

The LMS (tied to `workday_id`) is continuously updated with risk data and schedules personalized training at the appropriate frequency.

## Project Structure

- `collectors/`: Data collectors (Git, Jira, IAM, SIEM)
- `engine/`: Risk scoring and training recommendation engine
- `gateway/`: LLM Gateway service
- `lms/`: Streamlit Learning Management System
- `configs/`: SPIRE configuration
- `helm/`: Kubernetes deployment charts

## Getting Started

1. **Setup Environment**:
   ```bash
   chmod +x scripts/setup-dev.sh
   ./scripts/setup-dev.sh
   ```

2. **Run Locally**:
    See `scripts/README.md` for local development instructions.

## Deployment

For detailed Kubernetes deployment architecture, see:
- [DEPLOYMENT_ARCHITECTURE.md](./DEPLOYMENT_ARCHITECTURE.md) - Complete K8s connectivity diagram
- [PROJECT_CHECKLIST.md](./PROJECT_CHECKLIST.md) - Implementation status
- [walkthrough.md](./walkthrough.md) - Step-by-step deployment guide
