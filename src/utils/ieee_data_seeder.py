#!/usr/bin/env python3
"""
IEEE Paper Data Seeder - Automated deployment data generation

This module is called by the Kubernetes Job ieee-data-seeder during
Helm install to populate the database with reproducible IEEE paper data.

Generates:
- 50 users with 8 IEEE-spec role distribution
- 30 days of multi-source behavioral events (Git, Jira, IAM, SIEM)
- Training completion records
- Temporal patterns (Week 3 spike)
"""

import os
import sys
import random
import uuid
import json
import time
from datetime import datetime, timedelta
from faker import Faker

# Add app to path when running in container
sys.path.insert(0, "/app")

import psycopg2

fake = Faker()
Faker.seed(42)  # Reproducibility for IEEE paper
random.seed(42)

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
        "secrets_probability": 0.12,
        "force_push_probability": 0.08,
        "jira_tickets_30d": (15, 30),
        "overdue_probability": 0.3,
        "iam_events_30d": (10, 30),
        "privileged_probability": 0.2,
        "siem_alerts_30d": (1, 4),
        "training_completion_rate": 0.3,
        "training_modules": 2
    },
    "frontend_developer": {
        "git_commits_per_day": (3, 10),
        "secrets_probability": 0.06,
        "force_push_probability": 0.04,
        "jira_tickets_30d": (10, 20),
        "overdue_probability": 0.2,
        "iam_events_30d": (5, 15),
        "privileged_probability": 0.05,
        "siem_alerts_30d": (0, 2),
        "training_completion_rate": 0.5,
        "training_modules": 4
    },
    "devops_engineer": {
        "git_commits_per_day": (2, 8),
        "secrets_probability": 0.10,
        "force_push_probability": 0.12,
        "jira_tickets_30d": (10, 25),
        "overdue_probability": 0.25,
        "iam_events_30d": (30, 100),
        "privileged_probability": 0.4,
        "siem_alerts_30d": (1, 4),
        "training_completion_rate": 0.4,
        "training_modules": 3
    },
    "devsecops_engineer": {  # Control - Low risk
        "git_commits_per_day": (3, 8),
        "secrets_probability": 0.01,  # Very low
        "force_push_probability": 0.01,
        "jira_tickets_30d": (20, 40),
        "overdue_probability": 0.05,
        "iam_events_30d": (20, 50),
        "privileged_probability": 0.05,  # Low privileged actions
        "siem_alerts_30d": (0, 0),  # No SIEM alerts
        "training_completion_rate": 1.0,  # 100% training
        "training_modules": 10
    },
    "cloud_security_analyst": {  # Control - Very low risk
        "git_commits_per_day": (0, 2),
        "secrets_probability": 0.0,
        "force_push_probability": 0.0,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.02,
        "iam_events_30d": (50, 150),  # Many read-only audits
        "privileged_probability": 0.02,
        "siem_alerts_30d": (0, 0),
        "training_completion_rate": 1.0,
        "training_modules": 10
    },
    "data_analyst": {
        "git_commits_per_day": (1, 5),
        "secrets_probability": 0.04,
        "force_push_probability": 0.02,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.15,
        "iam_events_30d": (20, 60),
        "privileged_probability": 0.15,
        "siem_alerts_30d": (0, 2),
        "training_completion_rate": 0.6,
        "training_modules": 5
    },
    "data_engineer": {
        "git_commits_per_day": (3, 10),
        "secrets_probability": 0.08,
        "force_push_probability": 0.06,
        "jira_tickets_30d": (10, 25),
        "overdue_probability": 0.2,
        "iam_events_30d": (40, 100),
        "privileged_probability": 0.35,
        "siem_alerts_30d": (1, 4),
        "training_completion_rate": 0.35,
        "training_modules": 3
    },
    "sre": {
        "git_commits_per_day": (2, 8),
        "secrets_probability": 0.06,
        "force_push_probability": 0.15,
        "jira_tickets_30d": (15, 30),
        "overdue_probability": 0.25,
        "iam_events_30d": (30, 80),
        "privileged_probability": 0.5,
        "siem_alerts_30d": (0, 5),
        "training_completion_rate": 0.5,
        "training_modules": 4
    }
}

