"""Jira Collector - ONLY Jira-specific logic!"""

import os
import random
from datetime import datetime
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import Database, JiraActivityRepository


class JiraCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="jira-collector",
            port=8502,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/risk-scorer"
            ]
        )
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_token = os.getenv('JIRA_API_TOKEN')
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            return self._collect_jira_activity(data.get('user_email'))
        elif path == '/stats':
            return self._get_user_stats(data.get('user_id'))
        return {"error": "Unknown path"}
    
    def _collect_jira_activity(self, user_email: str) -> dict:
        """
        IEEE PAPER SIMULATION:
        Generates simulated overdue security tickets to trigger the 'Training Gap' risk.
        """
        if not user_email: return {"error": "Missing user_email"}
        
        # 1. Lookup User ID
        from src.base.database import UserRepository
        user = UserRepository.get_by_email(user_email)
        if not user:
             return {"error": "User not found in DB"}
        user_id = user['user_id']

        # 2. Fetch user profile for context
        from src.base.database import Database
        user_stack = []
        with Database.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tech_stack FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row and row[0]: user_stack = row[0]
        
        # Customize Ticket based on Role
        ticket_summary = "Security Vulnerability"
        if "terraform" in user_stack:
            ticket_summary = "Unencrypted EBS Volumes in Prod"
        elif "react" in user_stack:
            ticket_summary = "XSS Vulnerability in Login Form"
        elif "python" in user_stack:
            ticket_summary = "Hardcoded API Keys in Scripts"
        
        # Simulate: 1 Critical Vulnerability Overdue
        JiraActivityRepository.insert(
            user_id=user_id,
            event_type='ticket_assigned',
            ticket_key=f"SEC-{random.randint(1000,9999)}",
            ticket_type="security_vulnerability",
            priority="High",
            status="In Progress",
            due_date=datetime.utcnow(), 
            raw_data={"simulated": True, "summary": ticket_summary}
        )
        
        return {
            "user_email": user_email,
            "status": "simulation_complete",
            "generated_tickets": 1
        }
    
    def _get_user_stats(self, user_id: str) -> dict:
        return JiraActivityRepository.get_user_stats(user_id)


if __name__ == '__main__':
    JiraCollector().run()
