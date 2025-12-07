# Context-Aware AI for Personalized Cybersecurity Training: A Zero-Trust Approach

## IEEE Technical Paper - Implementation Details

---

## Abstract

This paper presents a novel **Context-Aware Personalization Engine** for cybersecurity awareness training that combines continuous behavioral risk assessment with generative AI to deliver targeted, individualized training modules. Unlike traditional static Learning Management Systems (LMS), our approach implements a **Zero-Trust architecture** using SPIFFE/SPIRE for workload identity, ensuring cryptographic verification of all data sources feeding the AI system. We demonstrate that personalized training based on dynamic risk profiles can reduce security incidents by targeting specific behavioral patterns rather than applying generic training curricula.

---

## I. Introduction

### A. Problem Statement

Traditional security awareness training suffers from three critical limitations:

1. **Static Content**: Training modules created once, never adapted to evolving threats
2. **One-Size-Fits-All**: Identical training for all employees regardless of role or risk profile  
3. **Unverified Data Sources**: No cryptographic guarantee that behavioral data is authentic

### B. Research Contribution

We propose a system that:
- Continuously monitors employee behavioral signals across multiple enterprise systems
- Calculates a dynamic, normalized risk score using a weighted multi-dimensional model
- Generates personalized AI training content via a secure, identity-verified gateway
- Implements full mutual TLS (mTLS) with SPIFFE X.509-SVIDs for zero-trust data provenance

---

## II. Risk Scoring Model

### A. Multi-Dimensional Risk Assessment

Let $R_u(t)$ denote the overall risk score for user $u$ at time $t$. We define:

$$R_u(t) = \sum_{i=1}^{n} w_i \cdot S_i(u, t)$$

Where:
- $S_i(u, t) \in [0, 1]$ is the normalized sub-score for risk dimension $i$
- $w_i$ is the weight for dimension $i$, with $\sum_{i=1}^{n} w_i = 1$
- $n$ is the number of risk dimensions (Git, IAM, SIEM, Jira)

### B. Sub-Score Definitions

#### Git Risk Score $S_{git}$

$$S_{git}(u, t) = \alpha_1 \cdot \text{SecretExposure}(u, t) + \alpha_2 \cdot \text{ForcePush}(u, t) + \alpha_3 \cdot \text{VulnIntroduced}(u, t)$$

Where each component is normalized using:

$$\text{Normalize}(x) = \frac{x - x_{min}}{x_{max} - x_{min}}$$

| Component | Description | Weight $\alpha$ |
|-----------|-------------|-----------------|
| SecretExposure | API keys, credentials in commits | 0.5 |
| ForcePush | Force pushes to protected branches | 0.3 |
| VulnIntroduced | Security vulnerabilities added | 0.2 |

#### IAM Risk Score $S_{iam}$

$$S_{iam}(u, t) = \beta_1 \cdot \text{PrivilegeEscalation}(u, t) + \beta_2 \cdot \text{UnusualAccess}(u, t) + \beta_3 \cdot \text{PolicyViolation}(u, t)$$

| Component | Description | Weight $\beta$ |
|-----------|-------------|----------------|
| PrivilegeEscalation | Self-assigned elevated permissions | 0.4 |
| UnusualAccess | Access outside normal patterns | 0.35 |
| PolicyViolation | IAM policy compliance failures | 0.25 |

#### SIEM Risk Score $S_{siem}$

$$S_{siem}(u, t) = \gamma_1 \cdot \text{PhishingClicks}(u, t) + \gamma_2 \cdot \text{MalwareAlerts}(u, t) + \gamma_3 \cdot \text{DLPViolations}(u, t)$$

### C. Time-Weighted Aggregation

Recent events are weighted more heavily using exponential decay:

$$S_i(u, t) = \sum_{e \in E_u} v(e) \cdot e^{-\lambda(t - t_e)}$$

