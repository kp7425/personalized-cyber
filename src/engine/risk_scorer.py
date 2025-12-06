"""
Risk Scoring Engine - Aggregates data from all collectors,
calculates risk scores, and saves to database.
"""

import os
from datetime import datetime
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import (
    Database, RiskProfileRepository,
    GitActivityRepository, JiraActivityRepository,
    IAMEventsRepository, SIEMAlertRepository
)


class RiskScorer(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="risk-scorer",
            port=8510,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/lms-api",
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/training-recommender"
            ]
        )
        Database.init_pool()
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/score':
            return self._calculate_risk_score(data.get('user_id'))
        elif path == '/score-all':
            return self._calculate_all_scores()
        elif path == '/high-risk':
            threshold = data.get('threshold', 0.7)
            return self._get_high_risk_users(threshold)
        return {"error": f"Unknown path: {path}"}
    
    def _calculate_risk_score(self, user_id: str) -> dict:
        """Calculate and save risk score for a single user."""
        
        # Get stats from all data sources
        git_stats = GitActivityRepository.get_user_stats(user_id) or {}
        jira_stats = JiraActivityRepository.get_user_stats(user_id) or {}
        iam_stats = IAMEventsRepository.get_user_stats(user_id) or {}
        siem_stats = SIEMAlertRepository.get_user_stats(user_id) or {}
        
        # Calculate individual risk scores (0.0 - 1.0)
        # Weights are defined in NEW_PROJECT_CONTEXT.md
        git_risk = min(1.0, (
            (git_stats.get('secrets_detected', 0) or 0) * 0.3 +
            (git_stats.get('force_pushes', 0) or 0) * 0.1
        ))
        
        iam_risk = min(1.0, (
            (iam_stats.get('privileged_events', 0) or 0) * 0.15
        ))
        
        incident_risk = min(1.0, (
            (siem_stats.get('phishing_clicks', 0) or 0) * 0.2 +
            (siem_stats.get('malware_detections', 0) or 0) * 0.3
        ))
        
        training_gap = min(1.0, (
            (jira_stats.get('overdue_tasks', 0) or 0) * 0.1
        ))
        
        # Weighted overall score
        overall_risk = (
            git_risk * 0.25 +
            iam_risk * 0.30 +
            incident_risk * 0.30 +
            training_gap * 0.15
        )
        
        # Build metrics dict
        metrics = {
            'secrets_committed_count': git_stats.get('secrets_detected', 0) or 0,
            'force_pushes_count': git_stats.get('force_pushes', 0) or 0,
            'security_tickets_created': jira_stats.get('security_tickets', 0) or 0,
            'overdue_security_tasks': jira_stats.get('overdue_tasks', 0) or 0,
            'privilege_escalation_events': iam_stats.get('privileged_events', 0) or 0,
            'security_alerts_triggered': siem_stats.get('total_alerts', 0) or 0,
            'phishing_clicks': siem_stats.get('phishing_clicks', 0) or 0,
            'malware_detections': siem_stats.get('malware_detections', 0) or 0,
            'git_risk_score': round(git_risk, 2),
            'iam_risk_score': round(iam_risk, 2),
            'security_incident_score': round(incident_risk, 2),
            'training_gap_score': round(training_gap, 2),
            'overall_risk_score': round(overall_risk, 2)
        }
        
        # Save to database
        RiskProfileRepository.upsert(user_id, metrics)
        
        # Save history for trending
        RiskProfileRepository.save_history(user_id, metrics)
        
        self.logger.info(f"✅ Risk score calculated for {user_id}: {overall_risk:.2f}")
        
        return {
            "user_id": user_id,
            "scores": metrics,
            "risk_level": self._get_risk_level(overall_risk),
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_all_scores(self) -> dict:
        """Recalculate scores for all users (batch job)."""
        users = Database.fetch_all("SELECT user_id FROM users")
        
        results = {"processed": 0, "errors": 0}
        for user in users:
            try:
                self._calculate_risk_score(str(user['user_id']))
                results["processed"] += 1
            except Exception as e:
                self.logger.error(f"Error scoring {user['user_id']}: {e}")
                results["errors"] += 1
        
        return results
    
    def _get_high_risk_users(self, threshold: float) -> dict:
        """Get all users above risk threshold."""
        users = RiskProfileRepository.get_high_risk_users(threshold)
        return {
            "threshold": threshold,
            "count": len(users),
            "users": users
        }
    
    def _get_risk_level(self, score: float) -> str:
        if score >= 0.7: return "CRITICAL"
        if score >= 0.5: return "HIGH"
        if score >= 0.2: return "MEDIUM"
        return "LOW"


if __name__ == '__main__':
    RiskScorer().run()
