# Synthetic Data Specification (IEEE Paper Version)

## Overview
This document defines the synthetic data model for the IEEE paper simulation. The goal is to generate realistic, diverse employee profiles and their behavioral metadata across multiple enterprise systems.

---

## 1. Employee Population (50 Users)

| Role | Count | Cloud | Expected Risk Level |
|------|-------|-------|---------------------|
| Developer (Backend) | 12 | AWS | High (0.6-0.9) |
| Developer (Frontend) | 8 | AWS | Medium (0.4-0.6) |
| DevOps Engineer | 8 | AWS + GCP | High (0.6-0.8) |
| DevSecOps Engineer | 4 | AWS + GCP | Low (0.1-0.3) — Control |
| Cloud Security Analyst | 3 | AWS + GCP | Very Low (0.0-0.2) — Control |
| Data Analyst | 6 | GCP | Medium (0.3-0.5) |
| Data Engineer | 6 | GCP | High (0.5-0.8) |
| SRE | 3 | AWS + GCP | Variable (0.2-0.9) |
| **Total** | **50** | | |

---

## 2. Cloud Services Per Role

### AWS Services
| Service | Roles That Use It | Risk Events |
|---------|-------------------|-------------|
| IAM | All | AssumeRole, CreateAccessKey, AttachUserPolicy |
| S3 | DevOps, Data Eng, SRE | Public bucket, large downloads |
| EC2 | Backend Dev, DevOps | Open security groups, unencrypted EBS |
| RDS | Backend Dev | Public snapshots, weak passwords |
| Lambda | Backend Dev, DevOps | Overpermissioned roles |
| EKS | DevOps, SRE | Privileged pods, exposed API server |

### GCP Services
| Service | Roles That Use It | Risk Events |
|---------|-------------------|-------------|
| IAM | All | SetIamPolicy, CreateServiceAccountKey |
| BigQuery | Data Analyst, Data Eng | Large exports, external sharing |
| GCS | Data Eng, DevOps | Public buckets, allUsers access |
| GKE | DevOps, SRE | Privileged pods, Workload Identity bypass |
| Cloud Functions | Backend Dev | Overpermissioned service accounts |

---

## 3. Risk Scoring Formula (Mathematical Definition)

### Generalized Risk Score (Extensible Form)

The overall risk score is computed as a weighted sum over all data sources:

```
R_overall(u, t) = Σᵢ wᵢ(role) × Rᵢ(u, t)

Where:
  u = employee (workday_id)
  t = time window (e.g., 30 days)
  i = data source index (Git, IAM, SIEM, Jira, Training, ...)
  wᵢ(role) = weight for source i, dependent on employee role
  Rᵢ(u, t) = normalized risk score [0,1] from source i
```

### Continuous Form (For Time-Series Analysis)

For real-time risk trending, we use exponential decay weighting:

```
Rᵢ(u, T) = (1/T) ∫₀ᵀ rᵢ(u, t) × e^(-λ(T-t)) dt

Where:
  rᵢ(u, t) = instantaneous risk signal at time t
  λ = decay constant (older events contribute less)
  T = current time
```

### Discrete Implementation (What We Code)

```python
def calculate_risk(user_id, time_window_days=30):
    sources = ['git', 'iam', 'siem', 'jira', 'training']  # Extensible
    weights = get_role_weights(user_id)  # Role-based
    
    R_overall = sum(
        weights[src] * normalize(get_source_risk(user_id, src, time_window_days))
        for src in sources
        if src in weights
    )
    
    # Apply correlation multiplier
    R_overall *= get_correlation_multiplier(user_id)
    
    return min(1.0, R_overall)
```

### Adding New Data Sources (Future Extensibility)

To add a new source (e.g., Slack, GitHub Copilot, EDR):

```python
# 1. Add to sources list
sources = ['git', 'iam', 'siem', 'jira', 'training', 'slack', 'copilot', 'edr']

# 2. Define weight in role config
role_weights['backend_dev']['slack'] = 0.05
role_weights['backend_dev']['copilot'] = 0.10

# 3. Implement collector
class SlackCollector(BaseSPIFFEAgent):
    def collect(self, user_id):
        # Return risk events from Slack
```