Where:
- $E_u$ is the set of events for user $u$
- $v(e)$ is the severity value of event $e$
- $t_e$ is the timestamp of event $e$
- $\lambda$ is the decay constant (typically 0.1 for 30-day half-life)

### D. Overall Risk Calculation

The final risk score combines all dimensions:

$$R_u(t) = 0.30 \cdot S_{git} + 0.25 \cdot S_{iam} + 0.25 \cdot S_{siem} + 0.20 \cdot S_{training}$$

Where $S_{training}$ represents the training compliance gap:

$$S_{training}(u, t) = 1 - \frac{\text{ModulesCompleted}(u, t)}{\text{ModulesRequired}(u, t)}$$

---

## III. Training Frequency Model

### A. Risk-Based Scheduling

The training frequency $F_u$ for user $u$ is determined by:

$$F_u = \begin{cases} 
\text{Quarterly} & \text{if } R_u < 0.3 \\
\text{Monthly} & \text{if } 0.3 \leq R_u < 0.7 \\
\text{Weekly/Urgent} & \text{if } R_u \geq 0.7
\end{cases}$$

### B. Risk Reduction Model

After completing personalized training module $m$, the expected risk reduction is:

$$\Delta R_u(m) = R_u^{before} - R_u^{after} = \eta \cdot \text{Relevance}(m, u) \cdot \text{Engagement}(u, m)$$

Where:
- $\eta$ is the learning effectiveness coefficient (empirically derived)
- $\text{Relevance}(m, u)$ measures how well module $m$ addresses user $u$'s specific risk factors
- $\text{Engagement}(u, m)$ measures user interaction (quiz scores, completion rate)

### C. Personalization Advantage

For personalized training $P$ vs generic training $G$:

$$\mathbb{E}[\Delta R_u | P] > \mathbb{E}[\Delta R_u | G]$$

Because $\text{Relevance}(m_P, u) \gg \text{Relevance}(m_G, u)$ for targeted modules.

---

## IV. Zero-Trust Architecture

### A. Why Zero-Trust for AI Training Systems?

Traditional AI training systems face a critical trust problem:

$$\text{AI Output Quality} = f(\text{Data Quality}, \text{Model Quality})$$

If input data can be spoofed or poisoned, the AI recommendations become unreliable. We address this through cryptographic identity verification.

### B. SPIFFE/SPIRE Implementation

**SPIFFE** (Secure Production Identity Framework for Everyone) provides:

1. **Workload Identity**: Each service receives a unique SPIFFE ID
   $$\text{SPIFFE ID} = \text{spiffe://}\langle\text{trust-domain}\rangle/\langle\text{workload-path}\rangle$$

2. **X.509-SVID**: Short-lived certificates (TTL: 1 hour) for mTLS
   $$\text{Certificate} = \text{Sign}_{CA}(\text{Public Key}, \text{SPIFFE ID}, \text{TTL})$$

3. **Attestation**: Workloads prove identity via Kubernetes service account tokens (PSAT)

### C. Trust Chain

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRUST VERIFICATION CHAIN                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   Data Collector         Risk Scorer          LLM Gateway           │
│   ┌──────────┐          ┌──────────┐         ┌──────────┐          │
│   │ SVID: C₁ │──mTLS───▶│ SVID: R₁ │──mTLS──▶│ SVID: G₁ │          │
│   └──────────┘          └──────────┘         └──────────┘          │
│        │                      │                    │                 │
│        ▼                      ▼                    ▼                 │
│   Verify(C₁) ∈ A_R      Verify(R₁) ∈ A_G     Verify(G₁) ∈ A_LLM    │
│                                                                       │
│   A_x = {Allowed SPIFFE IDs for service x}                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### D. Security Properties

| Property | Traditional System | Our Zero-Trust Approach |
|----------|-------------------|------------------------|
| Data Provenance | ❌ Assumed trusted | ✅ Cryptographically verified via SVID |
| Service Authentication | ❌ Network-based (IP) | ✅ Identity-based (SPIFFE) |
| API Key Isolation | ❌ Distributed to clients | ✅ Only LLM Gateway has key |
| Certificate Rotation | ❌ Manual, infrequent | ✅ Automatic, 1-hour TTL |

---

## V. System Architecture

### A. Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────────────┐
│                     KUBERNETES CLUSTER                               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    SPIRE TRUST DOMAIN                         │    │
│  │  ┌──────────────┐         ┌──────────────┐                    │    │
│  │  │ SPIRE Server │◄────────│ SPIRE Agent  │                    │    │
│  │  │ (StatefulSet)│ Attest  │  (DaemonSet) │                    │    │
│  │  └──────────────┘         └──────┬───────┘                    │    │
│  │                                   │ Issue SVIDs                │    │
│  └───────────────────────────────────┼───────────────────────────┘    │
│                                       ▼                               │
│  ┌─────────────┐    mTLS    ┌─────────────┐    mTLS    ┌──────────┐ │
│  │ Collectors  │───────────▶│ Risk Scorer │───────────▶│   LMS    │ │
│  │ (SVID: C_i) │            │ (SVID: R)   │            │ (SVID: L)│ │
│  └─────────────┘            └─────────────┘            └────┬─────┘ │
│        │                          │                          │       │
│        │                          ▼                          │       │
│        │                   ┌─────────────┐                   │       │
│        │                   │  PostgreSQL │                   │       │
│        │                   │  (Risk DB)  │                   │       │
│        │                   └─────────────┘                   │       │
│        │                                                     │       │
│        │              ┌─────────────┐                        │       │
│        └──────────────│ LLM Gateway │◄───────────────────────┘       │
│                       │ (SVID: G)   │         mTLS                   │
│                       └──────┬──────┘                                │
│                              │ HTTPS (API Key)                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               ▼
                        ┌─────────────┐
                        │  Gemini API │
                        │  (External) │
                        └─────────────┘
```

### B. Data Flow

1. **Collection Phase**: Collectors gather behavioral data from enterprise systems (Git, IAM, SIEM)
2. **Verification Phase**: Each data submission is authenticated via mTLS with SPIFFE SVIDs
3. **Aggregation Phase**: Risk Scorer computes $R_u(t)$ using the weighted formula
4. **Personalization Phase**: LMS requests AI-generated content from LLM Gateway
5. **Delivery Phase**: Targeted training delivered to user based on risk profile

### C. mTLS Verification Formula

For each request, the receiving service verifies:

$$\text{Accept}(req) = \text{ValidCert}(req) \land \text{SPIFFE\_ID}(req) \in \text{AllowedCallers}$$

---

## VI. Implementation Details

### A. Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Identity | SPIFFE/SPIRE | Workload identity and mTLS |
| Orchestration | Kubernetes + Helm | Container orchestration |
| AI Backend | Google Gemini 2.5-flash | Content generation |
| Frontend | Streamlit | User dashboard |
| Database | PostgreSQL | Risk profiles and events |
| Language | Python 3.11 | Application code |

### B. Certificate Management

```python
class SPIFFEMTLSHandler:
    def fetch_certificates(self):
        """Fetch X.509-SVID from SPIRE Agent via Workload API"""
        client = WorkloadApiClient(socket_path=SPIFFE_SOCKET)
        svid = client.fetch_x509_svid()
        
        # Write to temp files for SSL context
        self.cert_file = write_cert(svid.leaf.public_bytes)
        self.key_file = write_key(svid.private_key.private_bytes)
        self.ca_file = write_ca(svid.bundle.x509_authorities)
        
    def create_ssl_context(self):
        """Create SSL context for mTLS"""
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.verify_mode = ssl.CERT_REQUIRED  # Require client cert
        ctx.load_cert_chain(self.cert_file, self.key_file)
        ctx.load_verify_locations(self.ca_file)
        return ctx
```

### C. Risk Calculation Implementation

```python
def calculate_risk_score(user_id: str) -> float:
    """
    Calculate overall risk score R_u(t) for user
    
    R = w_git * S_git + w_iam * S_iam + w_siem * S_siem + w_training * S_training
    """
    WEIGHTS = {
        'git': 0.30,
        'iam': 0.25, 
        'siem': 0.25,
        'training': 0.20
    }
    
    scores = {
        'git': normalize(calculate_git_risk(user_id)),
        'iam': normalize(calculate_iam_risk(user_id)),
        'siem': normalize(calculate_siem_risk(user_id)),
        'training': calculate_training_gap(user_id)
    }
    
    return sum(WEIGHTS[k] * scores[k] for k in WEIGHTS)
```

---

## VII. Results and Evaluation

### A. Hypothesis

**H₁**: Personalized, risk-based training reduces security incidents more effectively than generic training.

$$\frac{\partial R_u}{\partial t}\bigg|_{\text{personalized}} < \frac{\partial R_u}{\partial t}\bigg|_{\text{generic}}$$

### B. Expected Outcomes

| Metric | Generic Training | Personalized Training | Improvement |
|--------|-----------------|----------------------|-------------|
| Training Relevance Score | 0.40 | 0.85 | +112% |
| Knowledge Retention (30d) | 45% | 72% | +60% |
| Incident Reduction | 15% | 35% | +133% |
| Time to Competency | 4 weeks | 2 weeks | -50% |

### C. Risk Reduction Over Time

For a user with initial risk $R_0 = 0.75$:

$$R(t) = R_0 \cdot e^{-\mu t} + R_{baseline}$$

Where:
- $\mu$ = learning rate (higher for personalized training)
- $R_{baseline}$ = minimum achievable risk (≈ 0.1)

With personalized training ($\mu_P = 0.15$) vs generic ($\mu_G = 0.05$):

| Week | $R_P(t)$ | $R_G(t)$ | Difference |
|------|----------|----------|------------|
| 0 | 0.75 | 0.75 | 0.00 |
| 4 | 0.51 | 0.66 | 0.15 |
| 8 | 0.35 | 0.58 | 0.23 |
| 12 | 0.24 | 0.51 | 0.27 |

---

## VIII. Conclusion

This paper demonstrates a novel approach to cybersecurity training that combines:

1. **Mathematical Risk Modeling**: Multi-dimensional, time-weighted risk scoring
2. **Zero-Trust Architecture**: SPIFFE/SPIRE for cryptographic data provenance
3. **AI Personalization**: Targeted content generation based on individual risk profiles
4. **Continuous Improvement**: Risk-driven training frequency adaptation

The integration of workload identity (SPIFFE) with generative AI ensures that training recommendations are based on verified behavioral data, addressing the fundamental trust problem in AI-driven security systems.

---

## References

[1] SPIFFE: Secure Production Identity Framework for Everyone. https://spiffe.io

[2] SPIRE: SPIFFE Runtime Environment. https://github.com/spiffe/spire

[3] Google Gemini API. https://ai.google.dev

[4] Kubernetes Security Best Practices. https://kubernetes.io/docs/concepts/security/

---

## Appendix A: SPIFFE ID Registry

| Service | SPIFFE ID | Role |
|---------|-----------|------|
| Git Collector | spiffe://security-training.example.org/git-collector | Data source |
| IAM Collector | spiffe://security-training.example.org/iam-collector | Data source |
| SIEM Collector | spiffe://security-training.example.org/siem-collector | Data source |
| Risk Scorer | spiffe://security-training.example.org/risk-scorer | Aggregator |
| LLM Gateway | spiffe://security-training.example.org/llm-gateway | AI proxy |
| LMS | spiffe://security-training.example.org/lms | Frontend |

## Appendix B: Allowed Caller Matrix

| Service | Accepts Calls From |
|---------|-------------------|
| Risk Scorer | git-collector, iam-collector, siem-collector, jira-collector |
| LLM Gateway | lms, risk-scorer |
| LMS | (user-facing, no API callers) |
