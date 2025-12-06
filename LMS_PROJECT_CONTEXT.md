# AI-Driven Personalized Security Awareness Training System

## Project Context Document
**Created:** December 5, 2025  
**Purpose:** Complete architecture and design context for starting a new repository

---

## 1. Project Overview

### Research Goal (IEEE Paper)
Demonstrate an **AI-Driven Personalized Security Awareness Training System** that uses:
1.  **Context-Aware Personalization**: A dynamic engine that tailors training content based on real-time user behavior (e.g., specific Git errors or Cloud miscues).
2.  **Simulated Metadata Servers**: For the purpose of this research, we simulate diverse enterprise data sources (Git, Jira, IAM) to generate deterministic risk scenarios.
3.  **Zero-Trust Provenance**: Using SPIFFE/SPIRE to guarantee the authenticity of the risk data feeding the AI.

### Key Innovation
Unlike generic security training, this system tailors content based on actual user behavior patterns. It uses a **Normalized Risk Score (0-1)** to translate technical events (e.g., "IAM Role Assumption") into business risk metrics suitable for HR and Executive dashboards.

---

## 2. High-Level Architecture (Simulation Mode)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SIMULATED METADATA SERVERS                             │
│  (Generates deterministic events for research: Force Switch, Phishing, etc.) │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│  Git     │   Jira   │ Workday  │ AWS IAM  │ Azure AD │ GCP IAM  │   SIEM   │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     │          │          │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA COLLECTORS (SPIFFE-Authenticated)                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Git Collector│ │Jira Collector│ │IAM Collector │ │SIEM Collector│           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘            │
└─────────┼───────────────┼───────────────┼───────────────┼───────────────────┘
          │               │               │               │
          ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         METADATA DATABASE                                    │
│                    (PostgreSQL: Users, Risks, Events)                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RISK SCORING ENGINE                                  │
│               (Normalizes metrics to 0.0 - 1.0 Risk Score)                   │
└───────────┼────────────────────┼────────────────────┼────────────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM GATEWAY (SPIFFE mTLS)                            │
│                  (Injects Risk Context -> Google Gemini)                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LMS (Personalized Dashboard)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. SPIFFE Infrastructure (Reuse from SPIFFE Paper)

### Trust Domain
```
spiffe://security-training.example.org
```

### SPIFFE Identities
| Component | SPIFFE ID |
|-----------|-----------|
| Git Collector | `spiffe://security-training.example.org/collector/git` |
| Jira Collector | `spiffe://security-training.example.org/collector/jira` |
| IAM Collector | `spiffe://security-training.example.org/collector/iam` |
| SIEM Collector | `spiffe://security-training.example.org/collector/siem` |
| Risk Scoring Engine | `spiffe://security-training.example.org/engine/risk-scorer` |
| Training Recommender | `spiffe://security-training.example.org/engine/recommender` |
| LLM Gateway | `spiffe://security-training.example.org/gateway/llm` |
| LMS API | `spiffe://security-training.example.org/lms/api` |

### Certificate Configuration
- **X.509-SVID TTL:** 1 hour (same as SPIFFE paper)
- **Auto-rotation:** 50% TTL (~30 minutes)
- **Storage:** Memory-only, never persisted to disk

---

## 4. Database Schema (PostgreSQL)

### Core Tables

```sql
-- User identity from Workday
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workday_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    department VARCHAR(100),
    job_title VARCHAR(100),
    manager_workday_id VARCHAR(50),
    hire_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Aggregated risk profile per user
CREATE TABLE user_risk_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    
    -- Git-derived metrics
    secrets_committed_count INT DEFAULT 0,
    force_pushes_count INT DEFAULT 0,
    commits_without_review INT DEFAULT 0,
    
    -- Jira-derived metrics  
    security_tickets_created INT DEFAULT 0,
    security_tickets_assigned INT DEFAULT 0,
    overdue_security_tasks INT DEFAULT 0,
    
    -- Cloud IAM metrics (aggregated across AWS/Azure/GCP)
    privilege_escalation_events INT DEFAULT 0,
    unused_permissions_count INT DEFAULT 0,
    mfa_disabled_services INT DEFAULT 0,
    cross_account_access_count INT DEFAULT 0,
    
    -- SIEM-derived metrics
    security_alerts_triggered INT DEFAULT 0,
    phishing_clicks INT DEFAULT 0,
    malware_detections INT DEFAULT 0,
    policy_violations INT DEFAULT 0,
    
    -- LMS metrics
    training_modules_completed INT DEFAULT 0,
    training_modules_overdue INT DEFAULT 0,
    last_training_date DATE,
    
    -- Computed scores (0.0 - 1.0, higher = more risk)
    git_risk_score DECIMAL(3,2) DEFAULT 0.00,
    iam_risk_score DECIMAL(3,2) DEFAULT 0.00,
    security_incident_score DECIMAL(3,2) DEFAULT 0.00,
    training_gap_score DECIMAL(3,2) DEFAULT 0.00,
    overall_risk_score DECIMAL(3,2) DEFAULT 0.00,
    
    -- Metadata
    last_calculated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Git activity events
CREATE TABLE git_activity (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,  -- 'commit', 'push', 'force_push', 'secret_detected'
    repository VARCHAR(255),
    branch VARCHAR(255),
    commit_sha VARCHAR(40),
    secret_type VARCHAR(100),  -- 'aws_key', 'api_token', etc.
    event_timestamp TIMESTAMP NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Jira activity
CREATE TABLE jira_activity (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,  -- 'ticket_created', 'ticket_assigned', 'ticket_resolved'
    ticket_key VARCHAR(50),
    ticket_type VARCHAR(50),  -- 'security_vulnerability', 'incident', etc.
    priority VARCHAR(20),
    status VARCHAR(50),
    due_date DATE,
    event_timestamp TIMESTAMP NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cloud IAM events (AWS, Azure, GCP unified)
CREATE TABLE iam_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    cloud_provider VARCHAR(10) NOT NULL,  -- 'aws', 'azure', 'gcp'
    event_type VARCHAR(100) NOT NULL,  -- 'role_assumed', 'permission_granted', etc.
    resource_arn VARCHAR(500),
    action VARCHAR(100),
    is_privileged BOOLEAN DEFAULT FALSE,
    event_timestamp TIMESTAMP NOT NULL,
    source_ip INET,
    user_agent TEXT,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- SIEM alerts
CREATE TABLE siem_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    alert_type VARCHAR(100) NOT NULL,  -- 'phishing', 'malware', 'policy_violation'
    severity VARCHAR(20),  -- 'low', 'medium', 'high', 'critical'
    source_system VARCHAR(100),  -- 'crowdstrike', 'sentinel', 'splunk'
    alert_name VARCHAR(255),
    description TEXT,
    remediation_status VARCHAR(50),
    event_timestamp TIMESTAMP NOT NULL,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Training completions
CREATE TABLE training_completions (
    completion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    module_id VARCHAR(100) NOT NULL,
    module_name VARCHAR(255),
    module_category VARCHAR(100),  -- 'phishing', 'password', 'data_handling'
    score DECIMAL(5,2),
    passed BOOLEAN,
    time_spent_minutes INT,
    completed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Risk score history (for trending)
CREATE TABLE risk_scores_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    overall_risk_score DECIMAL(3,2),
    git_risk_score DECIMAL(3,2),
    iam_risk_score DECIMAL(3,2),
    security_incident_score DECIMAL(3,2),
    training_gap_score DECIMAL(3,2),
    calculated_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_git_activity_user_timestamp ON git_activity(user_id, event_timestamp);
CREATE INDEX idx_jira_activity_user_timestamp ON jira_activity(user_id, event_timestamp);
CREATE INDEX idx_iam_events_user_timestamp ON iam_events(user_id, event_timestamp);
CREATE INDEX idx_siem_alerts_user_timestamp ON siem_alerts(user_id, event_timestamp);
CREATE INDEX idx_risk_profiles_overall_score ON user_risk_profiles(overall_risk_score DESC);
CREATE INDEX idx_risk_history_user_time ON risk_scores_history(user_id, calculated_at);
```

---

## 5. Data Source Integration Details

### 5.1 Git Integration (GitHub/GitLab)
**Webhook Events:**
- `push` - Track commits and force pushes
- `pull_request` - Track code reviews
- Secret scanning alerts (GitHub Advanced Security / GitLab Secret Detection)

**Risk Indicators:**
- Secrets committed to repos
- Force pushes to protected branches
- Commits without PR review
- Large file additions (potential data exfil)

### 5.2 Jira Integration
**API Polling:**
- JQL queries for security-related tickets
- User assignment and resolution tracking

**Risk Indicators:**
- Overdue security tasks
- Unresolved vulnerabilities assigned
- Pattern of reopened security tickets

### 5.3 Workday Integration
**Sync Frequency:** Daily batch

**Data Retrieved:**
- Employee ID, email, department
- Manager hierarchy
- Job title/role
- Hire date (for tenure-based risk weighting)

### 5.4 Cloud IAM Integration

#### AWS (CloudTrail)
- `AssumeRole` events
- `CreateAccessKey` events
- IAM policy changes
- Cross-account access

#### Azure AD / Entra ID
- Sign-in logs
- Privileged Identity Management (PIM) activations
- Conditional Access policy bypasses
- MFA status changes

#### GCP (Cloud Audit Logs)
- IAM role bindings
- Service account key creation
- Organization policy changes

