"""
Training Recommender - Recommends modules based on risk profile.
"""

import os
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import Database, RiskProfileRepository


class TrainingRecommender(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="training-recommender",
            port=8511,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/lms-api"
            ]
        )
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/recommend':
            return self._recommend_training(data.get('user_id'))
        return {"error": "Unknown path"}
    
    def _recommend_training(self, user_id: str) -> dict:
        profile = RiskProfileRepository.get_by_user_id(user_id)
        if not profile:
            return {"error": "User profile not found, populate risk score first"}
        
        modules = []
        
        # Simple rule-based recommendation for now
        if profile['git_risk_score'] > 0.3:
            modules.append("Secure Coding Fundamentals")
            modules.append("Managing Secrets in Git")
            
        if profile['iam_risk_score'] > 0.3:
            modules.append("Cloud Identity Best Practices")
            
        if profile['security_incident_score'] > 0.2:
            modules.append("Phishing Awareness 101")
        
        return {
            "user_id": user_id,
            "recommended_modules": modules,
            "risk_summary": {
                "overall": float(profile['overall_risk_score']),
                "git": float(profile['git_risk_score'])
            }
        }


if __name__ == '__main__':
    TrainingRecommender().run()