### Component Score Functions

Each source computes a normalized [0,1] score:

```
Rₛ(u,t) = min(1.0, Σⱼ αⱼ × count(eventⱼ, u, t))

Where:
  j = event type index within source s
  αⱼ = severity weight for event type j
  count() = number of events in time window
```

| Source | Event Types (j) | Severity Weight (αⱼ) |
|--------|-----------------|---------------------|
| Git | secrets_committed | 0.30 |
| Git | force_push | 0.10 |
| Git | vulnerable_deps | 0.15 |
| IAM | privilege_escalation | 0.25 |
| IAM | service_account_key | 0.20 |
| IAM | off_hours_access | 0.15 |
| SIEM | malware_detection | 0.30 |
| SIEM | phishing_click | 0.15 |
| Jira | overdue_sec_ticket | 0.10 |

### Role-Based Weight Matrix (wᵢ)

| Role | w_git | w_iam | w_siem | w_training |
|------|-------|-------|--------|------------|
| Developer (Backend) | 0.35 | 0.25 | 0.20 | 0.20 |
| Developer (Frontend) | 0.30 | 0.20 | 0.25 | 0.25 |
| DevOps Engineer | 0.25 | 0.40 | 0.15 | 0.20 |
| Data Engineer | 0.20 | 0.45 | 0.15 | 0.20 |
| Data Analyst | 0.15 | 0.35 | 0.20 | 0.30 |
| SRE | 0.20 | 0.40 | 0.20 | 0.20 |
| DevSecOps | 0.25 | 0.30 | 0.25 | 0.20 |
| Cloud Security | 0.20 | 0.30 | 0.30 | 0.20 |

### Cross-System Correlation Multiplier

```
If (off_hours_IAM_access AND large_data_export AND no_jira_ticket):
    R_overall = R_overall × 1.5  # Insider threat pattern

If (no_git_activity AND high_IAM_activity AND SIEM_alerts > 3):
    R_overall = R_overall × 2.0  # Compromised account pattern
```

### Training Frequency Derivation

```
If R_overall < 0.30:  Training_Frequency = "Quarterly"
If R_overall 0.30-0.60:  Training_Frequency = "Monthly"
If R_overall > 0.60:  Training_Frequency = "Weekly/Sprint"
If R_overall > 0.80:  Training_Frequency = "Immediate + Manager Alert"
```

---

## 4. Temporal Risk Patterns (30-Day Simulation)

| Pattern Type | Roles | Timeline | Description |
|--------------|-------|----------|-------------|
| **Deadline Spike** | Backend Dev, DevOps | Days 15-18 | 3x normal risky events during sprint end |
| **Post-Incident Behavior** | SRE | Days 5-7 | Break-glass usage, then returns to normal |
| **Gradual Improvement** | Frontend Dev | Days 1→30 | Starts 0.6 risk, training reduces to 0.3 |
| **Consistent Low Risk** | DevSecOps, Security | All 30 days | Flat 0.1-0.2 throughout (control group) |
| **New Employee Ramp** | Data Analyst | Days 1-14 | High IAM activity (learning), normalizes |

### Weekly Event Distribution

```
Week 1: Baseline establishment (normal activity)
Week 2: Steady state (slight variations)
Week 3: SPIKE WEEK - Deadlines, incidents, hotfixes
Week 4: Recovery - Cleanup, training completion, risk reduction
```

---

## 5. Cross-System Risk Indicators

| Pattern | Git | Jira | IAM | SIEM | Interpretation | Risk Multiplier |
|---------|-----|------|-----|------|----------------|-----------------|
| **Negligent Developer** | Secrets | "Fix later" | Root creds | None | Isolated mistakes | 1.0x |
| **Insider Threat** | Large exports | "Won't fix" | Off-hours | Failed auth | Suspicious correlation | 1.5x |
| **Compromised Account** | None | None | High activity | Many alerts | Behavioral anomaly | 2.0x |
| **Burnout Pattern** | Force pushes | Overdue tickets | Normal | None | Process shortcuts | 1.2x |