### 5.5 SIEM Integration
**Supported Sources:**
- Splunk (REST API)
- Microsoft Sentinel (Log Analytics API)
- CrowdStrike (Falcon API)
- Elastic SIEM

**Alert Types:**
- Phishing email clicks
- Malware detections
- DLP policy violations
- Anomalous login patterns

---

## 6. Risk Scoring Algorithm

### Component Scores (0.0 - 1.0)

```python
def calculate_risk_scores(user_profile):
    """Calculate individual and overall risk scores."""
    
    # Git Risk Score
    git_risk = min(1.0, (
        user_profile.secrets_committed_count * 0.3 +
        user_profile.force_pushes_count * 0.1 +
        user_profile.commits_without_review * 0.05
    ))
    
    # IAM Risk Score
    iam_risk = min(1.0, (
        user_profile.privilege_escalation_events * 0.2 +
        user_profile.mfa_disabled_services * 0.25 +
        user_profile.unused_permissions_count * 0.02
    ))
    
    # Security Incident Score
    incident_risk = min(1.0, (
        user_profile.phishing_clicks * 0.15 +
        user_profile.malware_detections * 0.3 +
        user_profile.policy_violations * 0.1
    ))
    
    # Training Gap Score
    training_gap = min(1.0, (
        user_profile.training_modules_overdue * 0.1 +
        (1.0 if days_since_training > 180 else 0.0) * 0.3
    ))
    
    # Overall Risk (weighted average)
    overall_risk = (
        git_risk * 0.25 +
        iam_risk * 0.30 +
        incident_risk * 0.30 +
        training_gap * 0.15
    )
    
    return {
        'git_risk_score': git_risk,
        'iam_risk_score': iam_risk,
        'security_incident_score': incident_risk,
        'training_gap_score': training_gap,
        'overall_risk_score': overall_risk
    }
```

### Risk Levels
| Score Range | Level | Training Frequency |
|-------------|-------|-------------------|
| 0.0 - 0.2 | Low | Quarterly |
| 0.2 - 0.5 | Medium | Monthly |
| 0.5 - 0.7 | High | Bi-weekly |
| 0.7 - 1.0 | Critical | Weekly + Manager notification |

---

## 7. LMS (Streamlit Application)

### Core Features

1. **User Dashboard**
   - Personal risk score with trend
   - Risk breakdown by category
   - Assigned training modules
   - Completion history

2. **Training Module Delivery**
   - AI-generated personalized content based on risk factors
   - Interactive quizzes
   - Video content support
   - Progress tracking

3. **Manager Dashboard**
   - Team risk overview
   - Training compliance rates
   - High-risk user alerts
   - Drill-down to individual reports

4. **Admin Dashboard**
   - System-wide risk distribution
   - Training effectiveness metrics
   - Data source health monitoring
   - SPIFFE certificate status

### Personalization via LLM

```python
def generate_personalized_training(user_profile, risk_category):
    """Generate training content tailored to user's risk profile."""
    
    prompt = f"""
    Generate a personalized security training module for an employee with:
    - Department: {user_profile.department}
    - Job Title: {user_profile.job_title}
    - Primary Risk Area: {risk_category}
    - Recent Incidents: {summarize_incidents(user_profile)}
    
    The training should:
    1. Be directly relevant to their job role
    2. Address their specific risk behaviors
    3. Include practical examples they would encounter
    4. Provide actionable remediation steps
    """
    
    # Call LLM Gateway (SPIFFE-authenticated)
    response = llm_gateway.generate(prompt)
    return response
```

---

## 8. Project Structure

```
security-awareness-training/
├── README.md
├── docker-compose.yml
├── QUICKSTART.sh
│
├── configs/
│   ├── spire-server.yaml
│   ├── spire-agent.yaml
│   └── registrations.yaml
│
├── collectors/
│   ├── __init__.py
│   ├── base_collector.py
│   ├── git_collector.py
│   ├── jira_collector.py
│   ├── iam_collector.py
│   ├── siem_collector.py
│   └── workday_collector.py
│
├── database/
│   ├── schema.sql
│   ├── migrations/
│   └── seed_data.sql
│
├── engine/
│   ├── __init__.py
│   ├── risk_scorer.py
│   ├── behavior_analyzer.py
│   └── training_recommender.py
│
├── gateway/
│   ├── __init__.py
│   └── llm_gateway.py
│
├── lms/
│   ├── app.py                    # Streamlit main app
│   ├── pages/
│   │   ├── 1_dashboard.py
│   │   ├── 2_training.py
│   │   ├── 3_manager_view.py
│   │   └── 4_admin.py
│   ├── components/
│   │   ├── risk_chart.py
│   │   ├── training_card.py
│   │   └── user_table.py
│   └── utils/
│       ├── auth.py
│       └── api_client.py
│
├── scripts/
│   ├── deploy-spire.sh
│   ├── run-collectors.sh
│   └── calculate-risk-scores.sh
│
├── k8s/
│   ├── namespace.yaml
│   ├── spire/
│   ├── collectors/
│   ├── engine/
│   └── lms/
│
└── tests/
    ├── test_collectors.py
    ├── test_risk_scorer.py
    └── test_lms.py
```

---

## 9. Technology Stack

| Layer | Technology |
|-------|------------|
| Identity | SPIFFE/SPIRE (X.509-SVID, mTLS) |
| Database | PostgreSQL 15 + TimescaleDB |
| Backend | Python 3.11, FastAPI |
| LMS Frontend | Streamlit |
| LLM | Google Gemini 2.0 Flash |
| Container | Docker, Kubernetes |
| CI/CD | GitHub Actions |

---

## 10. Getting Started (After Creating New Repo)

### Step 1: Initialize Repository
```bash
mkdir security-awareness-training
cd security-awareness-training
git init
# Paste this document as ARCHITECTURE.md
```

### Step 2: Create Python Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn streamlit psycopg2-binary py-spiffe google-generativeai
```

### Step 3: Start with Database Schema
```bash
# Create database/schema.sql from Section 4 above
psql -U postgres -c "CREATE DATABASE security_training;"
psql -U postgres -d security_training -f database/schema.sql
```

### Step 4: Implement in Order
1. SPIRE infrastructure (`configs/`, `scripts/deploy-spire.sh`)
2. Base collector with SPIFFE auth (`collectors/base_collector.py`)
3. One collector as POC (`collectors/git_collector.py`)
4. Risk scoring engine (`engine/risk_scorer.py`)
5. LLM Gateway (`gateway/llm_gateway.py`)
6. Streamlit LMS (`lms/app.py`)

---

## 11. Relationship to SPIFFE Paper

This project reuses the core SPIFFE patterns from the IEEE paper:

| SPIFFE Paper Component | This Project Equivalent |
|------------------------|------------------------|
| Pipeline Orchestrator | Risk Scoring Engine |
| Threat Classifier | Behavior Analyzer |
| Confidence Scorer | Risk Calculator |
| Threat Validator | Training Recommender |
| LLM Gateway | LLM Gateway (same pattern) |

**Key Differences:**
- Data flows from external sources (Git, Jira, IAM, SIEM) instead of threat events
- Output is personalized training, not threat assessments
- Includes persistent database for user profiles
- Includes Streamlit UI for end users

---

## 12. Future Enhancements

- **Phase 2:** Add EDR/MDM integration (CrowdStrike, Intune)
- **Phase 3:** Gamification (leaderboards, badges)
- **Phase 4:** Cross-organization benchmarking
- **Phase 5:** Integration with HR systems for training compliance reporting

---

## 13. IMPROVED CODE ARCHITECTURE (NO MORE DUPLICATION!)

### The Problem in the Old Project

In `/agents/`, we had 4 files with ~500 lines each, but **~300 lines were identical** (the SPIFFEMTLSHandler class). This is bad because:
- Bug fixes need to be applied 4 times
- Easy to have inconsistencies
- Harder to maintain

### The Solution: Base Class + Inheritance

```
collectors/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── spiffe_agent.py      # ALL SPIFFE/mTLS code lives here (ONE place!)
│   └── http_handlers.py     # Common HTTP patterns
├── git_collector.py         # Just the Git-specific logic (~50 lines)
├── jira_collector.py        # Just the Jira-specific logic (~50 lines)
├── iam_collector.py         # Just the IAM-specific logic (~50 lines)
└── siem_collector.py        # Just the SIEM-specific logic (~50 lines)
```

---

### 13.1 The Base SPIFFE Agent Class (PUT ALL COMMON CODE HERE)

```python
# collectors/base/spiffe_agent.py
"""
Base SPIFFE Agent - ALL mTLS/certificate code in ONE place!
Every collector inherits from this.
"""

import os
import ssl
import json
import tempfile
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from abc import ABC, abstractmethod

from spiffe import WorkloadApiClient
from cryptography.hazmat.primitives import serialization