TEMPORAL_MULTIPLIERS = {
    "week_1": 1.0,
    "week_2": 1.0,
    "week_3": 2.5,  # SPIKE
    "week_4": 0.8
}

TRAINING_MODULES = [
    ("SEC-001", "Phishing Awareness", "phishing"),
    ("SEC-002", "Password Security", "password"),
    ("SEC-003", "Secure Coding Basics", "secure_coding"),
    ("SEC-004", "Data Handling & Privacy", "data_handling"),
    ("SEC-005", "Cloud Security Fundamentals", "cloud_security"),
    ("SEC-006", "Incident Response", "incident_response"),
    ("SEC-007", "API Security", "api_security"),
    ("SEC-008", "Container Security", "container_security"),
    ("SEC-009", "IAM Best Practices", "iam"),
    ("SEC-010", "Social Engineering Defense", "social_engineering")
]


def get_week_multiplier(day_offset):
    if day_offset >= 21:
        return TEMPORAL_MULTIPLIERS["week_4"]
    elif day_offset >= 14:
        return TEMPORAL_MULTIPLIERS["week_3"]
    elif day_offset >= 7:
        return TEMPORAL_MULTIPLIERS["week_2"]
    else:
        return TEMPORAL_MULTIPLIERS["week_1"]


def get_db_connection():
    """Get database connection with retry logic."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(
                host=os.getenv("DB_HOST", "postgres-svc"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "security_training"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "securepassword123")
            )
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   Database connection attempt {attempt + 1} failed, retrying in 5s...")
                time.sleep(5)
            else:
                raise e


def check_data_exists(conn):
    """Check if data already exists to avoid duplicate seeding."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    cur.close()
    return count > 0


