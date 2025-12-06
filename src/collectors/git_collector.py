"""
Git Collector - Collects from GitHub/GitLab AND saves to database.
"""

import os
import requests
from datetime import datetime
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import Database, UserRepository, GitActivityRepository


class GitCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="git-collector",
            port=8501,
            allowed_callers=[
                # In prod, this would be the SPIFFE ID of the risk scoring engine
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/risk-scorer"
            ]
        )
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_org = os.getenv('GITHUB_ORG', 'your-org')
        
        # Initialize database pool
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            return self._collect_and_save(data.get('user_email'))
        elif path == '/webhook':
            return self._handle_webhook(data)
        elif path == '/stats':
            return self._get_user_stats(data.get('user_id'))
        return {"error": f"Unknown path: {path}"}
    
    def _collect_and_save(self, user_email: str) -> dict:
        """Collect git activity and save to database."""
        if not user_email:
            return {"error": "user_email is required"}
        
        # Get user from database
        user = UserRepository.get_by_email(user_email)
        if not user:
            # Check by workday ID if email fails? Or just return error
            return {"error": f"User not found: {user_email}"}
        
        user_id = user['user_id']
        
        # SIMULATION: Generate fake metadata
        events_saved = self._generate_synthetic_events(user_id, user_email)
        
        # Get aggregated stats
        stats = GitActivityRepository.get_user_stats(user_id)
        
        self.logger.info(f"✅ Saved {events_saved} git events for {user_email}")
        
        return {
            "user_email": user_email,
            "user_id": str(user_id),
            "events_saved": events_saved,
            "stats": stats,
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _handle_webhook(self, payload: dict) -> dict:
        """Handle GitHub webhook for real-time updates."""
        event_type = payload.get('action', 'push')
        
        # Extract user email from webhook (simplified logic)
        user_email = None
        if 'pusher' in payload:
            user_email = payload['pusher'].get('email')
        elif 'sender' in payload:
            user_email = payload['sender'].get('email')
        
        if not user_email:
             return {"error": "Could not extract user email from webhook"}
        
        user = UserRepository.get_by_email(user_email)
        if not user:
            self.logger.warning(f"Unknown user from webhook: {user_email}")
            return {"status": "ignored", "reason": "unknown user"}
        
        # Detect force push
        if payload.get('forced', False):
            GitActivityRepository.insert(
                user_id=user['user_id'],
                event_type='force_push',
                repository=payload.get('repository', {}).get('full_name'),
                branch=payload.get('ref', '').replace('refs/heads/', ''),
                raw_data=payload
            )
            self.logger.warning(f"⚠️ Force push detected from {user_email}")
        
        return {"status": "processed", "event_type": event_type}
    
    def _get_user_stats(self, user_id: str) -> dict:
        """Get stats directly from database."""
        return GitActivityRepository.get_user_stats(user_id)
    
    def _generate_synthetic_events(self, user_id: str, email: str) -> int:
        """
        IEEE PAPER SIMULATION:
        Generates 'risky' metadata tailored to the user's tech stack.
        """
        # Fetch user profile to customize the risk
        from src.base.database import Database
        user_stack = []
        with Database.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tech_stack, job_profile FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    user_stack = row[0] # JSONB list
        
        events_saved = 0
        is_python = "python" in user_stack
        
        # Scenario 1: Python - Secrets in Code
        if "python" in user_stack:
            try:
                GitActivityRepository.insert(
                    user_id=user_id,
                    event_type='secret_detected',
                    repository=f"{self.github_org}/ml-pipeline",
                    secret_type="gcp_service_account_key",
                    event_timestamp=datetime.utcnow(),
                    raw_data={"simulated": True, "file": "notebooks/config.py", "language": "python"}
                )
                events_saved += 1
            except Exception as e:
                self.logger.error(f"Failed to generate python risk: {e}")

        # Scenario 2: Frontend (JS/React) - Vulnerable Dependencies
        if "javascript" in user_stack or "react" in user_stack:
            try:
                GitActivityRepository.insert(
                    user_id=user_id,
                    event_type='vulnerability_detected',
                    repository=f"{self.github_org}/customer-portal",
                    branch="feature/login-ui",
                    commit_sha="js12345",
                    event_timestamp=datetime.utcnow(),
                    raw_data={
                        "simulated": True, 
                        "vuln_id": "CVE-2023-1234", 
                        "package": "lodash", 
                        "severity": "HIGH",
                        "description": "Prototype Pollution in npm package"
                    }
                )
                events_saved += 1
            except Exception as e:
                self.logger.error(f"Failed to generate frontend risk: {e}")

        # Scenario 3: Backend (Java) - Log Injection Pattern
        if "java" in user_stack:
            try:
                GitActivityRepository.insert(
                    user_id=user_id,
                    event_type='code_quality_issue',
                    repository=f"{self.github_org}/payment-service",
                    branch="hotfix/logging",
                    commit_sha="java987",
                    event_timestamp=datetime.utcnow(),
                    raw_data={
                        "simulated": True, 
                        "issue_type": "Log Injection",
                        "snippet": "logger.info(\"User input: \" + userInput);",
                        "recommendation": "Sanitize user input before logging"
                    }
                )
                events_saved += 1
            except Exception as e:
                self.logger.error(f"Failed to generate java risk: {e}")

        # Scenario 4: DevOps (Terraform) - Open Security Groups
        if "terraform" in user_stack:
            try:
                GitActivityRepository.insert(
                    user_id=user_id,
                    event_type='iac_misconfiguration',
                    repository=f"{self.github_org}/infra-live",
                    branch="main",
                    commit_sha="tf45678",
                    event_timestamp=datetime.utcnow(),
                    raw_data={
                        "simulated": True, 
                        "resource": "aws_security_group", 
                        "risk": "Open to 0.0.0.0/0 on port 22",
                        "file": "modules/vpc/main.tf"
                    }
                )
                events_saved += 1
            except Exception as e:
                self.logger.error(f"Failed to generate terraform risk: {e}")
            
        return events_saved


if __name__ == '__main__':
    GitCollector().run()