class SPIFFEMTLSHandler:
    """Certificate management - same as before but now shared."""
    
    def __init__(self, trust_domain="security-training.example.org"):
        self.cert_file = None
        self.key_file = None
        self.bundle_file = None
        self.x509_svid = None
        self.spiffe_id = None
        self.trust_domain = trust_domain
        self.logger = logging.getLogger(self.__class__.__name__)
        self._refresh_certificates()
        self._start_refresh_thread()
    
    def _start_refresh_thread(self):
        """Auto-refresh certificates before expiry."""
        def refresh_loop():
            while True:
                time.sleep(1800)  # 30 minutes
                self._refresh_certificates()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
    
    def _refresh_certificates(self):
        """Fetch certs from SPIRE - with retry logic."""
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                with WorkloadApiClient() as client:
                    self.x509_svid = client.fetch_x509_svid()
                    self.spiffe_id = str(self.x509_svid.spiffe_id)
                    trust_bundle = client.fetch_x509_bundles()
                    
                    self._write_cert_files(trust_bundle)
                    self.logger.info(f"✅ Certificates refreshed: {self.spiffe_id}")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Cert fetch failed (attempt {attempt}): {e}")
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
        return False
    
    def _write_cert_files(self, trust_bundle):
        """Write cert/key/bundle to temp files."""
        # Cleanup old files
        for f in [self.cert_file, self.key_file, self.bundle_file]:
            if f:
                try: os.unlink(f.name)
                except: pass
        
        # Write cert chain
        self.cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        cert_chain = self.x509_svid.cert_chain
        if callable(cert_chain): cert_chain = cert_chain()
        if isinstance(cert_chain, list):
            for c in cert_chain:
                self.cert_file.write(c.public_bytes(serialization.Encoding.PEM).decode())
        else:
            self.cert_file.write(cert_chain.decode() if isinstance(cert_chain, bytes) else cert_chain)
        self.cert_file.flush()
        
        # Write private key
        self.key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key')
        priv_key = self.x509_svid.private_key
        if callable(priv_key): priv_key = priv_key()
        if hasattr(priv_key, 'private_bytes'):
            priv_key = priv_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
        self.key_file.write(priv_key if isinstance(priv_key, str) else priv_key.decode())
        self.key_file.flush()
        
        # Write trust bundle
        self.bundle_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        if hasattr(trust_bundle, '_bundles'):
            for td, bundle in trust_bundle._bundles.items():
                authorities = bundle.x509_authorities
                if callable(authorities): authorities = authorities()
                for cert in authorities:
                    self.bundle_file.write(cert.public_bytes(serialization.Encoding.PEM).decode())
        self.bundle_file.flush()
    
    def create_server_ssl_context(self):
        """SSL context for HTTPS server with mTLS."""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(self.cert_file.name, self.key_file.name)
        context.load_verify_locations(cafile=self.bundle_file.name)
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context
    
    def make_mtls_request(self, url, json_data, timeout=30):
        """Make mTLS client request."""
        import requests
        import urllib3
        urllib3.disable_warnings()
        return requests.post(
            url, json=json_data,
            cert=(self.cert_file.name, self.key_file.name),
            verify=False, timeout=timeout
        )


class BaseSPIFFEAgent(ABC):
    """
    Base class for ALL agents/collectors.
    Inherit from this and just implement the business logic!
    """
    
    def __init__(self, service_name: str, port: int, allowed_callers: list = None):
        self.service_name = service_name
        self.port = port
        self.allowed_callers = allowed_callers or []
        self.logger = logging.getLogger(service_name)
        
        # Initialize SPIFFE
        self.mtls = SPIFFEMTLSHandler()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @abstractmethod
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        """
        Override this in your agent!
        
        Args:
            path: Request path (e.g., '/collect', '/score')
            data: JSON request body
            peer_spiffe_id: Authenticated caller's SPIFFE ID
        
        Returns:
            dict: Response to send back
        """
        pass
    
    def run(self):
        """Start the HTTPS server with mTLS."""
        handler = self._create_handler()
        
        server = HTTPServer(('0.0.0.0', self.port), handler)
        server.socket = self.mtls.create_server_ssl_context().wrap_socket(
            server.socket, server_side=True
        )
        
        self.logger.info(f"🚀 {self.service_name} running on port {self.port}")
        self.logger.info(f"   SPIFFE ID: {self.mtls.spiffe_id}")
        self.logger.info(f"   mTLS: enabled")
        
        server.serve_forever()
    
    def _create_handler(self):
        """Create HTTP handler with reference to this agent."""
        agent = self
        
        class AgentHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                # Extract peer SPIFFE ID
                peer_cert = self.connection.getpeercert()
                san = peer_cert.get('subjectAltName', []) if peer_cert else []
                peer_id = next(
                    (uri for typ, uri in san if typ == 'URI' and uri.startswith('spiffe://')),
                    None
                )
                
                # Authorize
                if agent.allowed_callers and peer_id not in agent.allowed_callers:
                    self.send_error(403, f"Unauthorized: {peer_id}")
                    return
                
                # Read request
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length)) if length else {}
                
                # Delegate to agent's business logic
                try:
                    result = agent.handle_request(self.path, data, peer_id)
                    self._send_json(200, result)
                except Exception as e:
                    agent.logger.error(f"Error: {e}")
                    self._send_json(500, {"error": str(e)})
            
            def do_GET(self):
                if self.path == '/health':
                    self._send_json(200, {
                        "status": "healthy",
                        "service": agent.service_name,
                        "spiffe_id": agent.mtls.spiffe_id
                    })
                else:
                    self.send_error(404)
            
            def _send_json(self, code, data):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            
            def log_message(self, format, *args):
                agent.logger.info("%s - %s", self.client_address[0], format % args)
        
        return AgentHandler
```

---

### 13.2 Now Your Collectors Are TINY!

```python
# collectors/git_collector.py
"""
Git Collector - ONLY the Git-specific logic!
All SPIFFE/mTLS code is inherited from base class.
"""

from base.spiffe_agent import BaseSPIFFEAgent
import requests


class GitCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="git-collector",
            port=8501,
            allowed_callers=[
                "spiffe://security-training.example.org/risk-scorer"
            ]
        )
        self.github_token = os.getenv('GITHUB_TOKEN')
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        """Handle incoming requests - this is YOUR business logic."""
        
        if path == '/collect':
            user_email = data.get('user_email')
            return self._collect_git_activity(user_email)
        
        elif path == '/webhook':
            return self._handle_webhook(data)
        
        else:
            return {"error": f"Unknown path: {path}"}
    
    def _collect_git_activity(self, user_email: str) -> dict:
        """Collect git activity for a user."""
        # Your Git API logic here
        commits = self._fetch_commits(user_email)
        secrets = self._check_secret_scanning(user_email)
        
        return {
            "user_email": user_email,
            "commits_count": len(commits),
            "secrets_detected": len(secrets),
            "force_pushes": self._count_force_pushes(user_email)
        }
    
    def _fetch_commits(self, user_email):
        # GitHub API call
        pass
    
    def _check_secret_scanning(self, user_email):
        # GitHub secret scanning API
        pass


if __name__ == '__main__':
    GitCollector().run()
```

```python
# collectors/jira_collector.py
"""Jira Collector - ONLY Jira-specific logic!"""

from base.spiffe_agent import BaseSPIFFEAgent


class JiraCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="jira-collector",
            port=8502,
            allowed_callers=[
                "spiffe://security-training.example.org/risk-scorer"
            ]
        )
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            return self._collect_jira_activity(data.get('user_email'))
        return {"error": "Unknown path"}
    
    def _collect_jira_activity(self, user_email: str) -> dict:
        # Your Jira logic here
        return {
            "user_email": user_email,
            "security_tickets": 5,
            "overdue_tasks": 2
        }


if __name__ == '__main__':
    JiraCollector().run()
```

**Result:** Each collector is now ~50 lines instead of ~500 lines!

---

## 13.3 DATABASE INTEGRATION (SAVING DATA TO POSTGRESQL)

The collectors need to save data to the database. Here's the complete pattern:

### Base Database Class (Shared)

```python
# src/base/database.py
"""
Database utilities - shared by all collectors and services.
Uses connection pooling for efficiency.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values

logger = logging.getLogger(__name__)

class Database:
    """
    PostgreSQL database handler with connection pooling.
    Thread-safe for use in multi-threaded SPIFFE agents.
    """
    
    _pool: pool.ThreadedConnectionPool = None
    
    @classmethod
    def init_pool(cls, min_conn=2, max_conn=10):
        """Initialize connection pool. Call once at startup."""
        if cls._pool is None:
            cls._pool = pool.ThreadedConnectionPool(
                min_conn, max_conn,
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                dbname=os.getenv('DB_NAME', 'security_training'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            logger.info(f"✅ Database pool initialized ({min_conn}-{max_conn} connections)")
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a connection from the pool (context manager)."""
        if cls._pool is None:
            cls.init_pool()
        
        conn = cls._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cls._pool.putconn(conn)
    
    @classmethod
    def execute(cls, query: str, params: tuple = None) -> None:
        """Execute a query (INSERT, UPDATE, DELETE)."""
        with cls.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
    
    @classmethod
    def fetch_one(cls, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch a single row as dict."""
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchone()
    
    @classmethod
    def fetch_all(cls, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows as list of dicts."""
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
    
    @classmethod
    def insert_many(cls, table: str, columns: List[str], values: List[tuple]) -> int:
        """Bulk insert rows efficiently."""
        with cls.get_connection() as conn:
            with conn.cursor() as cur:
                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
                execute_values(cur, query, values)
                return cur.rowcount


# =============================================================================
# REPOSITORY CLASSES - One per table/entity
# =============================================================================

class UserRepository:
    """Database operations for users table."""
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM users WHERE email = %s", (email,)
        )
    
    @staticmethod
    def get_by_workday_id(workday_id: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM users WHERE workday_id = %s", (workday_id,)
        )
    
    @staticmethod
    def upsert(workday_id: str, email: str, full_name: str, 
               department: str, job_title: str) -> Dict:
        """Insert or update user."""
        return Database.fetch_one("""
            INSERT INTO users (workday_id, email, full_name, department, job_title, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (workday_id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                department = EXCLUDED.department,
                job_title = EXCLUDED.job_title,
                updated_at = NOW()
            RETURNING *
        """, (workday_id, email, full_name, department, job_title))


