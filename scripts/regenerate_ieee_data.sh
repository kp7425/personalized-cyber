#!/bin/bash
# ==============================================================================
# IEEE Paper Data Regeneration Script
# ==============================================================================
# This script:
# 1. Clears existing data
# 2. Runs the IEEE-spec historical data generator
# 3. Recalculates risk scores for all users
# ==============================================================================

set -e

NAMESPACE="${NAMESPACE:-security-training}"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        IEEE PAPER - DATA REGENERATION SCRIPT                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Namespace: $NAMESPACE"
echo ""

# Get pods
POSTGRES_POD=$(kubectl get pod -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}')
RISK_SCORER_POD=$(kubectl get pod -n $NAMESPACE -l app=risk-scorer -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POSTGRES_POD" ]; then
    echo "❌ PostgreSQL pod not found!"
    exit 1
fi

echo "📦 PostgreSQL Pod: $POSTGRES_POD"
echo "📦 Risk Scorer Pod: $RISK_SCORER_POD"
echo ""

# Step 1: Clear existing data
echo "🗑️  Step 1: Clearing existing data..."
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "
    -- Clear event tables
    TRUNCATE git_activity CASCADE;
    TRUNCATE jira_activity CASCADE;
    TRUNCATE iam_events CASCADE;
    TRUNCATE siem_alerts CASCADE;
    TRUNCATE training_completions CASCADE;
    TRUNCATE risk_scores_history CASCADE;
    
    -- Clear user risk profiles (but keep users)
    TRUNCATE user_risk_profiles CASCADE;
    
    -- Optionally clear users to start fresh
    TRUNCATE users CASCADE;
" 2>/dev/null || echo "   (Some tables may not exist, continuing...)"
echo "   ✓ Tables cleared"
echo ""

# Step 2: Copy historical data generator to pod
echo "📤 Step 2: Copying historical data generator..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create a combined script that can run inside the pod
cat > /tmp/generate_ieee_data.py << 'ENDSCRIPT'
"""
IEEE Paper Historical Data Generator - Standalone Version
Generates 30 days of multi-source behavioral data with proper role distribution
"""

import random
from datetime import datetime, timedelta
from faker import Faker
import psycopg2
import json
import uuid
import os

fake = Faker()

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres-svc"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "security_training"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "securepassword123")
    )

# ============================================================================
# ROLE DEFINITIONS (Per IEEE Spec)
# ============================================================================

JOB_PROFILES = [
    {
        "title": "Backend Developer",
        "profile_key": "backend_developer",
        "stack": ["python", "java", "aws", "rds"],
        "dept": "Engineering",
        "count": 12,
        "expected_risk": (0.6, 0.9),
        "ground_truth": "HIGH"
    },
    {
        "title": "Frontend Developer",
        "profile_key": "frontend_developer",
        "stack": ["javascript", "react", "typescript", "aws"],
        "dept": "Product",
        "count": 8,
        "expected_risk": (0.4, 0.6),
        "ground_truth": "MEDIUM"
    },
    {
        "title": "DevOps Engineer",
        "profile_key": "devops_engineer",
        "stack": ["terraform", "kubernetes", "aws", "gcp"],
        "dept": "Platform",
        "count": 8,
        "expected_risk": (0.6, 0.8),
        "ground_truth": "HIGH"
    },
    {
        "title": "DevSecOps Engineer",
        "profile_key": "devsecops_engineer",
        "stack": ["python", "aws", "gcp", "splunk"],
        "dept": "Security",
        "count": 4,
        "expected_risk": (0.1, 0.3),
        "ground_truth": "LOW"
    },
    {
        "title": "Cloud Security Analyst",
        "profile_key": "cloud_security_analyst",
        "stack": ["aws", "gcp", "sentinel", "crowdstrike"],
        "dept": "Security",
        "count": 3,
        "expected_risk": (0.0, 0.2),
        "ground_truth": "VERY_LOW"
    },
    {
        "title": "Data Analyst",
        "profile_key": "data_analyst",
        "stack": ["python", "sql", "bigquery", "gcp"],
        "dept": "Data Platform",
        "count": 6,
        "expected_risk": (0.3, 0.5),
        "ground_truth": "MEDIUM"
    },
    {
        "title": "Data Engineer",
        "profile_key": "data_engineer",
        "stack": ["python", "spark", "airflow", "bigquery", "gcp"],
        "dept": "Data Platform",
        "count": 6,
        "expected_risk": (0.5, 0.8),
        "ground_truth": "HIGH"
    },
    {
        "title": "SRE",
        "profile_key": "sre",
        "stack": ["go", "kubernetes", "terraform", "aws", "gcp"],
        "dept": "Reliability",
        "count": 3,
        "expected_risk": (0.2, 0.9),
        "ground_truth": "VARIABLE"
    }
]

