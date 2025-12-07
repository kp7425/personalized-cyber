# Risk Scoring Model: Formal Mathematical Specification

## IEEE Paper: AI-Driven Personalized Security Awareness Training

**Author**: PhD Candidate, Dakota State University  
**Domain**: Cybersecurity + Applied Mathematics + Machine Learning

---

## 1. Notation and Definitions

### 1.1 Set Definitions

Let:
- **U** = {u₁, u₂, ..., uₙ} be the set of employees, where n = |U| = 50
- **S** = {s₁, s₂, ..., sₘ} be the set of data sources, where S = {Git, IAM, SIEM, Jira, Training}
- **R** = {r₁, r₂, ..., rₖ} be the set of job roles, where k = 8
- **T** = [0, τ] be the observation time window, where τ = 30 days
- **E_s** = {e₁, e₂, ..., eₚ} be the set of event types for source s

### 1.2 Function Definitions

| Symbol | Domain → Codomain | Description |
|--------|-------------------|-------------|
| ρ: U → R | Employee → Role | Maps employee to their job role |
| w_s: R → [0,1] | Role × Source → Weight | Weight for source s given role r |
| α_e: E_s → [0,1] | Event Type → Severity | Severity weight for event type e |
| N(u, e, t): U × E × T → ℤ⁺ | Employee × Event × Time → Count | Event count function |

---

## 2. Individual Risk Score Model

### 2.1 Source-Level Risk Score

For employee u ∈ U and source s ∈ S over time window [0, τ]:

```
                    ⎛  τ                          ⎞
R_s(u, τ) = min⎜1, ∫  Σ  α_e · δ(t - t_e) dt⎟
                    ⎝  0 e∈E_s                    ⎠
```

**Discrete approximation** (implemented):

```
R_s(u, τ) = min(1.0, Σ_{e ∈ E_s} α_e · N(u, e, τ))
```

Where:
- α_e ∈ [0, 1] is the severity weight for event type e
- N(u, e, τ) is the count of event e for user u in window τ
- The min(1.0, ·) ensures normalization to [0, 1]

### 2.2 Weighted Aggregate Risk Score

**Definition 1 (Individual Risk Score):**

For employee u with role ρ(u) = r:

```
                    m
R_user(u, τ) = Σ  w_{s,r} · R_s(u, τ)
                   s=1
```

Subject to the constraint:

```
Σ_{s ∈ S} w_{s,r} = 1  ∀r ∈ R  (weights sum to unity)
```

### 2.3 Role-Based Weight Matrix

**Definition 2 (Weight Matrix):**

Let **W** ∈ ℝ^{k×m} be the role-source weight matrix:

```
        ┌                                      ┐
        │  w_Git   w_IAM   w_SIEM   w_Training │
W =     │   ·       ·       ·         ·        │
        │   ·       ·       ·         ·        │
        └                                      ┘
```

| Role r | w_{Git,r} | w_{IAM,r} | w_{SIEM,r} | w_{Train,r} | Σ |
|--------|-----------|-----------|------------|-------------|---|
| Backend Dev | 0.35 | 0.25 | 0.20 | 0.20 | 1.0 |
| Frontend Dev | 0.30 | 0.20 | 0.25 | 0.25 | 1.0 |
| DevOps Eng | 0.25 | 0.40 | 0.15 | 0.20 | 1.0 |
| Data Eng | 0.20 | 0.45 | 0.15 | 0.20 | 1.0 |
| Data Analyst | 0.15 | 0.35 | 0.20 | 0.30 | 1.0 |
| SRE | 0.20 | 0.40 | 0.20 | 0.20 | 1.0 |
| DevSecOps | 0.25 | 0.30 | 0.25 | 0.20 | 1.0 |
| Cloud Security | 0.20 | 0.30 | 0.30 | 0.20 | 1.0 |

### 2.4 Event Severity Weights

**Definition 3 (Severity Function):**

```
α: E → [0, 1]
```

