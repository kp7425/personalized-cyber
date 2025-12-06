import random
from faker import Faker
from src.base.database import Database, UserRepository
import json
import uuid

fake = Faker()

JOB_PROFILES = [
    {"title": "Data Engineer", "stack": ["python", "gcp", "bigquery", "airflow"]},
    {"title": "Frontend Developer", "stack": ["javascript", "react", "aws", "cloudfront"]},
    {"title": "Backend Developer", "stack": ["java", "spring", "aws", "rds"]},
    {"title": "DevOps Engineer", "stack": ["terraform", "kubernetes", "azure", "aks"]},
    {"title": "Security Analyst", "stack": ["python", "splunk", "aws", "iam"]},
]

class SimulationSeeder:
    @staticmethod
    def seed_users(count=50):
        """Generates synthetic users with specific job profiles and tech stacks."""
        Database.init_pool()
        users_created = 0
        
        print(f"🌱 Seeding {count} users...")
        
        for _ in range(count):
            profile = random.choice(JOB_PROFILES)
            
            # Deterministic workday ID for reproducibility
            workday_id = f"WD-{random.randint(10000, 99999)}"
            email = fake.email()
            
            try:
                # Check if user exists (simple check)
                existing = UserRepository.get_by_email(email)
                if existing:
                    continue

                # Insert into DB (using raw query since Repository might not have new columns yet)
                with Database.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO users (
                                user_id, workday_id, email, full_name, 
                                department, job_title, job_profile, tech_stack
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (email) DO NOTHING
                        """, (
                            str(uuid.uuid4()),
                            workday_id,
                            email,
                            fake.name(),
                            "Engineering",
                            profile["title"],
                            profile["title"],
                            json.dumps(profile["stack"])
                        ))
                        users_created += 1
                        conn.commit()
            except Exception as e:
                print(f"Error seeding user: {e}")
                
        print(f"✅ Created {users_created} new users.")

if __name__ == "__main__":
    SimulationSeeder.seed_users()