class GitActivityRepository:
    """Database operations for git_activity table."""
    
    @staticmethod
    def insert(user_id: str, event_type: str, repository: str,
               branch: str = None, commit_sha: str = None,
               secret_type: str = None, event_timestamp: datetime = None,
               raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO git_activity 
            (user_id, event_type, repository, branch, commit_sha, 
             secret_type, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, event_type, repository, branch, commit_sha,
              secret_type, event_timestamp or datetime.utcnow(),
              psycopg2.extras.Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        """Get aggregated stats for a user."""
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE event_type = 'commit') as commits,
                COUNT(*) FILTER (WHERE event_type = 'force_push') as force_pushes,
                COUNT(*) FILTER (WHERE event_type = 'secret_detected') as secrets_detected
            FROM git_activity
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))
    
    @staticmethod
    def bulk_insert(events: List[Dict]) -> int:
        """Bulk insert git events."""
        columns = ['user_id', 'event_type', 'repository', 'branch', 
                   'commit_sha', 'event_timestamp']
        values = [
            (e['user_id'], e['event_type'], e['repository'], 
             e.get('branch'), e.get('commit_sha'), e.get('event_timestamp'))
            for e in events
        ]
        return Database.insert_many('git_activity', columns, values)


class JiraActivityRepository:
    """Database operations for jira_activity table."""
    
    @staticmethod
    def insert(user_id: str, event_type: str, ticket_key: str,
               ticket_type: str, priority: str, status: str,
               due_date: datetime = None, raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO jira_activity 
            (user_id, event_type, ticket_key, ticket_type, priority, 
             status, due_date, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (user_id, event_type, ticket_key, ticket_type, priority,
              status, due_date,
              psycopg2.extras.Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE ticket_type = 'security_vulnerability') as security_tickets,
                COUNT(*) FILTER (WHERE status != 'Done' AND due_date < NOW()) as overdue_tasks
            FROM jira_activity
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class IAMEventsRepository:
    """Database operations for iam_events table."""
    
    @staticmethod
    def insert(user_id: str, cloud_provider: str, event_type: str,
               resource_arn: str = None, action: str = None,
               is_privileged: bool = False, source_ip: str = None,
               raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO iam_events 
            (user_id, cloud_provider, event_type, resource_arn, action,
             is_privileged, event_timestamp, source_ip, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        """, (user_id, cloud_provider, event_type, resource_arn, action,
              is_privileged, source_ip,
              psycopg2.extras.Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE is_privileged = true) as privileged_events,
                COUNT(*) FILTER (WHERE event_type = 'AssumeRole') as role_assumptions,
                COUNT(DISTINCT cloud_provider) as cloud_providers_used
            FROM iam_events
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class SIEMAlertRepository:
    """Database operations for siem_alerts table."""
    
    @staticmethod
    def insert(user_id: str, alert_type: str, severity: str,
               source_system: str, alert_name: str,
               description: str = None, raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO siem_alerts 
            (user_id, alert_type, severity, source_system, alert_name,
             description, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (user_id, alert_type, severity, source_system, alert_name,
              description,
              psycopg2.extras.Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE alert_type = 'phishing') as phishing_clicks,
                COUNT(*) FILTER (WHERE alert_type = 'malware') as malware_detections,
                COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as high_severity
            FROM siem_alerts
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class RiskProfileRepository:
    """Database operations for user_risk_profiles table."""
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM user_risk_profiles WHERE user_id = %s", (user_id,)
        )
    
    @staticmethod
    def upsert(user_id: str, metrics: Dict) -> Dict:
        """Update or create risk profile with new metrics."""
        return Database.fetch_one("""
            INSERT INTO user_risk_profiles (user_id, 
                secrets_committed_count, force_pushes_count, commits_without_review,
                security_tickets_created, overdue_security_tasks,
                privilege_escalation_events, mfa_disabled_services,
                security_alerts_triggered, phishing_clicks, malware_detections,
                git_risk_score, iam_risk_score, security_incident_score,
                training_gap_score, overall_risk_score,
                last_calculated_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                secrets_committed_count = EXCLUDED.secrets_committed_count,
                force_pushes_count = EXCLUDED.force_pushes_count,
                commits_without_review = EXCLUDED.commits_without_review,
                security_tickets_created = EXCLUDED.security_tickets_created,
                overdue_security_tasks = EXCLUDED.overdue_security_tasks,
                privilege_escalation_events = EXCLUDED.privilege_escalation_events,
                mfa_disabled_services = EXCLUDED.mfa_disabled_services,
                security_alerts_triggered = EXCLUDED.security_alerts_triggered,
                phishing_clicks = EXCLUDED.phishing_clicks,
                malware_detections = EXCLUDED.malware_detections,
                git_risk_score = EXCLUDED.git_risk_score,
                iam_risk_score = EXCLUDED.iam_risk_score,
                security_incident_score = EXCLUDED.security_incident_score,
                training_gap_score = EXCLUDED.training_gap_score,
                overall_risk_score = EXCLUDED.overall_risk_score,
                last_calculated_at = NOW(),
                updated_at = NOW()
            RETURNING *
        """, (user_id,
              metrics.get('secrets_committed_count', 0),
              metrics.get('force_pushes_count', 0),
              metrics.get('commits_without_review', 0),
              metrics.get('security_tickets_created', 0),
              metrics.get('overdue_security_tasks', 0),
              metrics.get('privilege_escalation_events', 0),
              metrics.get('mfa_disabled_services', 0),
              metrics.get('security_alerts_triggered', 0),
              metrics.get('phishing_clicks', 0),
              metrics.get('malware_detections', 0),
              metrics.get('git_risk_score', 0.0),
              metrics.get('iam_risk_score', 0.0),
              metrics.get('security_incident_score', 0.0),
              metrics.get('training_gap_score', 0.0),
              metrics.get('overall_risk_score', 0.0)))
    
    @staticmethod
    def get_high_risk_users(threshold: float = 0.7) -> List[Dict]:
        """Get all users above risk threshold."""
        return Database.fetch_all("""
            SELECT urp.*, u.email, u.full_name, u.department
            FROM user_risk_profiles urp
            JOIN users u ON urp.user_id = u.user_id
            WHERE urp.overall_risk_score >= %s
            ORDER BY urp.overall_risk_score DESC
        """, (threshold,))
    
    @staticmethod
    def save_history(user_id: str, scores: Dict) -> None:
        """Save score snapshot for trending."""
        Database.execute("""
            INSERT INTO risk_scores_history 
            (user_id, overall_risk_score, git_risk_score, iam_risk_score,
             security_incident_score, training_gap_score, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (user_id, scores['overall_risk_score'], scores['git_risk_score'],
              scores['iam_risk_score'], scores['security_incident_score'],
              scores['training_gap_score']))
```

---

### Git Collector WITH Database Integration

```python
# src/collectors/git_collector.py
"""
Git Collector - Collects from GitHub/GitLab AND saves to database.
"""

import os
import requests
from datetime import datetime
from base.spiffe_agent import BaseSPIFFEAgent
from base.database import Database, UserRepository, GitActivityRepository


class GitCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="git-collector",
            port=8501,
            allowed_callers=[
                "spiffe://security-training.example.org/risk-scorer"
            ]
        )
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_org = os.getenv('GITHUB_ORG', 'your-org')
        
        # Initialize database pool
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            return self._collect_and_save(data.get('user_email'))
        elif path == '/webhook':
            return self._handle_webhook(data)
        elif path == '/stats':
            return self._get_user_stats(data.get('user_id'))
        return {"error": f"Unknown path: {path}"}
    
    def _collect_and_save(self, user_email: str) -> dict:
        """Collect git activity and save to database."""
        
        # Get user from database
        user = UserRepository.get_by_email(user_email)
        if not user:
            return {"error": f"User not found: {user_email}"}
        
        user_id = user['user_id']
        
        # Fetch from GitHub API
        commits = self._fetch_github_commits(user_email)
        secrets = self._fetch_secret_alerts(user_email)
        
        # Save each event to database
        events_saved = 0
        
        for commit in commits:
            GitActivityRepository.insert(
                user_id=user_id,
                event_type='commit',
                repository=commit['repo'],
                branch=commit.get('branch'),
                commit_sha=commit['sha'],
                event_timestamp=datetime.fromisoformat(commit['date']),
                raw_data=commit
            )
            events_saved += 1
        
        for secret in secrets:
            GitActivityRepository.insert(
                user_id=user_id,
                event_type='secret_detected',
                repository=secret['repo'],
                secret_type=secret['secret_type'],
                event_timestamp=datetime.fromisoformat(secret['created_at']),
                raw_data=secret
            )
            events_saved += 1
        
        # Get aggregated stats
        stats = GitActivityRepository.get_user_stats(user_id)
        
        self.logger.info(f"✅ Saved {events_saved} git events for {user_email}")
        
        return {
            "user_email": user_email,
            "user_id": str(user_id),
            "events_saved": events_saved,
            "stats": stats,
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _handle_webhook(self, payload: dict) -> dict:
        """Handle GitHub webhook for real-time updates."""
        event_type = payload.get('action', 'push')
        
        # Extract user email from webhook
        if 'pusher' in payload:
            user_email = payload['pusher'].get('email')
        elif 'sender' in payload:
            user_email = payload['sender'].get('email')
        else:
            return {"error": "Could not extract user email from webhook"}
        
        user = UserRepository.get_by_email(user_email)
        if not user:
            self.logger.warning(f"Unknown user from webhook: {user_email}")
            return {"status": "ignored", "reason": "unknown user"}
        
        # Detect force push
        if payload.get('forced', False):
            GitActivityRepository.insert(
                user_id=user['user_id'],
                event_type='force_push',
                repository=payload['repository']['full_name'],
                branch=payload.get('ref', '').replace('refs/heads/', ''),
                raw_data=payload
            )
            self.logger.warning(f"⚠️ Force push detected from {user_email}")
        
        return {"status": "processed", "event_type": event_type}
    
    def _get_user_stats(self, user_id: str) -> dict:
        """Get stats directly from database."""
        return GitActivityRepository.get_user_stats(user_id)
    
    def _fetch_github_commits(self, user_email: str) -> list:
        """Fetch commits from GitHub API."""
        headers = {"Authorization": f"token {self.github_token}"}
        commits = []
        
        # Search commits by author email
        response = requests.get(
            f"https://api.github.com/search/commits",
            params={
                "q": f"author-email:{user_email} org:{self.github_org}",
                "sort": "author-date",
                "order": "desc",
                "per_page": 100
            },
            headers={**headers, "Accept": "application/vnd.github.cloak-preview+json"}
        )
        
        if response.status_code == 200:
            for item in response.json().get('items', []):
                commits.append({
                    "sha": item['sha'],
                    "repo": item['repository']['full_name'],
                    "message": item['commit']['message'][:200],
                    "date": item['commit']['author']['date']
                })
        
        return commits
    
    def _fetch_secret_alerts(self, user_email: str) -> list:
        """Fetch secret scanning alerts."""
        # Implementation depends on GitHub Advanced Security or GitLab
        return []


if __name__ == '__main__':
    GitCollector().run()
```

---

### Risk Scorer WITH Database Integration

```python
# src/engine/risk_scorer.py
"""
Risk Scoring Engine - Aggregates data from all collectors,
calculates risk scores, and saves to database.
"""

from datetime import datetime
from base.spiffe_agent import BaseSPIFFEAgent
from base.database import (
    Database, UserRepository, RiskProfileRepository,
    GitActivityRepository, JiraActivityRepository,
    IAMEventsRepository, SIEMAlertRepository
)


class RiskScorer(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="risk-scorer",
            port=8510,
            allowed_callers=[
                "spiffe://security-training.example.org/lms-api",
                "spiffe://security-training.example.org/training-recommender"
            ]
        )
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/score':
            return self._calculate_risk_score(data.get('user_id'))
        elif path == '/score-all':
            return self._calculate_all_scores()
        elif path == '/high-risk':
            threshold = data.get('threshold', 0.7)
            return self._get_high_risk_users(threshold)
        return {"error": f"Unknown path: {path}"}
    
    def _calculate_risk_score(self, user_id: str) -> dict:
        """Calculate and save risk score for a single user."""
        
        # Get stats from all data sources
        git_stats = GitActivityRepository.get_user_stats(user_id) or {}
        jira_stats = JiraActivityRepository.get_user_stats(user_id) or {}
        iam_stats = IAMEventsRepository.get_user_stats(user_id) or {}
        siem_stats = SIEMAlertRepository.get_user_stats(user_id) or {}
        
        # Calculate individual risk scores (0.0 - 1.0)
        git_risk = min(1.0, (
            (git_stats.get('secrets_detected', 0) or 0) * 0.3 +
            (git_stats.get('force_pushes', 0) or 0) * 0.1
        ))
        
        iam_risk = min(1.0, (
            (iam_stats.get('privileged_events', 0) or 0) * 0.15
        ))
        
        incident_risk = min(1.0, (
            (siem_stats.get('phishing_clicks', 0) or 0) * 0.2 +
            (siem_stats.get('malware_detections', 0) or 0) * 0.3
        ))
        
        training_gap = min(1.0, (
            (jira_stats.get('overdue_tasks', 0) or 0) * 0.1
        ))
        
        # Weighted overall score
        overall_risk = (
            git_risk * 0.25 +
            iam_risk * 0.30 +
            incident_risk * 0.30 +
            training_gap * 0.15
        )
        
        # Build metrics dict
        metrics = {
            'secrets_committed_count': git_stats.get('secrets_detected', 0) or 0,
            'force_pushes_count': git_stats.get('force_pushes', 0) or 0,
            'security_tickets_created': jira_stats.get('security_tickets', 0) or 0,
            'overdue_security_tasks': jira_stats.get('overdue_tasks', 0) or 0,
            'privilege_escalation_events': iam_stats.get('privileged_events', 0) or 0,
            'security_alerts_triggered': siem_stats.get('total_alerts', 0) or 0,
            'phishing_clicks': siem_stats.get('phishing_clicks', 0) or 0,
            'malware_detections': siem_stats.get('malware_detections', 0) or 0,
            'git_risk_score': round(git_risk, 2),
            'iam_risk_score': round(iam_risk, 2),
            'security_incident_score': round(incident_risk, 2),
            'training_gap_score': round(training_gap, 2),
            'overall_risk_score': round(overall_risk, 2)
        }
        
        # Save to database
        profile = RiskProfileRepository.upsert(user_id, metrics)
        
        # Save history for trending
        RiskProfileRepository.save_history(user_id, metrics)
        
        self.logger.info(f"✅ Risk score calculated for {user_id}: {overall_risk:.2f}")
        
        return {
            "user_id": user_id,
            "scores": metrics,
            "risk_level": self._get_risk_level(overall_risk),
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_all_scores(self) -> dict:
        """Recalculate scores for all users (batch job)."""
        users = Database.fetch_all("SELECT user_id FROM users")
        
        results = {"processed": 0, "errors": 0}
        for user in users:
            try:
                self._calculate_risk_score(str(user['user_id']))
                results["processed"] += 1
            except Exception as e:
                self.logger.error(f"Error scoring {user['user_id']}: {e}")
                results["errors"] += 1
        
        return results
    
    def _get_high_risk_users(self, threshold: float) -> dict:
        """Get all users above risk threshold."""
        users = RiskProfileRepository.get_high_risk_users(threshold)
        return {
            "threshold": threshold,
            "count": len(users),
            "users": users
        }
    
    def _get_risk_level(self, score: float) -> str:
        if score >= 0.7: return "CRITICAL"
        if score >= 0.5: return "HIGH"
        if score >= 0.2: return "MEDIUM"
        return "LOW"


if __name__ == '__main__':
    RiskScorer().run()
```

---

### Database Environment Variables (Add to Helm values.yaml)

```yaml
# In values.yaml
database:
  host: postgres-svc
  port: 5432
  name: security_training
  user: postgres
  # Password should come from a Secret
  passwordSecret: db-credentials
  passwordKey: password

# Add to each collector/service deployment
env:
  - name: DB_HOST
    value: "{{ .Values.database.host }}"
  - name: DB_PORT
    value: "{{ .Values.database.port }}"
  - name: DB_NAME
    value: "{{ .Values.database.name }}"
  - name: DB_USER
    value: "{{ .Values.database.user }}"
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: "{{ .Values.database.passwordSecret }}"
        key: "{{ .Values.database.passwordKey }}"
```

---

### PostgreSQL Deployment (Helm Template)

```yaml
# helm/security-training/templates/database/postgres.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: {{ .Values.global.namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: {{ .Values.database.name }}
        - name: POSTGRES_USER
          value: {{ .Values.database.user }}
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: {{ .Values.database.passwordSecret }}
              key: {{ .Values.database.passwordKey }}
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        - name: init-scripts
          mountPath: /docker-entrypoint-initdb.d
      volumes:
      - name: postgres-data
        persistentVolumeClaim:
          claimName: postgres-pvc
      - name: init-scripts
        configMap:
          name: postgres-init-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-svc
  namespace: {{ .Values.global.namespace }}
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-init-scripts
  namespace: {{ .Values.global.namespace }}
data:
  01-schema.sql: |
    -- Paste your schema from Section 4 here
    -- Or reference a file
```

---

## 14. USING HELM (YES, IT MAKES EVERYTHING EASIER!)

### Why Helm?

| Without Helm | With Helm |
|--------------|-----------|
| 10+ YAML files, lots of copy-paste | 1 Chart, parameterized |
| Change TTL? Edit 5 files | Change TTL? Edit 1 value |
| Different envs = duplicate files | Different envs = different values.yaml |
| SPIRE registrations = manual | SPIRE registrations = automated |

---

### 14.1 Helm Chart Structure

```
helm/
└── security-training/
    ├── Chart.yaml
    ├── values.yaml                    # Default values
    ├── values-dev.yaml                # Dev overrides
    ├── values-prod.yaml               # Prod overrides
    └── templates/
        ├── _helpers.tpl               # Template helpers
        ├── namespace.yaml
        ├── spire/
        │   ├── server-configmap.yaml
        │   ├── server-deployment.yaml
        │   ├── server-service.yaml
        │   ├── agent-configmap.yaml
        │   ├── agent-daemonset.yaml
        │   └── registrations-job.yaml  # Auto-register identities!
        ├── collectors/
        │   ├── deployment.yaml         # ONE template for ALL collectors!
        │   └── service.yaml
        ├── engine/
        │   ├── deployment.yaml
        │   └── service.yaml
        ├── gateway/
        │   ├── deployment.yaml
        │   └── service.yaml
        └── lms/
            ├── deployment.yaml
            └── service.yaml
```

---

### 14.2 values.yaml - All Config in ONE Place!

```yaml
# helm/security-training/values.yaml

global:
  namespace: security-training
  trustDomain: security-training.example.org
  
spire:
  server:
    image: ghcr.io/spiffe/spire-server:1.8.5
    svid_ttl: "1h"      # Change TTL here, applies everywhere!
    ca_ttl: "24h"
    log_level: DEBUG
  agent:
    image: ghcr.io/spiffe/spire-agent:1.8.5

# Define ALL collectors in one place
collectors:
  - name: git-collector
    port: 8501
    serviceAccount: git-collector-sa
    spiffeId: git-collector
    env:
      - name: GITHUB_TOKEN
        valueFrom:
          secretKeyRef:
            name: collector-secrets
            key: github-token
    
  - name: jira-collector
    port: 8502
    serviceAccount: jira-collector-sa
    spiffeId: jira-collector
    env:
      - name: JIRA_API_TOKEN
        valueFrom:
          secretKeyRef:
            name: collector-secrets
            key: jira-token
    
  - name: iam-collector
    port: 8503
    serviceAccount: iam-collector-sa
    spiffeId: iam-collector
    
  - name: siem-collector
    port: 8504
    serviceAccount: siem-collector-sa
    spiffeId: siem-collector

engine:
  riskScorer:
    port: 8510
    replicas: 2
  recommender:
    port: 8511
    replicas: 1

gateway:
  llm:
    port: 8520
    backend: gemini  # or 'lmstudio'
    model: gemini-2.0-flash

lms:
  port: 8080
  replicas: 2

database:
  host: postgres-svc
  port: 5432
  name: security_training
```

---

### 14.3 Template for ALL Collectors (ONE file!)

```yaml
# helm/security-training/templates/collectors/deployment.yaml
{{- range .Values.collectors }}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .serviceAccount }}
  namespace: {{ $.Values.global.namespace }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
  namespace: {{ $.Values.global.namespace }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ .name }}
  template:
    metadata:
      labels:
        app: {{ .name }}
    spec:
      serviceAccountName: {{ .serviceAccount }}
      containers:
      - name: {{ .name }}
        image: {{ $.Values.global.collectorImage | default "python:3.11-slim" }}
        command: ["/bin/sh", "-c"]
        args:
          - |
            pip install -r /app/requirements.txt
            python /app/collectors/{{ .name | replace "-" "_" }}.py
        ports:
        - containerPort: {{ .port }}
        env:
        - name: SPIFFE_ENDPOINT_SOCKET
          value: "unix:///opt/spire/sockets/agent.sock"
        {{- if .env }}
        {{- toYaml .env | nindent 8 }}
        {{- end }}
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /opt/spire/sockets
          readOnly: true
        - name: app-code
          mountPath: /app
      volumes:
      - name: spire-agent-socket
        hostPath:
          path: /opt/spire/sockets
          type: DirectoryOrCreate
      - name: app-code
        configMap:
          name: app-code
---
apiVersion: v1
kind: Service
metadata:
  name: {{ .name }}-svc
  namespace: {{ $.Values.global.namespace }}
spec:
  selector:
    app: {{ .name }}
  ports:
  - port: {{ .port }}
    targetPort: {{ .port }}
{{- end }}
```

**This ONE template creates deployments for ALL 4 collectors!**

---

### 14.4 Auto-Register SPIFFE Identities with a Job

```yaml
# helm/security-training/templates/spire/registrations-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: spire-register-workloads
  namespace: {{ .Values.global.namespace }}
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "10"
spec:
  template:
    spec:
      serviceAccountName: spire-server
      restartPolicy: OnFailure
      containers:
      - name: register
        image: ghcr.io/spiffe/spire-server:1.8.5
        command: ["/bin/sh", "-c"]
        args:
          - |
            # Wait for SPIRE server
            sleep 10
            
            # Get agent parent ID
            PARENT_ID=$(spire-server entry show | grep -m1 "spire/agent" | awk '{print $2}')
            
            # Register collectors
            {{- range .Values.collectors }}
            spire-server entry create \
              -spiffeID spiffe://{{ $.Values.global.trustDomain }}/{{ .spiffeId }} \
              -parentID $PARENT_ID \
              -selector k8s:ns:{{ $.Values.global.namespace }} \
              -selector k8s:sa:{{ .serviceAccount }} \
              -ttl {{ $.Values.spire.server.svid_ttl | replace "h" "" | mul 60 }} \
              || echo "Entry may exist"
            {{- end }}
            
            # Register engine components
            spire-server entry create \
              -spiffeID spiffe://{{ .Values.global.trustDomain }}/risk-scorer \
              -parentID $PARENT_ID \
              -selector k8s:ns:{{ .Values.global.namespace }} \
              -selector k8s:sa:risk-scorer-sa \
              || echo "Entry may exist"
            
            echo "✅ All identities registered"
```

---

### 14.5 Deploy with Helm Commands

```bash
# Install (first time)
helm install security-training ./helm/security-training \
  --namespace security-training \
  --create-namespace

# Upgrade (after changes)
helm upgrade security-training ./helm/security-training

# Install with dev values
helm install security-training ./helm/security-training \
  -f ./helm/security-training/values-dev.yaml

# Install with prod values  
helm install security-training ./helm/security-training \
  -f ./helm/security-training/values-prod.yaml

# Dry-run to see what would be created
helm install security-training ./helm/security-training --dry-run --debug

# Uninstall
helm uninstall security-training
```

---

### 14.6 Different Environments with Values Files

```yaml
# values-dev.yaml
global:
  namespace: security-training-dev
  
spire:
  server:
    svid_ttl: "5m"    # Short TTL for testing rotation
    log_level: DEBUG

gateway:
  llm:
    backend: lmstudio  # Use local LM Studio in dev
    
lms:
  replicas: 1
```

```yaml
# values-prod.yaml
global:
  namespace: security-training-prod
  
spire:
  server:
    svid_ttl: "1h"     # Longer TTL in prod
    log_level: INFO

gateway:
  llm:
    backend: gemini    # Use Gemini in prod
    
lms:
  replicas: 3          # More replicas in prod
  
database:
  host: prod-postgres.internal
```

---

## 15. SUMMARY: NEW PROJECT STRUCTURE

```
security-awareness-training/
├── README.md
├── docker-compose.yml           # For local dev without K8s
│
├── helm/
│   └── security-training/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-dev.yaml
│       ├── values-prod.yaml
│       └── templates/
│           └── ...              # All K8s templates
│
├── src/
│   ├── base/                    # SHARED CODE (one place!)
│   │   ├── __init__.py
│   │   ├── spiffe_agent.py      # SPIFFEMTLSHandler + BaseSPIFFEAgent
│   │   └── database.py          # Shared DB utilities
│   │
│   ├── collectors/              # Each ~50 lines, not ~500!
│   │   ├── __init__.py
│   │   ├── git_collector.py
│   │   ├── jira_collector.py
│   │   ├── iam_collector.py
│   │   └── siem_collector.py
│   │
│   ├── engine/
│   │   ├── risk_scorer.py
│   │   └── training_recommender.py
│   │
│   ├── gateway/
│   │   └── llm_gateway.py
│   │
│   └── lms/
│       ├── app.py               # Streamlit main
│       └── pages/
│
├── database/
│   ├── schema.sql
│   └── migrations/
│
├── scripts/
│   ├── local-dev.sh             # Start everything locally
│   └── collect-evidence.py
│
├── tests/
│   └── ...
│
└── requirements.txt
```

**Benefits:**
1. **No code duplication** - SPIFFE code in `base/` only
2. **Easy K8s management** - Helm handles everything
3. **Environment flexibility** - `values-dev.yaml` vs `values-prod.yaml`
4. **Auto-registration** - Helm job registers SPIFFE identities
5. **Single source of truth** - Change TTL in one place, applies everywhere

---

## 16. CODE PATTERNS FROM SPIFFE PAPER PROJECT

This section contains proven, working code patterns extracted from the SPIFFE paper project. **Use these as templates to avoid mistakes.**

---

### 13.1 SPIFFEMTLSHandler - The Core Class (PROVEN WORKING)

This is the **exact pattern** that works with py-spiffe. Copy this verbatim.

```python
#!/usr/bin/env python3
"""
Base SPIFFE mTLS Handler - PROVEN WORKING PATTERN
Copy this class into every agent that needs SPIFFE authentication.
"""

import os
import ssl
import tempfile
import time
import logging
from spiffe import WorkloadApiClient
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class SPIFFEMTLSHandler:
    """
    Manages SPIFFE certificates for mTLS (mutual TLS).
    
    Key responsibilities:
    1. Fetch X.509-SVID from SPIRE Agent via Workload API
    2. Write cert/key/bundle to temp files (memory-backed)
    3. Create SSL context for HTTPS server OR client requests
    4. Handle certificate refresh for rotation
    
    IMPORTANT: py-spiffe API varies between versions!
    This code handles both property and method access patterns.
    """
    
    def __init__(self, trust_domain="research.example.org"):
        self.cert_file = None
        self.key_file = None
        self.bundle_file = None
        self.x509_svid = None
        self.spiffe_id = None
        self.trust_domain = trust_domain
        
        logger.info("Initializing SPIFFE mTLS handler...")
        self.refresh_certificates()
    
    def refresh_certificates(self):
        """
        Fetch X.509-SVID certificate from SPIRE Agent.
        Retries up to 5 times with exponential backoff.
        
        LESSON LEARNED: The SPIRE agent may not be ready immediately.
        Always use retry logic with backoff!
        """
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Connecting to SPIRE Workload API (attempt {attempt}/{max_attempts})...")
                
                with WorkloadApiClient() as client:
                    # Get our X.509-SVID certificate
                    self.x509_svid = client.fetch_x509_svid()
                    self.spiffe_id = str(self.x509_svid.spiffe_id)
                    
                    # Get trust bundle for verifying peer certificates
                    trust_bundle = client.fetch_x509_bundles()
                    
                    logger.info(f"✅ Successfully fetched X.509-SVID: {self.spiffe_id}")
                    
                    # Clean up old temp files
                    self._cleanup_temp_files()
                    
                    # Write certificate chain
                    self._write_cert_chain()
                    
                    # Write private key
                    self._write_private_key()
                    
                    # Write trust bundle
                    self._write_trust_bundle(trust_bundle)
                    
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Failed to fetch certificate: {e}")
                
                if attempt < max_attempts:
                    backoff = 2 ** attempt
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    continue
                
                logger.error("❌ Failed to initialize SPIFFE after all attempts!")
                return False
        
        return False
    
    def _cleanup_temp_files(self):
        """Remove old temp files before creating new ones."""
        for f in [self.cert_file, self.key_file, self.bundle_file]:
            if f:
                try:
                    os.unlink(f.name)
                except:
                    pass
    
    def _write_cert_chain(self):
        """
        Write certificate chain to temp file.
        
        LESSON LEARNED: py-spiffe API changed between versions!
        cert_chain can be a property OR a method. Handle both.
        """
        self.cert_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.pem'
        )
        
        cert_chain = self.x509_svid.cert_chain
        if callable(cert_chain):
            cert_chain = cert_chain()
        
        if isinstance(cert_chain, list):
            # List of cryptography X509 certificate objects
            for c in cert_chain:
                self.cert_file.write(
                    c.public_bytes(serialization.Encoding.PEM).decode()
                )
        elif isinstance(cert_chain, bytes):
            self.cert_file.write(cert_chain.decode())
        else:
            self.cert_file.write(cert_chain)
        
        self.cert_file.flush()
        logger.info(f"✅ Certificate written to: {self.cert_file.name}")
    
    def _write_private_key(self):
        """
        Write private key to temp file.
        
        LESSON LEARNED: private_key can return a cryptography key object
        or raw bytes. Handle both cases!
        """
        self.key_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.key'
        )
        
        priv_key = self.x509_svid.private_key
        if callable(priv_key):
            priv_key = priv_key()
        
        if hasattr(priv_key, 'private_bytes'):
            # Cryptography key object - serialize it
            priv_key = priv_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
        elif isinstance(priv_key, bytes):
            priv_key = priv_key.decode()
        
        self.key_file.write(priv_key)
        self.key_file.flush()
        logger.info(f"✅ Private key written to: {self.key_file.name}")
    
    def _write_trust_bundle(self, trust_bundle):
        """
        Write trust bundle (CA certificates) to temp file.
        
        LESSON LEARNED: trust_bundle API is inconsistent!
        Try multiple methods to extract certificates.
        """
        self.bundle_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.pem'
        )
        
        bundles_written = False
        
        # Method 1: Access _bundles directly (internal dict)
        if hasattr(trust_bundle, '_bundles'):
            try:
                bundles_dict = trust_bundle._bundles
                for td, bundle in bundles_dict.items():
                    authorities = bundle.x509_authorities
                    if callable(authorities):
                        authorities = authorities()
                    for cert in authorities:
                        pub_bytes = cert.public_bytes(serialization.Encoding.PEM)
                        if isinstance(pub_bytes, bytes):
                            self.bundle_file.write(pub_bytes.decode())
                        else:
                            self.bundle_file.write(pub_bytes)
                bundles_written = True
                logger.info("✅ Trust bundle extracted via _bundles")
            except Exception as e:
                logger.warning(f"Method 1 (_bundles) failed: {e}")
        
        # Method 2: get_bundle_for_trust_domain() with TrustDomain object
        if not bundles_written and hasattr(trust_bundle, 'get_bundle_for_trust_domain'):
            try:
                from spiffe.spiffe_id.trust_domain import TrustDomain
                td_obj = TrustDomain.parse(self.trust_domain)
                bundle = trust_bundle.get_bundle_for_trust_domain(td_obj)
                if bundle:
                    authorities = bundle.x509_authorities
                    if callable(authorities):
                        authorities = authorities()
                    for cert in authorities:
                        pub_bytes = cert.public_bytes(serialization.Encoding.PEM)
                        if isinstance(pub_bytes, bytes):
                            self.bundle_file.write(pub_bytes.decode())
                        else:
                            self.bundle_file.write(pub_bytes)
                    bundles_written = True
                    logger.info("✅ Trust bundle extracted via get_bundle_for_trust_domain")
            except Exception as e:
                logger.warning(f"Method 2 (get_bundle_for_trust_domain) failed: {e}")
        
        if not bundles_written:
            logger.error(f"❌ Could not extract trust bundle! Type: {type(trust_bundle)}")
        
        self.bundle_file.flush()
    
    def create_server_ssl_context(self):
        """
        Create SSL context for HTTPS SERVER with client cert verification.
        This enables mTLS - server requires client to present certificate.
        """
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=self.cert_file.name,
            keyfile=self.key_file.name
        )
        context.load_verify_locations(cafile=self.bundle_file.name)
        context.verify_mode = ssl.CERT_REQUIRED  # CRITICAL for mTLS!
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        logger.info("✅ Server SSL context created (mTLS enabled)")
        return context
    
    def make_mtls_request(self, url, json_data, timeout=30):
        """
        Make HTTPS request WITH client certificate (mTLS client).
        
        LESSON LEARNED: SPIFFE uses URI SANs, not hostname SANs!
        We must disable hostname verification but still send our cert.
        """
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        return requests.post(
            url,
            json=json_data,
            cert=(self.cert_file.name, self.key_file.name),
            verify=False,  # Skip hostname check (SPIFFE uses URI SAN)
            timeout=timeout
        )
    
    def get_certificate_info(self):
        """Return certificate info for /certificate endpoint."""
        if self.x509_svid:
            cert = self.x509_svid.leaf
            return {
                'spiffe_id': self.spiffe_id,
                'trust_domain': self.trust_domain,
                'has_certificate': True,
                'mtls_enabled': True,
                'not_valid_before': cert.not_valid_before_utc.isoformat(),
                'not_valid_after': cert.not_valid_after_utc.isoformat(),
                'serial_number': str(cert.serial_number),
            }
        return {'has_certificate': False, 'mtls_enabled': False}