| Source | Event e | α_e | Rationale |
|--------|---------|-----|-----------|
| Git | secrets_committed | 0.30 | Critical exposure |
| Git | force_push | 0.10 | Process bypass |
| Git | vulnerable_deps | 0.15 | Supply chain risk |
| IAM | privilege_escalation | 0.25 | Access abuse |
| IAM | service_account_key | 0.20 | Credential exposure |
| IAM | off_hours_access | 0.15 | Anomalous behavior |
| SIEM | malware_detection | 0.30 | Active threat |
| SIEM | phishing_click | 0.20 | Human factor |
| Jira | overdue_sec_ticket | 0.10 | Training debt |

---

## 3. Cross-System Correlation (Behavioral Fusion)

### 3.1 Correlation Multiplier

**Definition 4 (Correlation Function):**

Let C(u) be the correlation multiplier:

```
           ⎧ 2.0   if Compromised(u)
           ⎪
C(u) =     ⎨ 1.5   if InsiderThreat(u)
           ⎪
           ⎩ 1.0   otherwise
```

Where:

**Compromised Pattern:**
```
Compromised(u) ≡ (N(u, git_commit, τ) = 0) ∧ 
                 (N(u, iam_events, τ) > 20) ∧ 
                 (N(u, siem_alerts, τ) > 3)
```

**Insider Threat Pattern:**
```
InsiderThreat(u) ≡ (off_hours_access(u) = true) ∧ 
                   (large_data_export(u) = true) ∧ 
                   (approved_jira_ticket(u) = false)
```

### 3.2 Adjusted Individual Risk

**Theorem 1 (Bounded Risk):**

The adjusted risk score:

```
R̃_user(u, τ) = min(1.0, R_user(u, τ) · C(u))
```

satisfies R̃_user(u, τ) ∈ [0, 1] for all u ∈ U.

*Proof:* Since R_user(u, τ) ∈ [0, 1] by construction and C(u) ≥ 1.0, the product may exceed 1.0. The min(1.0, ·) operator ensures the upper bound. The lower bound holds as both factors are non-negative. ∎

---

## 4. Organization-Level Risk Score

### 4.1 Aggregate Risk Function

**Definition 5 (Organization Risk):**

```
R_org = α · R̄ + β · R_max + γ · (|H| / n)
```

Where:
- R̄ = (1/n) Σ_{u ∈ U} R̃_user(u, τ)  — Mean individual risk
- R_max = max_{u ∈ U} R̃_user(u, τ)  — Maximum exposure
- H = {u ∈ U : R̃_user(u, τ) ≥ θ_high}  — High-risk population
- θ_high = 0.6  — High-risk threshold
- (α, β, γ) = (0.4, 0.3, 0.3)  — Component weights

**Constraint:**
```
α + β + γ = 1  (convex combination)
```

### 4.2 Risk Level Classification

**Definition 6 (Risk Level Function):**

```
           ⎧ CRITICAL    if R_org ≥ 0.7
           ⎪
L(R_org) = ⎨ HIGH        if 0.5 ≤ R_org < 0.7
           ⎪
           ⎩ MEDIUM      if 0.3 ≤ R_org < 0.5
             LOW         if R_org < 0.3
```

---

## 5. Training Frequency Derivation

### 5.1 Risk-to-Frequency Mapping

**Definition 7 (Training Frequency):**

Let f: [0, 1] → {Q, M, W, I} map risk to training frequency:

```
           ⎧ Quarterly (Q)     if R < 0.3
           ⎪
f(R) =     ⎨ Monthly (M)       if 0.3 ≤ R < 0.6
           ⎪
           ⎩ Weekly (W)        if 0.6 ≤ R < 0.8
             Immediate (I)     if R ≥ 0.8
```

### 5.2 Expected Training Load

**Proposition 1:**

Given the empirical distribution of R_user, the expected training frequency distribution is:

| Frequency | Expected % | Actual (n=50) |
|-----------|------------|---------------|
| Quarterly | 25% | 2% |
| Monthly | 45% | 48% |
| Weekly | 25% | 42% |
| Immediate | 5% | 8% |

---

## 6. Temporal Dynamics

### 6.1 Time-Varying Risk with Exponential Decay

**Definition 8 (Temporal Risk):**

For real-time analysis with decay constant λ > 0:

```
                      τ
R_s^{(t)}(u, τ) = ∫  r_s(u, t) · e^{-λ(τ-t)} dt
                      0
```

