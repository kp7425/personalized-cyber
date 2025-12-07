"""
Historical Metadata Generator - IEEE Paper Version

Populates the Central Metadata Database with realistic, role-based fake data.
Implements temporal patterns, cross-system correlation, and ground truth labels.

Based on: SYNTHETIC_DATA_SPEC.md
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from src.base.database import Database
import json
import uuid
from typing import Dict, List, Any

fake = Faker()

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
        "expected_risk": (0.6, 0.9),  # High risk
        "ground_truth": "HIGH"
    },
    {
        "title": "Frontend Developer",
        "profile_key": "frontend_developer",
        "stack": ["javascript", "react", "typescript", "aws"],
        "dept": "Product",
        "count": 8,
        "expected_risk": (0.4, 0.6),  # Medium risk
        "ground_truth": "MEDIUM"
    },
    {
        "title": "DevOps Engineer",
        "profile_key": "devops_engineer",
        "stack": ["terraform", "kubernetes", "aws", "gcp"],
        "dept": "Platform",
        "count": 8,
        "expected_risk": (0.6, 0.8),  # High IAM risk
        "ground_truth": "HIGH"
    },
    {
        "title": "DevSecOps Engineer",
        "profile_key": "devsecops_engineer",
        "stack": ["python", "aws", "gcp", "splunk"],
        "dept": "Security",
        "count": 4,
        "expected_risk": (0.1, 0.3),  # Low risk - Control
        "ground_truth": "LOW"
    },
    {
        "title": "Cloud Security Analyst",
        "profile_key": "cloud_security_analyst",
        "stack": ["aws", "gcp", "sentinel", "crowdstrike"],
        "dept": "Security",
        "count": 3,
        "expected_risk": (0.0, 0.2),  # Very low - Control
        "ground_truth": "VERY_LOW"
    },
    {
        "title": "Data Analyst",
        "profile_key": "data_analyst",
        "stack": ["python", "sql", "bigquery", "gcp"],
        "dept": "Data Platform",
        "count": 6,
        "expected_risk": (0.3, 0.5),  # Medium - Data exfil risk
        "ground_truth": "MEDIUM"
    },
    {
        "title": "Data Engineer",
        "profile_key": "data_engineer",
        "stack": ["python", "spark", "airflow", "bigquery", "gcp"],
        "dept": "Data Platform",
        "count": 6,
        "expected_risk": (0.5, 0.8),  # High IAM + data risk
        "ground_truth": "HIGH"
    },
    {
        "title": "SRE",
        "profile_key": "sre",
        "stack": ["go", "kubernetes", "terraform", "aws", "gcp"],
        "dept": "Reliability",
        "count": 3,
        "expected_risk": (0.2, 0.9),  # Variable
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
        "iam_events_30d": (30, 100),  # High IAM activity
        "privileged_probability": 0.4,  # Creates privileged roles
        "siem_alerts_30d": (0, 3)
    },
    "devsecops_engineer": {  # Control - Low risk
        "git_commits_per_day": (3, 8),
        "secrets_probability": 0.01,  # Very low
        "force_push_probability": 0.01,
        "jira_tickets_30d": (20, 40),  # Many tickets - they fix things
        "overdue_probability": 0.05,
        "iam_events_30d": (20, 50),
        "privileged_probability": 0.1,
        "siem_alerts_30d": (0, 1)
    },
    "cloud_security_analyst": {  # Control - Very low risk
        "git_commits_per_day": (0, 2),  # Minimal code
        "secrets_probability": 0.0,
        "force_push_probability": 0.0,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.02,
        "iam_events_30d": (50, 150),  # High IAM - but read-only
        "privileged_probability": 0.02,
        "siem_alerts_30d": (0, 0)
    },
    "data_analyst": {
        "git_commits_per_day": (1, 5),
        "secrets_probability": 0.05,
        "force_push_probability": 0.02,
        "jira_tickets_30d": (5, 15),
        "overdue_probability": 0.15,
        "iam_events_30d": (20, 60),  # BigQuery access
        "privileged_probability": 0.15,
        "siem_alerts_30d": (0, 2)
    },
    "data_engineer": {
        "git_commits_per_day": (3, 10),
        "secrets_probability": 0.10,
        "force_push_probability": 0.08,
        "jira_tickets_30d": (10, 25),
        "overdue_probability": 0.2,
        "iam_events_30d": (40, 100),  # High - creates SA keys
        "privileged_probability": 0.35,
        "siem_alerts_30d": (0, 3)
    },
    "sre": {  # Variable - spikes during incidents
        "git_commits_per_day": (2, 8),
        "secrets_probability": 0.08,
        "force_push_probability": 0.20,  # High during incidents
        "jira_tickets_30d": (15, 30),
        "overdue_probability": 0.25,
        "iam_events_30d": (30, 80),
        "privileged_probability": 0.5,  # Break-glass usage
        "siem_alerts_30d": (0, 5)
    }
}

# ============================================================================
# TEMPORAL PATTERNS (Week 3 = Spike)
# ============================================================================

TEMPORAL_MULTIPLIERS = {
    "week_1": 1.0,   # Baseline
    "week_2": 1.0,   # Steady
    "week_3": 3.0,   # SPIKE - deadlines, incidents
    "week_4": 0.8    # Recovery
}

# ============================================================================
# APPLICATIONS
# ============================================================================

APPLICATIONS = {
    "git": ["github", "gitlab", "bitbucket"],
    "jira": ["jira-cloud"],
    "cloud": ["aws", "gcp", "azure"],
    "siem": ["splunk", "sentinel", "crowdstrike", "elastic"],
}


class HistoricalDataGenerator:
    """Generates 30 days of historical data per SYNTHETIC_DATA_SPEC.md"""
    
    def __init__(self, days_of_history: int = 30):
        self.days = days_of_history
        Database.init_pool()
        self.ground_truth_labels = []
    
    def generate_all(self, user_count: int = 50) -> Dict[str, Any]:
        """Main entry point."""
        print(f"🏗️  Generating {self.days} days of historical data...")
        print(f"   Using 8 IEEE paper roles with temporal patterns")
        
        users = self._seed_users()
        
        for user in users:
            self._generate_git_history(user)
            self._generate_jira_history(user)
            self._generate_iam_history(user)
            self._generate_siem_history(user)
        
        print(f"\n✅ Historical data generation complete!")
        print(f"   Users: {len(users)}")
        print(f"   Ground truth labels: {len(self.ground_truth_labels)}")
        
        return {
            "users_created": len(users),
            "ground_truth_labels": self.ground_truth_labels[:10]  # Sample
        }
    
    def _seed_users(self) -> List[Dict]:
        """Create users based on IEEE spec distribution."""
        users = []
        print(f"\n  👤 Seeding users by role...")
        
        user_index = 0
        for profile in JOB_PROFILES:
            count = profile["count"]
            print(f"     {profile['title']}: {count} users ({profile['ground_truth']} risk)")
            
            for i in range(count):
                user_id = str(uuid.uuid4())
                workday_id = f"WD-{10000 + user_index}"
                email = f"{fake.first_name().lower()}.{fake.last_name().lower()}@example.org"
                
                try:
                    with Database.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                INSERT INTO users (
                                    user_id, workday_id, email, full_name, 
                                    department, job_title, job_profile, tech_stack, hire_date
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (email) DO UPDATE SET 
                                    user_id = EXCLUDED.user_id,
                                    job_profile = EXCLUDED.job_profile
                                RETURNING user_id
                            """, (
                                user_id, workday_id, email, fake.name(),
                                profile["dept"], profile["title"], profile["profile_key"],
                                json.dumps(profile["stack"]),
                                fake.date_between(start_date='-3y', end_date='-6m')
                            ))
                            result = cur.fetchone()
                            conn.commit()
                            
                            user = {
                                "user_id": result[0] if result else user_id,
                                "email": email,
                                "stack": profile["stack"],
                                "profile_key": profile["profile_key"],
                                "expected_risk": profile["expected_risk"],
                                "ground_truth": profile["ground_truth"]
                            }
                            users.append(user)
                            
                            # Add to ground truth for first 10 users
                            if len(self.ground_truth_labels) < 10:
                                self.ground_truth_labels.append({
                                    "employee_id": workday_id,
                                    "role": profile["title"],
                                    "ground_truth": profile["ground_truth"],
                                    "justification": f"Role-based: {profile['dept']}"
                                })
                            
                except Exception as e:
                    print(f"    Error creating user: {e}")
                
                user_index += 1
        
        print(f"    ✓ {len(users)} users created")
        return users
    
    def _get_week_multiplier(self, day_offset: int) -> float:
        """Get temporal multiplier based on which week we're in."""
        if day_offset >= 21:  # Week 4 (days 21-30)
            return TEMPORAL_MULTIPLIERS["week_4"]
        elif day_offset >= 14:  # Week 3 (days 14-21) - SPIKE
            return TEMPORAL_MULTIPLIERS["week_3"]
        elif day_offset >= 7:  # Week 2 (days 7-14)
            return TEMPORAL_MULTIPLIERS["week_2"]
        else:  # Week 1 (days 0-7)
            return TEMPORAL_MULTIPLIERS["week_1"]
    
    def _generate_git_history(self, user: Dict):
        """Generate realistic git events with temporal patterns."""
        profile_key = user["profile_key"]
        config = EVENT_CONFIG.get(profile_key, EVENT_CONFIG["backend_developer"])
        stack = user["stack"]
        
        for day_offset in range(self.days):
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            multiplier = self._get_week_multiplier(day_offset)
            
            # Commits per day with temporal multiplier
            base_commits = random.randint(*config["git_commits_per_day"])
            commits_today = int(base_commits * multiplier)
            
            for _ in range(commits_today):
                # Determine event type with role-based probabilities
                if random.random() < config["secrets_probability"] * multiplier:
                    event_type = "secret_detected"
                elif random.random() < config["force_push_probability"] * multiplier:
                    event_type = "force_push"
                else:
                    event_type = "commit"
                
                # Language-specific repos
                if "python" in stack:
                    repo = random.choice(["ml-pipeline", "data-etl", "api-service", "analytics"])
                elif "javascript" in stack:
                    repo = random.choice(["customer-portal", "admin-dashboard", "mobile-web"])
                elif "java" in stack:
                    repo = random.choice(["payment-service", "order-api", "auth-service"])
                elif "terraform" in stack:
                    repo = random.choice(["infra-live", "k8s-configs", "terraform-modules"])
                else:
                    repo = random.choice(["shared-libs", "config-repo", "scripts"])
                
                raw_data = {
                    "simulated": True, 
                    "source": random.choice(APPLICATIONS["git"]),
                    "temporal_week": (self.days - day_offset) // 7 + 1
                }
                
                if event_type == "secret_detected":
                    raw_data["secret_type"] = random.choice(["aws_key", "gcp_sa_key", "api_token", "db_password"])
                    raw_data["severity"] = "CRITICAL"
                
                self._insert_git_event(user["user_id"], event_type, f"org/{repo}", event_date, raw_data)
    
    def _generate_jira_history(self, user: Dict):
        """Generate Jira security tickets."""
        profile_key = user["profile_key"]
        config = EVENT_CONFIG.get(profile_key, EVENT_CONFIG["backend_developer"])
        
        total_tickets = random.randint(*config["jira_tickets_30d"])
        
        for _ in range(total_tickets):
            day_offset = random.randint(0, self.days - 1)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            ticket_type = random.choice(["security_vulnerability", "compliance_issue", "incident", "security_review"])
            priority = random.choice(["Critical", "High", "Medium", "Low"])
            
            # Determine if overdue based on role probability
            if random.random() < config["overdue_probability"]:
                status = "Overdue"
            else:
                status = random.choice(["Open", "In Progress", "Resolved"])
            
            due_date = event_date + timedelta(days=random.randint(1, 14))
            
            self._insert_jira_event(
                user["user_id"], "ticket_assigned",
                f"SEC-{random.randint(1000, 9999)}", ticket_type, priority, status,
                due_date, event_date
            )
    
    def _generate_iam_history(self, user: Dict):
        """Generate cloud IAM events with role-based patterns."""
        profile_key = user["profile_key"]
        config = EVENT_CONFIG.get(profile_key, EVENT_CONFIG["backend_developer"])
        stack = user["stack"]
        
        total_events = random.randint(*config["iam_events_30d"])
        
        for _ in range(total_events):
            day_offset = random.randint(0, self.days - 1)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            multiplier = self._get_week_multiplier(day_offset)
            
            # Determine if privileged based on role + temporal
            is_privileged = random.random() < (config["privileged_probability"] * multiplier)
            
            # Off-hours detection (for correlation)
            hour = random.randint(0, 23)
            off_hours = hour < 6 or hour > 22
            
            # Cloud-specific events
            if "aws" in stack:
                event_type = random.choice(["AssumeRole", "CreateAccessKey", "AttachUserPolicy", "UpdateAssumeRolePolicy"])
                resource = f"arn:aws:iam::123456789012:role/{random.choice(['Admin', 'Developer', 'ReadOnly', 'DataAccess'])}"
                self._insert_iam_event(user["user_id"], "aws", event_type, resource, is_privileged, event_date, off_hours)
            
            if "gcp" in stack:
                event_type = random.choice(["SetIamPolicy", "CreateServiceAccountKey", "SetIamBindings"])
                resource = f"projects/prod-{random.randint(100,999)}/roles/{random.choice(['owner', 'editor', 'viewer', 'bigquery.admin'])}"
                self._insert_iam_event(user["user_id"], "gcp", event_type, resource, is_privileged, event_date, off_hours)
            
            if "azure" in stack:
                event_type = random.choice(["SignIn", "AddMember", "ActivateRole", "CreateServicePrincipal"])
                resource = f"subscriptions/{uuid.uuid4()}/resourceGroups/prod"
                self._insert_iam_event(user["user_id"], "azure", event_type, resource, is_privileged, event_date, off_hours)
    
    def _generate_siem_history(self, user: Dict):
        """Generate SIEM alerts."""
        profile_key = user["profile_key"]
        config = EVENT_CONFIG.get(profile_key, EVENT_CONFIG["backend_developer"])
        
        min_alerts, max_alerts = config["siem_alerts_30d"]
        alert_count = random.randint(min_alerts, max_alerts)
        
        for _ in range(alert_count):
            day_offset = random.randint(0, self.days - 1)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            alert_type = random.choice(["phishing", "malware", "policy_violation", "anomalous_login", "data_exfiltration"])
            severity = random.choice(["low", "medium", "high", "critical"])
            source = random.choice(APPLICATIONS["siem"])
            
            self._insert_siem_event(user["user_id"], alert_type, severity, source, event_date)
    
    # --- Database Insert Methods ---
    
    def _insert_git_event(self, user_id, event_type, repo, timestamp, raw_data):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO git_activity (user_id, event_type, repository, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, event_type, repo, timestamp, json.dumps(raw_data)))
                    conn.commit()
        except Exception:
            pass
    
    def _insert_jira_event(self, user_id, event_type, ticket_key, ticket_type, priority, status, due_date, timestamp):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO jira_activity (user_id, event_type, ticket_key, ticket_type, priority, status, due_date, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, event_type, ticket_key, ticket_type, priority, status, due_date, timestamp, json.dumps({"simulated": True})))
                    conn.commit()
        except Exception:
            pass
    
    def _insert_iam_event(self, user_id, cloud_provider, event_type, resource_arn, is_privileged, timestamp, off_hours=False):
        try:
            raw_data = {"simulated": True, "off_hours": off_hours}
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO iam_events (user_id, cloud_provider, event_type, resource_arn, is_privileged, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, cloud_provider, event_type, resource_arn, is_privileged, timestamp, json.dumps(raw_data)))
                    conn.commit()
        except Exception:
            pass
    
    def _insert_siem_event(self, user_id, alert_type, severity, source_system, timestamp):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO siem_alerts (user_id, alert_type, severity, source_system, alert_name, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, alert_type, severity, source_system, f"Simulated {alert_type}", timestamp, json.dumps({"simulated": True})))
                    conn.commit()
        except Exception:
            pass


if __name__ == "__main__":
    generator = HistoricalDataGenerator(days_of_history=30)
    result = generator.generate_all()
    
    print("\n📊 Ground Truth Labels (First 10):")
    for label in result["ground_truth_labels"]:
        print(f"   {label['employee_id']}: {label['role']} → {label['ground_truth']}")