```

---

### 13.2 Extracting Peer SPIFFE ID from Client Certificate

```python
def extract_peer_spiffe_id(self):
    """
    Extract SPIFFE ID from peer's certificate during mTLS.
    Called in HTTP handler after TLS handshake.
    
    The SPIFFE ID is in the certificate's SAN as a URI:
    spiffe://research.example.org/pipeline-orchestrator
    """
    try:
        # Get peer certificate from TLS connection
        peer_cert = self.connection.getpeercert()
        
        if not peer_cert:
            logger.error("❌ No peer certificate found!")
            return None
        
        # Extract Subject Alternative Name (SAN)
        san = peer_cert.get('subjectAltName', [])
        
        # Find SPIFFE ID (URI starting with spiffe://)
        spiffe_ids = [
            uri for typ, uri in san 
            if typ == 'URI' and uri.startswith('spiffe://')
        ]
        
        if not spiffe_ids:
            logger.error(f"❌ No SPIFFE ID in certificate! SAN: {san}")
            return None
        
        return spiffe_ids[0]
        
    except Exception as e:
        logger.error(f"❌ Failed to extract SPIFFE ID: {e}")
        return None
```

---

### 13.3 Identity-Based Authorization Pattern

```python
def authorize_peer(self, peer_spiffe_id):
    """
    Authorize peer based on SPIFFE ID.
    
    LESSON LEARNED: Be explicit about allowed callers!
    This replaces API key validation with identity validation.
    """
    # Define who is allowed to call this agent
    allowed_callers = [
        'spiffe://research.example.org/pipeline-orchestrator',
        # Add more as needed
    ]
    
    if peer_spiffe_id in allowed_callers:
        logger.info(f"✅ Authorized: {peer_spiffe_id}")
        return True
    else:
        logger.error(f"❌ UNAUTHORIZED: {peer_spiffe_id}")
        logger.error(f"   Allowed: {allowed_callers}")
        return False