def seed_ieee_data():
    """Main seeding function for IEEE paper data."""
    print("=" * 70)
    print("IEEE PAPER DATA SEEDER - Zero-Trust Personalized CybersecurityTraining")
    print("=" * 70)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("")
    
    conn = get_db_connection()
    
    # Check if already seeded
    if check_data_exists(conn):
        print("✅ Data already exists - skipping seeding")
        print("   (Delete data manually if you want to re-seed)")
        conn.close()
        return {"status": "skipped", "reason": "data_exists"}
    
    cur = conn.cursor()
    
    stats = {
        "users": 0,
        "git_events": 0,
        "jira_events": 0,
        "iam_events": 0,
        "siem_events": 0,
        "training_records": 0
    }
    
    users = []
    
    # ========================================================================
    # Create users
    # ========================================================================
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
    print(f"   ✅ Created {stats['users']} users\n")
    
    # ========================================================================
    # Generate events for each user
    # ========================================================================
    print("📊 Generating 30 days of behavioral events...")
    
    for user in users:
        config = EVENT_CONFIG.get(user["profile_key"], EVENT_CONFIG["backend_developer"])
        stack = user["stack"]
        user_id = user["user_id"]
        
        # --- Git events ---
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
                """, (user_id, event_type, f"org/{repo}", event_date, json.dumps({"simulated": True})))
                stats["git_events"] += 1
        
        # --- Jira events ---
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
            """, (user_id, "ticket_assigned", f"SEC-{random.randint(1000, 9999)}", ticket_type, priority, status, event_date, json.dumps({"simulated": True})))
            stats["jira_events"] += 1
        
        # --- IAM events ---
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
            """, (user_id, cloud, event_type, f"arn:{cloud}:iam::123456789012:role/SomeRole", is_privileged, event_date, json.dumps({"simulated": True})))
            stats["iam_events"] += 1
        
        # --- SIEM events ---
        min_alerts, max_alerts = config["siem_alerts_30d"]
        alert_count = random.randint(min_alerts, max_alerts)
        for _ in range(alert_count):
            day_offset = random.randint(0, 29)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            alert_type = random.choice(["phishing", "malware", "policy_violation", "anomalous_login", "data_exfiltration"])
            severity = random.choice(["medium", "high", "critical"]) if user["ground_truth"] == "HIGH" else random.choice(["low", "medium"])
            
            cur.execute("""
                INSERT INTO siem_alerts (user_id, alert_type, severity, source_system, alert_name, event_timestamp, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, alert_type, severity, random.choice(["splunk", "sentinel", "crowdstrike"]), f"Simulated {alert_type}", event_date, json.dumps({"simulated": True})))
            stats["siem_events"] += 1
        
        # --- Training completions ---
        completion_rate = config["training_completion_rate"]
        num_modules = config["training_modules"]
        
        available_modules = list(TRAINING_MODULES)
        random.shuffle(available_modules)
        
        for module_id, module_name, category in available_modules[:num_modules]:
            if random.random() < completion_rate:
                days_ago = random.randint(1, 60)
                completed_at = datetime.utcnow() - timedelta(days=days_ago)
                score = random.uniform(80, 100) if user["ground_truth"] in ["LOW", "VERY_LOW"] else random.uniform(65, 90)
                passed = True
            else:
                days_ago = random.randint(90, 365)
                completed_at = datetime.utcnow() - timedelta(days=days_ago)
                score = random.uniform(40, 65)
                passed = False
            
            cur.execute("""
                INSERT INTO training_completions 
                (user_id, module_id, module_name, module_category, score, passed, time_spent_minutes, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, module_id, module_name, category, score, passed, random.randint(15, 60), completed_at))
            stats["training_records"] += 1
    
    conn.commit()
    
    print(f"   ✅ Git Events: {stats['git_events']}")
    print(f"   ✅ Jira Events: {stats['jira_events']}")
    print(f"   ✅ IAM Events: {stats['iam_events']}")
    print(f"   ✅ SIEM Events: {stats['siem_events']}")
    print(f"   ✅ Training Records: {stats['training_records']}")
    print(f"   ✅ Total Events: {sum([stats['git_events'], stats['jira_events'], stats['iam_events'], stats['siem_events']])}")
    
    # ========================================================================
    # Calculate risk scores
    # ========================================================================
    print("\n📈 Calculating risk scores...")
    
    try:
        from src.engine.risk_scorer import RiskScorer
        scorer = RiskScorer()
        
        high_risk = 0
        medium_risk = 0
        low_risk = 0
        
        for user in users:
            try:
                result = scorer._calculate_risk_score(str(user["user_id"]))
                overall = result["scores"]["overall_risk_score"]
                
                if overall >= 0.7:
                    high_risk += 1
                elif overall >= 0.3:
                    medium_risk += 1
                else:
                    low_risk += 1
            except Exception as e:
                print(f"   Warning: Could not score user: {e}")
        
        print(f"   ✅ High Risk (≥0.7): {high_risk}")
        print(f"   ✅ Medium Risk (0.3-0.7): {medium_risk}")
        print(f"   ✅ Low Risk (<0.3): {low_risk}")
        
        stats["high_risk"] = high_risk
        stats["medium_risk"] = medium_risk
        stats["low_risk"] = low_risk
        
    except Exception as e:
        print(f"   ⚠️ Could not calculate scores (will retry later): {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ IEEE PAPER DATA SEEDING COMPLETE!")
    print("=" * 70)
    print(f"\nUsers: {stats['users']}")
    print(f"Total Events: {sum([stats['git_events'], stats['jira_events'], stats['iam_events'], stats['siem_events']])}")
    print(f"Training Records: {stats['training_records']}")
    
    return stats


if __name__ == "__main__":
    try:
        result = seed_ieee_data()
        print(f"\nResult: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
