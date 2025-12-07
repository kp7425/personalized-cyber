# Lessons Learned: Building a Zero-Trust Security Training Platform

This document captures the key challenges encountered and solutions implemented during the development of the personalized security awareness training platform with full mTLS/SPIFFE integration.

---

## 1. SPIRE Server RBAC Issues

### Problem
```
tokenreviews.authentication.k8s.io is forbidden: User "system:serviceaccount:security-training:spire-server" 
cannot create resource "tokenreviews" in API group "authentication.k8s.io" at the cluster scope
```

The SPIRE agent was crashing during node attestation because the SPIRE server lacked permissions to validate Kubernetes tokens.

### Root Cause
The SPIRE server ClusterRole was missing permissions for `tokenreviews` and `configmaps` in the `authentication.k8s.io` API group. Kubernetes PSAT (Projected Service Account Token) attestation requires these permissions.

### Solution
Updated `helm/security-training/templates/spire/server.yaml`:
```yaml
rules:
  - apiGroups: [""]
    resources: ["pods", "nodes", "configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["authentication.k8s.io"]
    resources: ["tokenreviews"]
    verbs: ["create"]
```

### Lesson
Always verify RBAC permissions match the attestation method. PSAT attestation requires cluster-scoped token review permissions.

---

## 2. Helm Cluster-Scoped Resource Management

### Problem
Cluster-scoped resources (ClusterRole, ClusterRoleBinding) were not being properly managed by Helm during upgrades and uninstalls.

### Root Cause
ClusterRoles lacked proper Helm labels and namespace-suffixed names, causing conflicts and orphaned resources.

### Solution
Added Helm-standard labels and unique names:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spire-server-{{ .Values.global.namespace }}
  labels:
    app.kubernetes.io/managed-by: Helm
    helm.sh/chart: {{ .Chart.Name }}
```

### Lesson
Cluster-scoped resources need careful naming and labeling to avoid conflicts across namespaces and ensure proper Helm lifecycle management.

---

## 3. Dynamic SPIRE Agent ID Discovery

### Problem
SPIRE agent SPIFFE IDs include a dynamic UUID that changes on each pod restart:
```
spiffe://security-training.example.org/spire/agent/k8s_psat/docker-desktop/9e23f4a1-...
```

Hardcoding agent IDs in workload registrations caused failures after agent restarts.

### Root Cause
The `k8s_psat` attestor generates a unique ID per agent instance based on the node.

### Solution
Created an automated registration job that discovers the agent ID dynamically:
```bash
AGENT_ID=$(kubectl logs -n $NS daemonset/spire-agent 2>&1 | \
  grep "Node attestation was successful" | tail -1 | \
  sed 's/.*spiffe_id="\([^"]*\)".*/\1/')

for WORKLOAD in git-collector risk-scorer lms llm-gateway; do
  spire-server entry create \
    -spiffeID spiffe://$TRUST_DOMAIN/$WORKLOAD \
    -parentID "$AGENT_ID" \
    -selector k8s:ns:$NS \
    -selector k8s:sa:${WORKLOAD}-sa
done
```

### Lesson
SPIRE deployments in Kubernetes should automate agent ID discovery rather than relying on static configurations.

---

## 4. Init Container Race Conditions

### Problem
Workload pods were starting before SPIRE workload registrations completed, causing certificate fetch failures.

### Root Cause
Kubernetes pods start immediately after their dependencies are available, but the SPIRE registration job runs asynchronously.

### Solution
Added init containers that wait for the registration job to complete:
```yaml
initContainers:
  - name: wait-for-spire-registration
    image: bitnami/kubectl:latest
    command:
      - /bin/bash
      - -c
      - |
        echo "Waiting for SPIRE registration..."
        kubectl wait --for=condition=Complete job/spire-register-workloads \
          -n $NS --timeout=300s
```

### Lesson
Use init containers to enforce startup ordering when dealing with external registration systems.

---

## 5. Streamlit SPIFFE Integration

### Problem
The LMS (Streamlit app) couldn't initialize SPIFFE certificates for mTLS client calls, causing silent failures when calling the LLM Gateway.

### Root Cause
Streamlit runs in a different execution model than the `BaseSPIFFEAgent` class, and the SPIFFE workload API client initialization was failing silently.

### Solution
Created a cached SPIFFE handler in the Streamlit session state:
```python
if 'mtls_handler' not in st.session_state:
    st.session_state.mtls_handler = SPIFFEMTLSHandler()

mtls = st.session_state.mtls_handler
response = mtls.make_mtls_request(gateway_url, payload)
```

### Lesson
Frontend/UI applications may need different patterns for SPIFFE integration than backend services. Session-based caching helps with stateless frameworks.

---

## 6. Gemini API Model Selection

### Problem
```
429: You exceeded your current quota, please check your plan... 
model: gemini-2.0-flash
```

Rate limit errors on `gemini-2.0-flash` model.

### Root Cause
The older model had exhausted its free-tier quota. The code and Helm values were using different models.

### Solution
1. Updated Helm values to use a newer model with quota:
```yaml
gateway:
  llm:
    model: gemini-2.5-flash
```

2. Also updated the Python code default to match:
```python
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
```

### Lesson
Environment variable overrides in Kubernetes can mask code defaults. Always check both the code and deployment configuration.

---

## 7. Gemini REST API vs Python Library

### Problem
```
Unexpected candidate structure: {'content': {'role': 'model'}, 'finishReason': 'MAX_TOKENS'}
```

REST API calls to Gemini 2.5 returned responses with no content due to "thinking" tokens consuming the output limit.

### Root Cause
Gemini 2.5 models use internal "thinking" tokens that count against `maxOutputTokens`. The REST API exposes this differently than the Python SDK.

### Solution
Switched from REST API to the `google-generativeai` Python library:
```python
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)
response = model.generate_content(prompt)

if response and hasattr(response, 'text') and response.text:
    return {"content": response.text, "model": GEMINI_MODEL}
```

### Lesson
Use official SDKs when available - they handle edge cases (like thinking tokens) that raw REST APIs may not handle gracefully.

---

## 8. Service Discovery in Kubernetes

### Problem
API client was using incorrect URLs for service-to-service communication within the cluster.

### Root Cause
The code was mixing local development URLs with Kubernetes DNS names, and the protocol (HTTP vs HTTPS) wasn't being set correctly for mTLS.

### Solution
Updated `api_client.py` to use proper Kubernetes DNS:
```python
def _get_service_url(self, service: str) -> str:
    namespace = os.getenv('K8S_NAMESPACE', 'security-training')
    service_map = {
        'llm-gateway': f'llm-gateway-svc.{namespace}.svc.cluster.local:8520',
        'risk-scorer': f'risk-scorer-svc.{namespace}.svc.cluster.local:8510',
    }
    return f"https://{service_map.get(service, service)}"
```

### Lesson
Service discovery patterns differ significantly between local development and Kubernetes. Use environment variables to switch between modes.

---

## Summary of Key Takeaways

| Category | Key Insight |
|----------|-------------|
| **SPIRE/SPIFFE** | Automate agent ID discovery; use init containers for ordering |
| **Kubernetes RBAC** | PSAT attestation requires tokenreviews permission at cluster scope |
| **Helm** | Cluster-scoped resources need unique names and proper labels |
| **Gemini API** | Use Python SDK over REST API for better response handling |
| **mTLS** | Frontend apps need different patterns than backend services |
| **Configuration** | Check both code defaults AND deployment config for consistency |

---

## Architecture Achieved

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

All internal communication secured with mTLS using SPIFFE X.509-SVIDs. Zero-trust achieved! 🛡️