```

---

### 13.4 LLM Gateway Pattern (Multi-Provider)

```python
"""
LLM Gateway - Supports multiple backends (LM Studio local, Gemini cloud)

LESSON LEARNED: Isolate API keys to the gateway only!
AI agents never see the API key - they authenticate via SPIFFE.
"""

import os
import requests

LLM_BACKEND = os.getenv('LLM_BACKEND', 'gemini').lower()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

def call_gemini(messages, temperature=0.3, max_tokens=500):
    """Call Google Gemini API."""
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    
    # Convert OpenAI-style messages to Gemini format
    contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        if role == 'system':
            system_instruction = content
        elif role == 'user':
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == 'assistant':
            contents.append({"role": "model", "parts": [{"text": content}]})
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    
    response = requests.post(
        f"{url}?key={GEMINI_API_KEY}",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"Gemini error: {response.status_code} - {response.text}")
    
    result = response.json()
    return {
        "content": result['candidates'][0]['content']['parts'][0]['text'],
        "model": GEMINI_MODEL,
        "backend": "gemini"
    }
```

---

## 14. KUBERNETES YAML PATTERNS (PROVEN WORKING)

### 14.1 SPIRE Server Configuration

```yaml
# Key settings that WORK:
server.conf: |
  server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "research.example.org"
    data_dir = "/run/spire/data"
    log_level = "DEBUG"  # Use DEBUG during development!
    ca_ttl = "24h"
    default_x509_svid_ttl = "1h"  # 1 hour is good balance
  }
  
  plugins {
    DataStore "sql" {
      plugin_data {
        database_type = "sqlite3"
        connection_string = "/run/spire/data/datastore.sqlite3"
      }
    }
    
    NodeAttestor "k8s_psat" {
      plugin_data {
        clusters = {
          "demo-cluster" = {
            service_account_allow_list = ["spiffe-research:spire-agent"]
          }
        }
      }
    }
  }
