"""SIEM Collector - Splunk/Sentinel/CrowdStrike Logic"""

import os
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import Database, SIEMAlertRepository


class SIEMCollector(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="siem-collector",
            port=8504,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/risk-scorer"
            ]
        )
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/collect':
            # SIMULATION:
            user_email = data.get('user_email')
            if not user_email: return {"error": "Missing user_email"}
            
            from src.base.database import UserRepository
            user = UserRepository.get_by_email(user_email)
            if not user: return {"error": "User not found"}
            
            # Simulate: Phishing Click
            SIEMAlertRepository.insert(
                user_id=user['user_id'],
                alert_type="phishing",
                severity="high",
                source_system="crowdstrike",
                alert_name="Malicious Link Clicked",
                description="User clicked on known phishing domain via email.",
                raw_data={"simulated": True}
            )
            return {"status": "siem_simulation_complete", "events_generated": 1}
        elif path == '/stats':
            return self._get_user_stats(data.get('user_id'))
        return {"error": "Unknown path"}
    
    def _get_user_stats(self, user_id: str) -> dict:
        return SIEMAlertRepository.get_user_stats(user_id)


if __name__ == '__main__':
    SIEMCollector().run()
