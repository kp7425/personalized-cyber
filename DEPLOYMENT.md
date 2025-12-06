# Deployment Guide

Complete deployment, troubleshooting, and rebuild commands for the IEEE Paper demonstration.

---

## Quick Start

```bash
# Build + Deploy + Test (4 commands)
./scripts/build.sh
helm install security-system ./helm/security-training --set secrets.geminiApiKey="YOUR_KEY"
kubectl get pods -n security-training -w  # Wait until all Running
./scripts/test-e2e.sh
```

---

## Step-by-Step Deployment

### 1. Build Docker Image
```bash
./scripts/build.sh
```

Verify:
```bash
docker images | grep security-training-app
```

### 2. Deploy to Kubernetes
```bash
helm install security-system ./helm/security-training \
  --set secrets.geminiApiKey="YOUR_GEMINI_API_KEY"
```

### 3. Wait for Pods
```bash
kubectl get pods -n security-training -w
```

Expected pods (~3 minutes to all Running):
| Pod | Status |
|-----|--------|
| spire-server-0 | Running |
| spire-agent-xxxxx | Running |
| postgres-xxxxx | Running |
| git-collector-xxxxx | Running |
| jira-collector-xxxxx | Running |
| iam-collector-xxxxx | Running |
| siem-collector-xxxxx | Running |
| risk-scorer-xxxxx | Running |
| llm-gateway-xxxxx | Running |
| lms-xxxxx | Running |

### 4. Run Simulation
```bash
./scripts/run-simulation.sh
```

### 5. Run End-to-End Test
```bash
./scripts/test-e2e.sh
```

### 6. Access Dashboard
```bash
kubectl port-forward svc/lms 8080:8080 -n security-training
# Open: http://localhost:8080
```

---

## Troubleshooting

### Pod is CrashLoopBackOff
```bash
# Check logs
kubectl logs -n security-training <POD_NAME> --previous

# Common causes:
# - Database not ready yet → Wait 60 seconds
# - Missing GEMINI_API_KEY → Redeploy with --set
# - Python import error → Rebuild image
```

### Pod is ImagePullBackOff
```bash
# Local image not found by K8s
# Ensure imagePullPolicy is IfNotPresent
kubectl describe pod -n security-training <POD_NAME>

# Fix: Rebuild and verify
./scripts/build.sh
docker images | grep security-training-app
```

### SPIRE Agent Can't Connect to Server
```bash
# Check SPIRE server logs
kubectl logs -n security-training spire-server-0

# Check agent logs
kubectl logs -n security-training -l app=spire-agent

# Restart agent
kubectl delete pod -n security-training -l app=spire-agent
```

### Database Connection Failed
```bash
# Check PostgreSQL is running
kubectl get pod -n security-training -l app=postgres

# Check logs
kubectl logs -n security-training -l app=postgres

# Test connection manually
kubectl exec -n security-training -it $(kubectl get pod -n security-training -l app=postgres -o name) -- psql -U postgres -d security_training -c "SELECT 1;"
```

### No Data in Dashboard
```bash
# Run simulation again
./scripts/run-simulation.sh

# Manually verify data
kubectl exec -n security-training $(kubectl get pod -n security-training -l app=postgres -o name) -- psql -U postgres -d security_training -c "SELECT COUNT(*) FROM users;"
```

---

## Rebuild & Redeploy

### Rebuild After Code Changes
```bash
# Rebuild image
./scripts/build.sh

# Delete old pods (will auto-recreate with new image)
kubectl delete pods -n security-training --all

# Or rolling restart
kubectl rollout restart deployment -n security-training
```

### Complete Redeploy (Clean Slate)
```bash
# Uninstall
helm uninstall security-system

# Delete namespace (removes all data!)
kubectl delete namespace security-training

# Re-deploy
./scripts/build.sh
helm install security-system ./helm/security-training \
  --set secrets.geminiApiKey="YOUR_KEY"
```

### Update Helm Values Only
```bash
helm upgrade security-system ./helm/security-training \
  --set secrets.geminiApiKey="NEW_KEY"
```

---

## Useful Debug Commands

### View All Resources
```bash
kubectl get all -n security-training
```

### Check Pod Details
```bash
kubectl describe pod <POD_NAME> -n security-training
```

### Stream Logs
```bash
kubectl logs -f <POD_NAME> -n security-training
```

### Exec Into Container
```bash
kubectl exec -it <POD_NAME> -n security-training -- /bin/sh
```

### Check SPIRE Entries
```bash
kubectl exec -n security-training spire-server-0 -- /opt/spire/bin/spire-server entry show
```

### Query Database
```bash
# Get postgres pod
PG_POD=$(kubectl get pod -n security-training -l app=postgres -o jsonpath="{.items[0].metadata.name}")

# Run query
kubectl exec -n security-training $PG_POD -- psql -U postgres -d security_training -c "SELECT * FROM users LIMIT 5;"
```

---

## Local Development (Without Kubernetes)

### Run Database Only
```bash
docker-compose up -d
```

### Run Services Manually
```bash
# Terminal 1: Database
docker-compose up -d

# Terminal 2: Git Collector
python -m src.collectors.git_collector

# Terminal 3: Risk Scorer
python -m src.engine.risk_scorer

# Terminal 4: LMS
streamlit run src/lms/app.py
```

### Generate Test Data Locally
```bash
python -m src.utils.historical_data_generator
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | postgres-svc | Database hostname |
| `DB_NAME` | security_training | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | (from secret) | Database password |
| `GEMINI_API_KEY` | (from secret) | Google Gemini API key |
| `SPIFFE_ENDPOINT_SOCKET` | unix:///opt/spire/sockets/agent.sock | SPIRE agent socket |
