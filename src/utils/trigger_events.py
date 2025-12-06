import time
from src.base.database import Database
from src.collectors.git_collector import GitCollector
from src.collectors.iam_collector import IAMCollector
from src.collectors.jira_collector import JiraCollector
from src.collectors.siem_collector import SIEMCollector

def trigger_all():
    Database.init_pool()
    
    # Fetch all users
    users = []
    with Database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, email FROM users")
            users = cur.fetchall()
            
    print(f"🚀 Triggering event generation for {len(users)} users...")
    
    # Instantiate collectors (they connect to DB)
    git = GitCollector()
    iam = IAMCollector()
    jira = JiraCollector()
    siem = SIEMCollector()
    
    start_time = time.time()
    stats = {"git": 0, "iam": 0, "jira": 0, "siem": 0}
    
    for user_id, email in users:
        print(f"  -> Generating events for {email}...")
        
        # Git: Tailored to stack
        stats["git"] += git._generate_synthetic_events(user_id, email)
        
        # Jira: Overdue tickets
        jira_res = jira._collect_jira_activity(email)
        if jira_res.get("generated_tickets"): stats["jira"] += 1
            
        # IAM: Cloud risks
        iam_res = iam.handle_request('/collect', {'user_email': email}, 'internal-trigger')
        if iam_res.get("events_generated"): stats["iam"] += 1
            
        # SIEM: Phishing
        siem_res = siem.handle_request('/collect', {'user_email': email}, 'internal-trigger')
        if siem_res.get("events_generated"): stats["siem"] += 1
        
    duration = time.time() - start_time
    print(f"\n✅ Simulation Complete in {duration:.2f}s")
    print(f"📊 Stats: {stats}")

if __name__ == "__main__":
    trigger_all()