Where:
- λ = ln(2) / t_{1/2}  — Decay constant
- t_{1/2} = 7 days  — Half-life (events contribute 50% after 7 days)

### 6.2 Temporal Multiplier (Spike Detection)

**Definition 9 (Week Multiplier):**

```
           ⎧ 1.0   if t ∈ [0, 7] ∪ [7, 14]    (Weeks 1-2: Baseline)
           ⎪
M(t) =     ⎨ 3.0   if t ∈ [14, 21]            (Week 3: Deadline spike)
           ⎪
           ⎩ 0.8   if t ∈ [21, 30]            (Week 4: Recovery)
```

---

## 7. Statistical Validation Framework

### 7.1 Ground Truth and Metrics

Let G: U → {LOW, MEDIUM, HIGH, CRITICAL} be the expert-labeled ground truth.

**Precision:**
```
P = |{u : Ĝ(u) = HIGH ∧ G(u) = HIGH}| / |{u : Ĝ(u) = HIGH}|
```

**Recall:**
```
R = |{u : Ĝ(u) = HIGH ∧ G(u) = HIGH}| / |{u : G(u) = HIGH}|
```

**F1 Score:**
```
F1 = 2PR / (P + R)
```

**Target:** F1 ≥ 0.85

### 7.2 Empirical Results (n = 50)

| Metric | Value | 
|--------|-------|
| Organization Risk (R_org) | 0.647 |
| Mean Individual Risk (R̄) | 0.604 |
| Max Individual Risk | 0.85 |
| Min Individual Risk | 0.28 |
| High Risk Count (|H|) | 25 |
| Critical Count | 6 |
| Standard Deviation | 0.15 |

### 7.3 Distribution Analysis

**Hypothesis:** Risk scores follow approximately normal distribution.

```
R_user ~ N(μ, σ²)  where μ ≈ 0.60, σ ≈ 0.15
```

**Kolmogorov-Smirnov Test:**
- H₀: R_user follows N(0.60, 0.15²)
- Expected: p > 0.05 (fail to reject normality)

---

## 8. Population Distribution

### 8.1 Role Distribution

| Role | Count n_r | Proportion | E[R] per role |
|------|-----------|------------|---------------|
| Backend Developer | 12 | 24% | 0.55 |
| Frontend Developer | 8 | 16% | 0.53 |
| DevOps Engineer | 8 | 16% | 0.71 |
| DevSecOps Engineer | 4 | 8% | 0.25 |
| Cloud Security Analyst | 3 | 6% | 0.20 |
| Data Analyst | 6 | 12% | 0.45 |
| Data Engineer | 6 | 12% | 0.68 |
| SRE | 3 | 6% | 0.67 |
| **Total** | **50** | **100%** | **0.60** |

### 8.2 Control Groups

- **DevSecOps + Cloud Security** (n=7): Expected R < 0.3 (low risk control)
- **Validation:** Ensures formula doesn't over-penalize security professionals

---

## 9. Algorithm Complexity

### 9.1 Per-User Risk Calculation

**Time Complexity:**
```
O(|S| × max|E_s|) = O(m × p)
```

Where m = 5 sources, p ≤ 10 event types per source.

### 9.2 Organization Risk Calculation

**Time Complexity:**
```
O(n)  for aggregation over n users
```

### 9.3 Total System Complexity

```
O(n × m × p) ≈ O(50 × 5 × 10) = O(2500) per refresh cycle
```

---

## 10. Implementation Mapping

| Mathematical Symbol | Code Variable | Type |
|---------------------|---------------|------|
| R_s(u, τ) | `source_scores[source]` | float |
| w_{s,r} | `ROLE_WEIGHTS[role][source]` | float |
| α_e | `EVENT_SEVERITY[source][event]` | float |
| C(u) | `_detect_correlation_patterns()` | float |
| R_user(u, τ) | `overall_risk_score` | float |
| R_org | `organization_risk_score` | float |
| f(R) | `_get_training_frequency()` | str |

---

## References

1. NIST SP 800-30: Risk Assessment Methodology
2. FAIR (Factor Analysis of Information Risk) Framework
3. CVSS v3.1: Common Vulnerability Scoring System
4. ISO 27001: Information Security Risk Management