```

### 14.2 SPIRE Agent Configuration

```yaml
# CRITICAL: These settings are required!
agent.conf: |
  agent {
    data_dir = "/run/spire"
    log_level = "DEBUG"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/opt/spire/sockets/agent.sock"
    trust_domain = "research.example.org"
    insecure_bootstrap = true  # OK for single-cluster demo
  }
  
  plugins {
    NodeAttestor "k8s_psat" {
      plugin_data {
        cluster = "demo-cluster"
      }
    }
    
    WorkloadAttestor "k8s" {
      plugin_data {
        skip_kubelet_verification = true  # Required for Docker Desktop!
      }
    }
  }

# DaemonSet MUST have these:
spec:
  template:
    spec:
      hostPID: true      # REQUIRED for workload attestation!
      hostNetwork: true  # Required for socket access
```

### 14.3 AI Agent Deployment Pattern

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-agent
  namespace: spiffe-research
spec:
  template:
    spec:
      serviceAccountName: my-agent-sa  # MUST match SPIRE registration!
      containers:
      - name: my-agent
        image: python:3.11-slim
        env:
        - name: SPIFFE_ENDPOINT_SOCKET
          value: "unix:///opt/spire/sockets/agent.sock"
        volumeMounts:
        - name: spire-agent-socket
          mountPath: /opt/spire/sockets
          readOnly: true
      volumes:
      - name: spire-agent-socket
        hostPath:
          path: /opt/spire/sockets
          type: DirectoryOrCreate
```

