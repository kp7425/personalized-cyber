"""
Historical Metadata Generator - Populates the Central Metadata Database
with realistic, multi-day fake data for the IEEE simulation.

This acts as if we had a Stacklet-like connector pulling data from:
- GitHub/GitLab
- Jira
- AWS/GCP/Azure
- SIEM (Splunk/Sentinel)
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from src.base.database import Database
import json
import uuid

fake = Faker()

# Extended Job Profiles with more applications
JOB_PROFILES = [
    {"title": "Data Engineer", "stack": ["python", "gcp", "bigquery", "airflow"], "dept": "Data Platform"},
    {"title": "Frontend Developer", "stack": ["javascript", "react", "aws", "cloudfront"], "dept": "Product"},
    {"title": "Backend Developer", "stack": ["java", "spring", "aws", "rds", "dynamodb"], "dept": "Engineering"},
    {"title": "DevOps Engineer", "stack": ["terraform", "kubernetes", "azure", "aks", "jenkins"], "dept": "Platform"},
    {"title": "Security Analyst", "stack": ["python", "splunk", "aws", "iam", "sentinel"], "dept": "Security"},
    {"title": "ML Engineer", "stack": ["python", "gcp", "vertex-ai", "bigquery"], "dept": "AI/ML"},
    {"title": "Mobile Developer", "stack": ["kotlin", "swift", "firebase", "gcp"], "dept": "Mobile"},
    {"title": "SRE", "stack": ["go", "kubernetes", "aws", "datadog", "terraform"], "dept": "Reliability"},
]

# Applications that can appear in events
APPLICATIONS = {
    "git": ["github", "gitlab", "bitbucket"],
    "jira": ["jira-cloud", "jira-server"],
    "cloud": ["aws", "gcp", "azure"],
    "siem": ["splunk", "sentinel", "crowdstrike", "elastic"],
}

class HistoricalDataGenerator:
    
    def __init__(self, days_of_history=30):
        self.days = days_of_history
        Database.init_pool()
    
    def generate_all(self, user_count=50):
        """Main entry point - generates users and all their historical events."""
        print(f"🏗️  Generating {self.days} days of historical data for {user_count} users...")
        
        users = self._seed_users(user_count)
        
        for user in users:
            self._generate_git_history(user)
            self._generate_jira_history(user)
            self._generate_iam_history(user)
            self._generate_siem_history(user)
        
        print(f"✅ Historical data generation complete!")
        return len(users)
    
    def _seed_users(self, count):
        """Create users with diverse profiles."""
        users = []
        print(f"  👤 Seeding {count} users...")
        
        for i in range(count):
            profile = random.choice(JOB_PROFILES)
            user_id = str(uuid.uuid4())
            workday_id = f"WD-{10000 + i}"
            email = f"{fake.first_name().lower()}.{fake.last_name().lower()}@example.org"
            
            try:
                with Database.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO users (
                                user_id, workday_id, email, full_name, 
                                department, job_title, job_profile, tech_stack, hire_date
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (email) DO UPDATE SET user_id = EXCLUDED.user_id
                            RETURNING user_id
                        """, (
                            user_id, workday_id, email, fake.name(),
                            profile["dept"], profile["title"], profile["title"],
                            json.dumps(profile["stack"]),
                            fake.date_between(start_date='-3y', end_date='-6m')
                        ))
                        result = cur.fetchone()
                        conn.commit()
                        users.append({
                            "user_id": result[0] if result else user_id,
                            "email": email,
                            "stack": profile["stack"],
                            "profile": profile["title"]
                        })
            except Exception as e:
                print(f"    Error creating user: {e}")
        
        print(f"    ✓ {len(users)} users created")
        return users
    
    def _generate_git_history(self, user):
        """Generate realistic git events over the history period."""
        stack = user["stack"]
        events_per_day = random.randint(2, 10)  # Commits per day
        
        for day_offset in range(self.days):
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            for _ in range(events_per_day):
                event_type = random.choices(
                    ["commit", "commit", "commit", "force_push", "secret_detected"],
                    weights=[70, 15, 10, 3, 2]
                )[0]
                
                # Language-specific repos
                if "python" in stack:
                    repo = random.choice(["ml-pipeline", "data-etl", "api-service"])
                elif "javascript" in stack:
                    repo = random.choice(["customer-portal", "admin-dashboard", "mobile-web"])
                elif "java" in stack:
                    repo = random.choice(["payment-service", "order-api", "legacy-monolith"])
                else:
                    repo = random.choice(["infra-live", "k8s-configs", "terraform-modules"])
                
                raw_data = {"simulated": True, "source": random.choice(APPLICATIONS["git"])}
                
                if event_type == "secret_detected":
                    raw_data["secret_type"] = random.choice(["aws_key", "gcp_sa_key", "api_token"])
                    raw_data["severity"] = "CRITICAL"
                
                self._insert_git_event(user["user_id"], event_type, f"org/{repo}", event_date, raw_data)
    
    def _generate_jira_history(self, user):
        """Generate Jira security tickets."""
        # Not every user gets security tickets
        if random.random() > 0.4:
            return
        
        for day_offset in range(0, self.days, random.randint(3, 10)):
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            ticket_type = random.choice(["security_vulnerability", "compliance_issue", "incident"])
            priority = random.choice(["Critical", "High", "Medium", "Low"])
            status = random.choice(["Open", "In Progress", "Resolved", "Overdue"])
            
            due_date = event_date + timedelta(days=random.randint(1, 14))
            
            self._insert_jira_event(
                user["user_id"], "ticket_assigned",
                f"SEC-{random.randint(1000, 9999)}", ticket_type, priority, status,
                due_date, event_date
            )
    
    def _generate_iam_history(self, user):
        """Generate cloud IAM events based on user's stack."""
        stack = user["stack"]
        
        for day_offset in range(0, self.days, random.randint(1, 5)):
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            if "aws" in stack:
                self._insert_iam_event(
                    user["user_id"], "aws",
                    random.choice(["AssumeRole", "CreateAccessKey", "AttachUserPolicy"]),
                    f"arn:aws:iam::123456789012:role/{random.choice(['Admin', 'Developer', 'ReadOnly'])}",
                    random.choice([True, False]),  # is_privileged
                    event_date
                )
            
            if "gcp" in stack:
                self._insert_iam_event(
                    user["user_id"], "gcp",
                    random.choice(["SetIamPolicy", "CreateServiceAccountKey"]),
                    f"projects/prod-{random.randint(100,999)}/roles/{random.choice(['owner', 'editor', 'viewer'])}",
                    random.choice([True, False]),
                    event_date
                )
            
            if "azure" in stack:
                self._insert_iam_event(
                    user["user_id"], "azure",
                    random.choice(["SignIn", "AddMember", "ActivateRole"]),
                    f"subscriptions/{uuid.uuid4()}/resourceGroups/prod",
                    random.choice([True, False]),
                    event_date
                )
    
    def _generate_siem_history(self, user):
        """Generate SIEM alerts (phishing, malware, policy violations)."""
        # Only some users have SIEM alerts
        if random.random() > 0.3:
            return
        
        alert_count = random.randint(1, 5)
        
        for _ in range(alert_count):
            day_offset = random.randint(0, self.days)
            event_date = datetime.utcnow() - timedelta(days=day_offset)
            
            alert_type = random.choice(["phishing", "malware", "policy_violation", "anomalous_login"])
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
        except Exception as e:
            pass  # Silently continue on duplicates
    
    def _insert_jira_event(self, user_id, event_type, ticket_key, ticket_type, priority, status, due_date, timestamp):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO jira_activity (user_id, event_type, ticket_key, ticket_type, priority, status, due_date, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, event_type, ticket_key, ticket_type, priority, status, due_date, timestamp, json.dumps({"simulated": True})))
                    conn.commit()
        except Exception as e:
            pass
    
    def _insert_iam_event(self, user_id, cloud_provider, event_type, resource_arn, is_privileged, timestamp):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO iam_events (user_id, cloud_provider, event_type, resource_arn, is_privileged, event_timestamp, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, cloud_provider, event_type, resource_arn, is_privileged, timestamp, json.dumps({"simulated": True})))
                    conn.commit()
        except Exception as e:
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
        except Exception as e:
            pass


if __name__ == "__main__":
    generator = HistoricalDataGenerator(days_of_history=30)
    generator.generate_all(user_count=50)
