# Deployment Walkthrough

This document provides step-by-step instructions for deploying the AI-Driven Personalized Security Training Platform.

## Prerequisites

- Docker Desktop with Kubernetes enabled
- Helm 3.x installed
- Gemini API key (from [AI Studio](https://aistudio.google.com/apikey))

## Step 1: Build Docker Image

```bash
cd personalized-cyber
docker build -t security-training-app:latest .
```

## Step 2: Set Environment Variables

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

## Step 3: Deploy with Helm

```bash
helm install security-system ./helm/security-training \
  --set global.geminiApiKey=$GEMINI_API_KEY
```

## Step 4: Wait for Pods

```bash
kubectl get pods -n security-training -w
```

Expected output (all pods Running):
```
NAME                              READY   STATUS    RESTARTS   AGE
git-collector-xxx                 1/1     Running   0          2m
iam-collector-xxx                 1/1     Running   0          2m
jira-collector-xxx                1/1     Running   0          2m
llm-gateway-xxx                   1/1     Running   0          2m
lms-xxx                           1/1     Running   0          2m
postgres-xxx                      1/1     Running   0          2m
risk-scorer-xxx                   1/1     Running   0          2m
siem-collector-xxx                1/1     Running   0          2m
spire-agent-xxx                   1/1     Running   0          2m
spire-server-0                    1/1     Running   0          2m
```

## Step 5: Verify SPIRE Registration

```bash
kubectl exec -n security-training deploy/spire-server -- \
  /opt/spire/bin/spire-server entry show
```

Should show entries for: lms, llm-gateway, risk-scorer, git-collector, etc.

## Step 6: Access LMS Dashboard

```bash
kubectl port-forward svc/lms 8080:8080 -n security-training
```

Open browser: http://localhost:8080

## Step 7: Test Personalized Training

1. Select a user from the dropdown in the sidebar
2. Navigate to "My Training" page
3. Click "Start Module" on any recommended module
4. Wait for Gemini to generate personalized content via mTLS → LLM Gateway

Success message should show:
```
✅ Generated via mTLS → LLM Gateway → gemini (gemini-2.5-flash)
```

---

## Troubleshooting

### SPIRE Agent Not Starting
```bash
kubectl logs -n security-training daemonset/spire-agent
```

Common fix: Wait for SPIRE server to be fully ready before agent starts.

### mTLS Certificate Errors
```bash
kubectl logs -n security-training -l app=lms | grep -i spiffe
```

Ensure workload is registered:
```bash
kubectl exec -n security-training deploy/spire-server -- \
  /opt/spire/bin/spire-server entry show | grep lms
```

### Gemini Rate Limits
If you see 429 errors, wait 60 seconds or check your API quota at:
https://ai.dev/usage?tab=rate-limit

### Rebuild After Code Changes
```bash
docker build -t security-training-app:latest .
kubectl delete pod -n security-training -l app=lms
kubectl delete pod -n security-training -l app=llm-gateway
```

---

## Architecture Reference

See [DEPLOYMENT_ARCHITECTURE.md](./DEPLOYMENT_ARCHITECTURE.md) for complete architecture diagram.

See [LESSONS_LEARNED.md](./LESSONS_LEARNED.md) for detailed troubleshooting scenarios.