# ============================================================================
# EVENT DISTRIBUTION (Per Role)
# ============================================================================

EVENT_CONFIG = {
    "backend_developer": {
        "git_commits_per_day": (5, 15),
        "secrets_probability": 0.15,
        "force_push_probability": 0.10,
        "jira_tickets_30d": (15, 30),
        "overdue_probability": 0.3,
        "iam_events_30d": (10, 30),
        "privileged_probability": 0.2,
        "siem_alerts_30d": (0, 3)
    },
    "frontend_developer": {
        "git_commits_per_day": (3, 10),
        "secrets_probability": 0.08,
        "force_push_probability": 0.05,
        "jira_tickets_30d": (10, 20),
        "overdue_probability": 0.2,
        "iam_events_30d": (5, 15),
        "privileged_probability": 0.05,
        "siem_alerts_30d": (0, 2)
    },
    "devops_engineer": {
        "git_commits_per_day": (2, 8),
        "secrets_probability": 0.12,
        "force_push_probability": 0.15,
        "jira_tickets_30d": (10, 25),
        "overdue_probability": 0.25,
        "iam_events_30d": (30, 100),
        "privileged_probability": 0.4,
        "siem_alerts_30d": (0, 3)
    },
    "devsecops_engineer": {  # Control - Low risk
        "git_commits_per_day": (3, 8),
        "secrets_probability": 0.01,
        "force_push_probability": 0.01,
        "jira_tickets_30d": (20, 40),
        "overdue_probability": 0.05,
        "iam_events_30d": (20, 50),
        "privileged_probability": 0.1,
        "siem_alerts_30d": (0, 1)
    },
    "cloud_security_analyst": {  # Control - Very low risk
        "git_commits_per_day": (0, 2),
        "secrets_probability": 0.0,
        "force_push_probability": 0.0,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.02,
        "iam_events_30d": (50, 150),
        "privileged_probability": 0.02,
        "siem_alerts_30d": (0, 0)
    },
    "data_analyst": {
        "git_commits_per_day": (1, 5),
        "secrets_probability": 0.05,
        "force_push_probability": 0.02,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.15,
        "iam_events_30d": (20, 60),
        "privileged_probability": 0.15,
        "siem_alerts_30d": (0, 2)
    },
    "data_engineer": {
        "git_commits_per_day": (3, 10),
        "secrets_probability": 0.10,
        "force_push_probability": 0.08,
        "jira_tickets_30d": (10, 25),
        "overdue_probability": 0.2,
        "iam_events_30d": (40, 100),
        "privileged_probability": 0.35,
        "siem_alerts_30d": (0, 3)
    },
    "sre": {
        "git_commits_per_day": (2, 8),
        "secrets_probability": 0.08,
        "force_push_probability": 0.20,
        "jira_tickets_30d": (15, 30),
        "overdue_probability": 0.25,
        "iam_events_30d": (30, 80),
        "privileged_probability": 0.5,
        "siem_alerts_30d": (0, 5)
    }
}

TEMPORAL_MULTIPLIERS = {
    "week_1": 1.0,
    "week_2": 1.0,
    "week_3": 3.0,  # SPIKE
    "week_4": 0.8
}

