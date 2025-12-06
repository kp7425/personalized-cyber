"""IAM Collector - Unified Cloud IAM Logic"""

import os
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import Database, IAMEventsRepository


class IAMCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="iam-collector",
            port=8503,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/risk-scorer"
            ]
        )
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            # IAM usually pushes logs or we poll APIs
            # SIMULATION:
            user_email = data.get('user_email')
            if not user_email: return {"error": "Missing user_email"}
            
            from src.base.database import Database
            # Fetch user profile using direct SQL for now
            tech_stack = []
            user_id = None
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id, tech_stack FROM users WHERE email = %s", (user_email,))
                    row = cur.fetchone()
                    if row:
                        user_id = row[0]
                        tech_stack = row[1]
            
            if not user_id: return {"error": "User not found"}
            
            events_gen = 0
            
            # Scenario: Cloud Specific Risk
            if "gcp" in tech_stack:
                # GCP BigQuery Owner excessive privilege
                IAMEventsRepository.insert(
                    user_id=user_id,
                    cloud_provider="gcp",
                    event_type="RoleAssignment",
                    resource_arn="projects/my-proj/roles/bigquery.admin",
                    action="iam.roles.grant",
                    is_privileged=True,
                    source_ip="1.2.3.4",
                    raw_data={"simulated": True, "risk": "Over-privileged Service Account"}
                )
                events_gen += 1
            
            if "aws" in tech_stack:
                 # AWS Admin Access
                IAMEventsRepository.insert(
                    user_id=user_id,
                    cloud_provider="aws",
                    event_type="AssumeRole",
                    resource_arn="arn:aws:iam::123:role/Administrator",
                    action="sts:AssumeRole",
                    is_privileged=True,
                    source_ip="1.2.3.4",
                    raw_data={"simulated": True, "risk": "Admin Access without Ticket"}
                )
                events_gen += 1
            
            if "azure" in tech_stack:
                # Azure AD Global Admin usage
                IAMEventsRepository.insert(
                    user_id=user_id,
                    cloud_provider="azure",
                    event_type="SignIn",
                    resource_arn="mypaas-app-registration",
                    action="User.ReadWrite.All",
                    is_privileged=True,
                    source_ip="1.2.3.4",
                    raw_data={"simulated": True, "risk": "Global Admin usage on non-compliant device"}
                )
                events_gen += 1
                
            return {"status": "iam_simulation_complete", "events_generated": events_gen}
        elif path == '/stats':
            return self._get_user_stats(data.get('user_id'))
        return {"error": "Unknown path"}
    
    def _get_user_stats(self, user_id: str) -> dict:
        return IAMEventsRepository.get_user_stats(user_id)


if __name__ == '__main__':
    IAMCollector().run()
