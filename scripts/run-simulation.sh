#!/bin/bash
set -e

echo "🔬 Starting IEEE Simulation Run..."

# Find a collector pod to run the scripts in (they have the code and DB access)
POD=$(kubectl get pod -l app=git-collector -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -z "$POD" ]; then
  echo "❌ Error: git-collector pod not found. Is the system deployed?"
  echo "   Falling back to local execution..."
  
  # Local fallback
  echo "🏗️  Generating 30 days of historical metadata..."
  python -m src.utils.historical_data_generator
  
  echo "📊 Calculating risk scores for all users..."
  python -c "from src.engine.risk_scorer import RiskScorer; r = RiskScorer(); print(r._calculate_all_scores())"
  
  exit 0
fi

echo "📍 Found Execution Pod: $POD"

# Generate historical metadata (30 days, 50 users)
echo "🏗️  Step 1: Populating Central Metadata Database (30 days of history)..."
kubectl exec $POD -- python -m src.utils.historical_data_generator

# Calculate risk scores for all users
echo "📊 Step 2: Calculating Risk Scores..."
kubectl exec $POD -- python -c "from src.engine.risk_scorer import RiskScorer; r = RiskScorer(); print(r._calculate_all_scores())"

echo "✅ Simulation Complete! Check the Dashboard."