def get_week_multiplier(day_offset):
    if day_offset >= 21:
        return TEMPORAL_MULTIPLIERS["week_4"]
    elif day_offset >= 14:
        return TEMPORAL_MULTIPLIERS["week_3"]
    elif day_offset >= 7:
        return TEMPORAL_MULTIPLIERS["week_2"]
    else:
        return TEMPORAL_MULTIPLIERS["week_1"]


def generate_all():
    print("🏗️  IEEE Paper - Historical Data Generator")
    print("   Generating 30 days of multi-source behavioral data...")
    print("")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    users = []
    stats = {
        "users": 0,
        "git_events": 0,
        "jira_events": 0,
        "iam_events": 0,
        "siem_events": 0
    }
    
    # Create users
    print("👤 Creating users by role distribution:")
    for profile in JOB_PROFILES:
        count = profile["count"]
        print(f"   {profile['title']}: {count} ({profile['ground_truth']} risk)")
        
        for i in range(count):
            user_id = str(uuid.uuid4())
            workday_id = f"WD-{10000 + stats['users']}"
            email = f"{fake.first_name().lower()}.{fake.last_name().lower()}.{stats['users']}@example.org"
            
            cur.execute("""
                INSERT INTO users (
                    user_id, workday_id, email, full_name, 
                    department, job_title, job_profile, tech_stack, hire_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (
                user_id, workday_id, email, fake.name(),
                profile["dept"], profile["title"], profile["profile_key"],
                json.dumps(profile["stack"]),
                fake.date_between(start_date='-3y', end_date='-6m')
            ))
            
            result = cur.fetchone()
            users.append({
                "user_id": result[0],
                "profile_key": profile["profile_key"],
                "stack": profile["stack"],
                "ground_truth": profile["ground_truth"]
            })
            stats["users"] += 1
    
    conn.commit()
    print(f"   ✅ Created {stats['users']} users")
    print("")
    
    # Generate events for each user
    print("📊 Generating behavioral events (30 days)...")
    
    for user in users:
        config = EVENT_CONFIG.get(user["profile_key"], EVENT_CONFIG["backend_developer"])
        stack = user["stack"]
        
        # Git events
        for day_offset in range(30):
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            multiplier = get_week_multiplier(day_offset)
            
            base_commits = random.randint(*config["git_commits_per_day"])
            commits_today = int(base_commits * multiplier)
            
            for _ in range(commits_today):
                if random.random() < config["secrets_probability"] * multiplier:
                    event_type = "secret_detected"
                elif random.random() < config["force_push_probability"] * multiplier:
                    event_type = "force_push"
                else:
                    event_type = "commit"
                
                repo = random.choice(["ml-pipeline", "api-service", "portal", "infra-live", "data-etl"])
                
                cur.execute("""
                    INSERT INTO git_activity (user_id, event_type, repository, event_timestamp, raw_data)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user["user_id"], event_type, f"org/{repo}", event_date, json.dumps({"simulated": True})))
                stats["git_events"] += 1
        
        # Jira events
        total_tickets = random.randint(*config["jira_tickets_30d"])
        for _ in range(total_tickets):
            day_offset = random.randint(0, 29)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            ticket_type = random.choice(["security_vulnerability", "compliance_issue", "incident"])
            priority = random.choice(["Critical", "High", "Medium", "Low"])
            status = "Overdue" if random.random() < config["overdue_probability"] else random.choice(["Open", "In Progress", "Resolved"])
            
            cur.execute("""
                INSERT INTO jira_activity (user_id, event_type, ticket_key, ticket_type, priority, status, event_timestamp, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user["user_id"], "ticket_assigned", f"SEC-{random.randint(1000, 9999)}", ticket_type, priority, status, event_date, json.dumps({"simulated": True})))
            stats["jira_events"] += 1
        
        # IAM events
        total_iam = random.randint(*config["iam_events_30d"])
        for _ in range(total_iam):
            day_offset = random.randint(0, 29)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            multiplier = get_week_multiplier(day_offset)
            
            is_privileged = random.random() < (config["privileged_probability"] * multiplier)
            cloud = random.choice([c for c in ["aws", "gcp", "azure"] if c in stack] or ["aws"])
            event_type = random.choice(["AssumeRole", "CreateAccessKey", "SetIamPolicy", "AttachUserPolicy"])
            
            cur.execute("""
                INSERT INTO iam_events (user_id, cloud_provider, event_type, resource_arn, is_privileged, event_timestamp, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user["user_id"], cloud, event_type, f"arn:{cloud}:iam::123456789012:role/SomeRole", is_privileged, event_date, json.dumps({"simulated": True})))
            stats["iam_events"] += 1
        
        # SIEM events
        min_alerts, max_alerts = config["siem_alerts_30d"]
        alert_count = random.randint(min_alerts, max_alerts)
        for _ in range(alert_count):
            day_offset = random.randint(0, 29)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            alert_type = random.choice(["phishing", "malware", "policy_violation", "anomalous_login"])
            severity = random.choice(["low", "medium", "high", "critical"])
            
            cur.execute("""
                INSERT INTO siem_alerts (user_id, alert_type, severity, source_system, alert_name, event_timestamp, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user["user_id"], alert_type, severity, random.choice(["splunk", "sentinel", "crowdstrike"]), f"Simulated {alert_type}", event_date, json.dumps({"simulated": True})))
            stats["siem_events"] += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Data Generation Complete!")
    print(f"   Users: {stats['users']}")
    print(f"   Git Events: {stats['git_events']}")
    print(f"   Jira Events: {stats['jira_events']}")
    print(f"   IAM Events: {stats['iam_events']}")
    print(f"   SIEM Events: {stats['siem_events']}")
    print(f"   Total Events: {stats['git_events'] + stats['jira_events'] + stats['iam_events'] + stats['siem_events']}")

if __name__ == "__main__":
    generate_all()
ENDSCRIPT

echo "   ✓ Script created"
echo ""

# Step 3: Copy to any running pod that has Python/psycopg2
echo "📤 Step 3: Copying script to risk-scorer pod..."
kubectl cp /tmp/generate_ieee_data.py $NAMESPACE/$RISK_SCORER_POD:/tmp/generate_ieee_data.py
echo "   ✓ Script copied"
echo ""

# Step 4: Run the generator
echo "🚀 Step 4: Running IEEE data generator..."
kubectl exec -n $NAMESPACE $RISK_SCORER_POD -- python3 /tmp/generate_ieee_data.py
echo ""

# Step 5: Trigger risk score recalculation
echo "📊 Step 5: Triggering risk score calculation..."
kubectl exec -n $NAMESPACE $RISK_SCORER_POD -- python3 -c "
import sys
sys.path.insert(0, '/app')
from src.engine.risk_scorer import RiskScorer
scorer = RiskScorer()
scorer.calculate_all_user_scores()
print('   ✅ Risk scores calculated for all users')
"
echo ""

# Step 6: Verify data
echo "📋 Step 6: Verifying generated data..."
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "
SELECT 'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Git Events', COUNT(*) FROM git_activity
UNION ALL
SELECT 'Jira Events', COUNT(*) FROM jira_activity
UNION ALL
SELECT 'IAM Events', COUNT(*) FROM iam_events
UNION ALL
SELECT 'SIEM Alerts', COUNT(*) FROM siem_alerts
UNION ALL
SELECT 'Risk Profiles', COUNT(*) FROM user_risk_profiles;
"

echo ""
echo "📊 Risk Score Distribution:"
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U postgres -d security_training -c "
SELECT 
    CASE 
        WHEN overall_risk_score >= 0.7 THEN 'High (>=0.7)'
        WHEN overall_risk_score >= 0.3 THEN 'Medium (0.3-0.7)'
        ELSE 'Low (<0.3)'
    END as risk_category,
    COUNT(*) as user_count,
    ROUND(AVG(overall_risk_score)::numeric, 3) as avg_score
FROM user_risk_profiles
GROUP BY 1
ORDER BY 2 DESC;
"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    DATA REGENERATION COMPLETE!                       ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Now run: python3 scripts/collect_ieee_evidence.py"
