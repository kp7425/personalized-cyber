#!/bin/bash
# End-to-End Test Script for IEEE Paper Demonstration
# This captures the full workflow for verification

set -e

NAMESPACE="security-training"

echo "=============================================="
echo "🧪 END-TO-END VERIFICATION TEST"
echo "=============================================="

# 1. Check all pods are running
echo ""
echo "📍 STEP 1: Verify All Pods Are Running"
echo "----------------------------------------------"
kubectl get pods -n $NAMESPACE -o wide

# Count running pods
RUNNING=$(kubectl get pods -n $NAMESPACE --no-headers | grep Running | wc -l)
TOTAL=$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
echo "✅ Running: $RUNNING / $TOTAL pods"

if [ "$RUNNING" -lt "8" ]; then
  echo "⚠️  Warning: Expected at least 8 pods (SPIRE, Postgres, 4 Collectors, Engine, Gateway, LMS)"
  echo "   Waiting 30 seconds for pods to start..."
  sleep 30
  kubectl get pods -n $NAMESPACE
fi

# 2. Verify SPIRE is issuing identities
echo ""
echo "📍 STEP 2: Verify SPIRE Server Is Working"
echo "----------------------------------------------"
SPIRE_SERVER=$(kubectl get pod -n $NAMESPACE -l app=spire-server -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$SPIRE_SERVER" ]; then
  echo "SPIRE Server Pod: $SPIRE_SERVER"
  kubectl exec -n $NAMESPACE $SPIRE_SERVER -- /opt/spire/bin/spire-server entry show || echo "Note: Entries may still be registering"
else
  echo "❌ SPIRE Server not found"
fi

# 3. Verify Database Connection
echo ""
echo "📍 STEP 3: Verify PostgreSQL Database"
echo "----------------------------------------------"
POSTGRES_POD=$(kubectl get pod -n $NAMESPACE -l app=postgres -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$POSTGRES_POD" ]; then
  echo "PostgreSQL Pod: $POSTGRES_POD"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT COUNT(*) as user_count FROM users;" 2>/dev/null || echo "Tables not yet populated"
else
  echo "❌ PostgreSQL not found"
fi

# 4. Run Simulation to Populate Data
echo ""
echo "📍 STEP 4: Populate Metadata Database (30 days of history)"
echo "----------------------------------------------"
COLLECTOR_POD=$(kubectl get pod -n $NAMESPACE -l app=git-collector -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -n "$COLLECTOR_POD" ]; then
  echo "Running historical data generator..."
  kubectl exec -n $NAMESPACE $COLLECTOR_POD -- python -m src.utils.historical_data_generator
  echo "✅ Historical data generated"
else
  echo "❌ Git Collector pod not found"
fi

# 5. Verify Data Was Inserted
echo ""
echo "📍 STEP 5: Verify Data in Database"
echo "----------------------------------------------"
if [ -n "$POSTGRES_POD" ]; then
  echo "Users created:"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT COUNT(*) FROM users;"
  echo "Git events:"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT COUNT(*) FROM git_activity;"
  echo "IAM events:"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT COUNT(*) FROM iam_events;"
  echo "SIEM alerts:"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT COUNT(*) FROM siem_alerts;"
fi

# 6. Calculate Risk Scores
echo ""
echo "📍 STEP 6: Calculate Risk Scores for All Users"
echo "----------------------------------------------"
if [ -n "$COLLECTOR_POD" ]; then
  kubectl exec -n $NAMESPACE $COLLECTOR_POD -- python -c "from src.engine.risk_scorer import RiskScorer; r = RiskScorer(); print(r._calculate_all_scores())"
fi

# 7. Verify Risk Scores in DB
echo ""
echo "📍 STEP 7: Verify Risk Profiles"
echo "----------------------------------------------"
if [ -n "$POSTGRES_POD" ]; then
  echo "Sample Risk Profiles:"
  kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "SELECT u.email, u.job_title, r.overall_risk_score, r.git_risk_score, r.iam_risk_score FROM users u JOIN user_risk_profiles r ON u.user_id = r.user_id ORDER BY r.overall_risk_score DESC LIMIT 5;"
fi

# 8. Test LMS Dashboard Access
echo ""
echo "📍 STEP 8: LMS Dashboard Access"
echo "----------------------------------------------"
echo "Run this command in another terminal to access the dashboard:"
echo ""
echo "   kubectl port-forward svc/lms 8080:8080 -n $NAMESPACE"
echo ""
echo "Then open: http://localhost:8080"

echo ""
echo "=============================================="
echo "✅ END-TO-END VERIFICATION COMPLETE"
echo "=============================================="
echo ""
echo "📸 For IEEE Paper Screenshots:"
echo "   1. Dashboard showing personalized risk profile"
echo "   2. Risk breakdown by category (Git, IAM, Training)"
echo "   3. Database query showing diverse user profiles"
echo "   4. SPIRE entry list showing all registered workloads"