---

## 15. LESSONS LEARNED & MISTAKES TO AVOID

### 15.1 SPIRE Registration Errors

**Problem:** "no identity issued" or "SVID not found"

**Root Cause:** Parent ID in registration doesn't match actual agent ID.

**Solution:** Auto-detect agent parent ID from logs:
```bash
AGENT_PARENT_ID=$(kubectl logs -n spiffe-research "$SPIRE_AGENT_POD" | \
    grep -m1 -Eo "spiffe://research.example.org/spire/agent/k8s_psat/demo-cluster/[0-9a-f-]+" || true)
```

### 15.2 py-spiffe API Version Issues

**Problem:** Code works on one machine, fails on another.

**Root Cause:** py-spiffe API changed between versions (property vs method).

**Solution:** Always check if attribute is callable:
```python
cert_chain = self.x509_svid.cert_chain
if callable(cert_chain):
    cert_chain = cert_chain()
```

### 15.3 mTLS Hostname Verification

**Problem:** SSL certificate verify failed - hostname mismatch.

**Root Cause:** SPIFFE uses URI SANs, not hostname SANs.

**Solution:** Disable hostname verification for mTLS client requests:
```python
requests.post(url, cert=(cert, key), verify=False)
```

### 15.4 SPIRE Agent Socket Not Found

**Problem:** Agent can't connect to Workload API.

**Root Cause:** Socket path not mounted or wrong path.

**Solution:**
1. Check env var: `SPIFFE_ENDPOINT_SOCKET=unix:///opt/spire/sockets/agent.sock`
2. Check volume mount exists
3. Verify SPIRE agent DaemonSet has `hostPID: true`

### 15.5 Certificate Rotation Breaking Connections

**Problem:** Connections fail after cert rotation.

**Root Cause:** Using old certificate files after rotation.

**Solution:** Implement certificate refresh in a background thread:
```python
import threading

def cert_refresh_loop(handler, interval=1800):  # 30 min
    while True:
        time.sleep(interval)
        handler.refresh_certificates()

# Start at agent startup
threading.Thread(target=cert_refresh_loop, args=(mtls_handler,), daemon=True).start()
```

### 15.6 Docker Desktop Kubernetes Issues

**Problem:** Workload attestation fails on Docker Desktop.

**Solution:** Add to SPIRE agent config:
```yaml
WorkloadAttestor "k8s" {
  plugin_data {
    skip_kubelet_verification = true
  }
}
```

---

## 16. DEPLOYMENT SCRIPT TEMPLATE

```bash
#!/bin/bash
# deploy.sh - Complete deployment script

set -e

echo "🚀 Deploying SPIFFE Security Training System"

# Step 1: Create namespace
kubectl create namespace security-training --dry-run=client -o yaml | kubectl apply -f -

# Step 2: Deploy SPIRE Server
kubectl apply -f k8s/spire/spire-server.yaml
kubectl wait --for=condition=ready pod -l app=spire-server -n security-training --timeout=120s

# Step 3: Deploy SPIRE Agent
kubectl apply -f k8s/spire/spire-agent.yaml
sleep 10  # Give agent time to connect
kubectl wait --for=condition=ready pod -l app=spire-agent -n security-training --timeout=120s

# Step 4: Register workload identities
SPIRE_SERVER_POD=$(kubectl get pod -n security-training -l app=spire-server -o jsonpath='{.items[0].metadata.name}')
SPIRE_AGENT_POD=$(kubectl get pod -n security-training -l app=spire-agent -o jsonpath='{.items[0].metadata.name}')

# Auto-detect agent parent ID (CRITICAL!)
AGENT_PARENT_ID=$(kubectl logs -n security-training "$SPIRE_AGENT_POD" | \
    grep -m1 -Eo "spiffe://security-training.example.org/spire/agent/k8s_psat/demo-cluster/[0-9a-f-]+" || true)

if [ -z "$AGENT_PARENT_ID" ]; then
    echo "⚠️  Could not auto-detect agent parent ID, using default"
    AGENT_PARENT_ID="spiffe://security-training.example.org/spire/agent/k8s_psat/demo-cluster/default"
fi

echo "📝 Registering identities with parent: $AGENT_PARENT_ID"

# Register each workload
for workload in git-collector jira-collector iam-collector risk-scorer llm-gateway lms-api; do
    kubectl exec -n security-training "$SPIRE_SERVER_POD" -- \
        /opt/spire/bin/spire-server entry create \
        -spiffeID spiffe://security-training.example.org/${workload} \
        -parentID ${AGENT_PARENT_ID} \
        -selector k8s:ns:security-training \
        -selector k8s:sa:${workload}-sa \
        -ttl 3600 || echo "Entry may exist"
done

# Step 5: Deploy application
kubectl apply -f k8s/database/
kubectl apply -f k8s/collectors/
kubectl apply -f k8s/engine/
kubectl apply -f k8s/lms/

echo "✅ Deployment complete!"
kubectl get pods -n security-training
```

---

## 17. QUICK REFERENCE

### Environment Variables
```bash
# Required for every SPIFFE-authenticated agent
SPIFFE_ENDPOINT_SOCKET=unix:///opt/spire/sockets/agent.sock

# LLM Gateway specific
LLM_BACKEND=gemini  # or 'lmstudio'
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash

# Database
DATABASE_URL=postgresql://user:pass@db:5432/security_training
```

### Python Dependencies
```txt
# requirements.txt
spiffe>=0.2.2
cryptography>=41.0.0
requests>=2.31.0
flask>=3.0.0
psycopg2-binary>=2.9.9
streamlit>=1.29.0
google-generativeai>=0.3.0
```

### Key File Locations
```
/opt/spire/sockets/agent.sock  - SPIRE Workload API socket
/tmp/*.pem                      - Temp cert files (auto-generated)
/tmp/*.key                      - Temp key files (auto-generated)
```

---

*This document contains all context needed to start the new repository. Copy this file to your new project folder as `ARCHITECTURE.md` or `PROJECT_CONTEXT.md`.*