---

## 6. Ground Truth Labels (For Validation)

### Expert-Labeled Subset (10 Employees)

| Employee ID | Role | True Risk | Justification |
|-------------|------|-----------|---------------|
| EMP001 | Backend Dev | HIGH | 5 secrets + 3 force pushes + overdue tickets |
| EMP007 | Frontend Dev | MEDIUM | 2 vulnerable deps, completes training |
| EMP015 | DevSecOps | LOW | Control - no risky events, fast ticket resolution |
| EMP023 | SRE | VARIABLE | 0.85 during incident (Day 6), 0.25 otherwise |
| EMP031 | Data Analyst | MEDIUM | Large exports but with approved Jira ticket |
| EMP042 | DevOps | HIGH | Open security groups + admin IAM usage |
| EMP048 | CloudSec | VERY LOW | Control - monitor-only access pattern |

### Validation Metrics

```
Precision = TP / (TP + FP)  # High-risk predictions that are actually high-risk
Recall = TP / (TP + FN)     # High-risk employees correctly identified
F1 = 2 × (Precision × Recall) / (Precision + Recall)

Target: F1 > 0.85 against expert labels
```

---

## 7. Legitimate High-Activity Scenarios (False Positive Handling)

| Scenario | Events Generated | Why It's Safe | System Handling |
|----------|-----------------|---------------|-----------------|
| **On-call SRE** | 50 IAM events/2hr | Active incident | If SIEM shows incident, suppress IAM risk |
| **Migration Project** | 200 BigQuery exports | Planned migration | Jira "MIGRATION" tag whitelists activity |
| **Security Audit** | Analyst queries all roles | Doing their job | Role-based exception for Security team |
| **New Employee Onboarding** | High IAM activity Week 1 | Learning systems | Tenure < 14 days reduces IAM weight |

---

## 8. Risk → Training Mapping (LLM Prompt Engineering)

| Risk Pattern Detected | LLM Prompt Context | Expected Training Output |
|----------------------|---------------------|--------------------------|
| 3+ secrets in code | "Employee committed API keys in last 7 days" | 5-min module: "Using AWS Secrets Manager" |
| Open 0.0.0.0/0 SG | "Employee exposed services to internet" | Interactive lab: "Least-privilege network design" |
| 10+ overdue sec tickets | "Employee deprioritizes security tasks" | Case study: "Equifax breach timeline" |
| BigQuery large export | "Employee exported 10GB from prod tables" | Policy reminder: "Data classification requirements" |
| Off-hours IAM + exports | "Suspicious access pattern detected" | Mandatory: "Insider threat awareness" |

---

## 9. Expected Results (For IEEE Paper)

### Risk Score Distribution
- **Mean**: 0.45
- **Std Dev**: 0.25
- **Distribution**: Approximately normal with slight right skew (more medium-high risk users)

### Training Frequency Distribution
| Frequency | % of Population |
|-----------|-----------------|
| Quarterly | 25% |
| Monthly | 45% |
| Weekly | 25% |
| Immediate | 5% |

### Key Metrics to Report
1. **Risk Detection Latency**: Spike detected within 1 hour of event
2. **Training Personalization Accuracy**: 92% match to expert-recommended modules
3. **Compliance Improvement**: 15% reduction in risk score post-training (simulated)
4. **Cross-System Correlation Detection**: 87% of insider threat patterns identified

---

## 10. Implementation Checklist

- [ ] Update `historical_data_generator.py` with 8 roles
- [ ] Add temporal spike patterns (Week 3 = high risk)
- [ ] Implement role-based weight configuration
- [ ] Add cross-system correlation detection
- [ ] Generate ground truth labels for validation subset
- [ ] Test with 50 users and verify distribution matches expected
