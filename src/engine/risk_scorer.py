"""
Risk Scoring Engine - Extensible Formula Implementation

Formula: R_overall(u, t) = Σᵢ wᵢ(role) × Rᵢ(u, t)

Where:
  u = employee (workday_id)
  t = time window (default: 30 days)
  i = data source index (Git, IAM, SIEM, Jira, Training, ...)
  wᵢ(role) = weight for source i, dependent on employee role
  Rᵢ(u, t) = normalized risk score [0,1] from source i
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from src.base.spiffe_agent import BaseSPIFFEAgent
from src.base.database import (
    Database, RiskProfileRepository,
    GitActivityRepository, JiraActivityRepository,
    IAMEventsRepository, SIEMAlertRepository
)


# ============================================================================
# ROLE-BASED WEIGHT CONFIGURATION (Extensible)
# ============================================================================
# Each role has different weights for each data source
# Weights should sum to 1.0 for normalized scoring

ROLE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "backend_developer": {
        "git": 0.35,
        "iam": 0.25,
        "siem": 0.20,
        "training": 0.20
    },
    "frontend_developer": {
        "git": 0.30,
        "iam": 0.20,
        "siem": 0.25,
        "training": 0.25
    },
    "devops_engineer": {
        "git": 0.25,
        "iam": 0.40,
        "siem": 0.15,
        "training": 0.20
    },
    "data_engineer": {
        "git": 0.20,
        "iam": 0.45,
        "siem": 0.15,
        "training": 0.20
    },
    "data_analyst": {
        "git": 0.15,
        "iam": 0.35,
        "siem": 0.20,
        "training": 0.30
    },
    "sre": {
        "git": 0.20,
        "iam": 0.40,
        "siem": 0.20,
        "training": 0.20
    },
    "devsecops_engineer": {
        "git": 0.25,
        "iam": 0.30,
        "siem": 0.25,
        "training": 0.20
    },
    "cloud_security_analyst": {
        "git": 0.20,
        "iam": 0.30,
        "siem": 0.30,
        "training": 0.20
    },
    # Default weights for unknown roles
    "default": {
        "git": 0.25,
        "iam": 0.30,
        "siem": 0.25,
        "training": 0.20
    }
}

# ============================================================================
# EVENT TYPE SEVERITY WEIGHTS (Per Source)
# ============================================================================
# αⱼ = severity weight for each event type j within source s

EVENT_SEVERITY: Dict[str, Dict[str, float]] = {
    "git": {
        "secrets_committed": 0.30,
        "force_push": 0.10,
        "commits_without_review": 0.05,
        "vulnerable_deps": 0.15,
        "large_file_addition": 0.05
    },
    "iam": {
        "privilege_escalation": 0.25,
        "service_account_key_creation": 0.20,
        "off_hours_access": 0.15,
        "unused_permissions": 0.10,
        "cross_account_access": 0.15
    },
    "siem": {
        "malware_detection": 0.30,
        "phishing_click": 0.20,
        "failed_auth_attempts": 0.10,
        "policy_violation": 0.10,
        "data_exfiltration_alert": 0.25
    },
    "training": {
        "overdue_modules": 0.20,
        "days_since_training": 0.30,  # > 180 days = 1.0
        "failed_assessments": 0.15
    }
}

# ============================================================================
# CROSS-SYSTEM CORRELATION MULTIPLIERS
# ============================================================================
# Patterns that indicate higher risk when events correlate across systems

CORRELATION_PATTERNS = {
    "insider_threat": {
        "conditions": ["off_hours_iam", "large_data_export", "no_jira_ticket"],
        "multiplier": 1.5
    },
    "compromised_account": {
        "conditions": ["no_git_activity", "high_iam_activity", "siem_alerts_gt_3"],
        "multiplier": 2.0
    },
    "burnout_pattern": {
        "conditions": ["force_pushes_gt_3", "overdue_tickets_gt_5", "weekend_activity"],
        "multiplier": 1.2
    }
}


class RiskScorer(BaseSPIFFEAgent):
    """
    Extensible Risk Scoring Engine.
    
    Implements: R_overall(u, t) = Σᵢ wᵢ(role) × Rᵢ(u, t)
    """
    
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
        
        # Registered data sources (extensible)
        self.sources = ['git', 'iam', 'siem', 'training']
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/score':
            return self._calculate_risk_score(data.get('user_id'))
        elif path == '/score-all':
            return self._calculate_all_scores()
        elif path == '/high-risk':
            threshold = data.get('threshold', 0.7)
            return self._get_high_risk_users(threshold)
        elif path == '/add-source':
            # Future: dynamically add new data sources
            return self._add_source(data.get('source_name'), data.get('weight'))
        return {"error": f"Unknown path: {path}"}
    
    def _calculate_risk_score(self, user_id: str) -> dict:
        """
        Calculate risk score using extensible formula.
        
        R_overall(u, t) = Σᵢ wᵢ(role) × Rᵢ(u, t)
        """
        # Get user's role for weight selection
        role = self._get_user_role(user_id)
        weights = ROLE_WEIGHTS.get(role, ROLE_WEIGHTS["default"])
        
        # Get raw stats from all data sources
        source_stats = {
            "git": GitActivityRepository.get_user_stats(user_id) or {},
            "iam": IAMEventsRepository.get_user_stats(user_id) or {},
            "siem": SIEMAlertRepository.get_user_stats(user_id) or {},
            "training": JiraActivityRepository.get_user_stats(user_id) or {}  # Jira used for training gaps
        }
        
        # Calculate normalized score for each source: Rᵢ(u, t)
        source_scores = {}
        for source in self.sources:
            source_scores[source] = self._calculate_source_score(
                source, 
                source_stats.get(source, {}),
                user_id
            )
        
        # Weighted sum: R_overall = Σᵢ wᵢ × Rᵢ
        R_overall = sum(
            weights.get(source, 0) * source_scores.get(source, 0)
            for source in self.sources
        )
        
        # Apply correlation multiplier
        correlation_multiplier = self._detect_correlation_patterns(source_stats)
        R_overall = min(1.0, R_overall * correlation_multiplier)
        
        # Build metrics dict for storage
        metrics = self._build_metrics(source_stats, source_scores, R_overall)
        
        # Save to database
        RiskProfileRepository.upsert(user_id, metrics)
        RiskProfileRepository.save_history(user_id, metrics)
        
        self.logger.info(f"✅ Risk score for {user_id} (role={role}): {R_overall:.2f}")
        
        return {
            "user_id": user_id,
            "role": role,
            "scores": metrics,
            "source_scores": source_scores,
            "weights_applied": weights,
            "correlation_multiplier": correlation_multiplier,
            "risk_level": self._get_risk_level(R_overall),
            "training_frequency": self._get_training_frequency(R_overall),
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_source_score(self, source: str, stats: dict, user_id: str = None) -> float:
        """
        Calculate normalized score for a single source.
        
        Uses threshold-based normalization:
        Rₛ(u,t) = Σⱼ (αⱼ × min(1.0, count(eventⱼ) / threshold(eventⱼ)))
        
        This ensures scores are properly normalized to [0,1] based on
        expected event counts, not raw counts.
        """
        if source == "training":
            # Training score comes from training_completions table
            return self._calculate_training_score(user_id, stats)
        
        # Thresholds for normalization - events above threshold = 1.0
        THRESHOLDS = {
            "git": {
                "secrets_committed": 3,      # 3+ secrets = 1.0
                "force_push": 5,             # 5+ force pushes = 1.0
                "commits_without_review": 10,
                "vulnerable_deps": 5,
                "large_file_addition": 10
            },
            "iam": {
                "privilege_escalation": 10,   # 10+ priv events = 1.0
                "service_account_key_creation": 5,
                "off_hours_access": 10,
                "unused_permissions": 20,
                "cross_account_access": 5
            },
            "siem": {
                "malware_detection": 2,       # 2+ malware = 1.0
                "phishing_click": 3,
                "failed_auth_attempts": 20,
                "policy_violation": 5,
                "data_exfiltration_alert": 1
            }
        }
        
        severity_weights = EVENT_SEVERITY.get(source, {})
        thresholds = THRESHOLDS.get(source, {})
        
        score = 0.0
        for event_type, weight in severity_weights.items():
            count = self._get_event_count(source, event_type, stats)
            threshold = thresholds.get(event_type, 5)  # default threshold
            
            # Normalize: count/threshold, capped at 1.0
            normalized_count = min(1.0, count / threshold) if threshold > 0 else 0
            score += weight * normalized_count
        
        return min(1.0, score)
    
    def _calculate_training_score(self, user_id: str, jira_stats: dict) -> float:
        """
        Calculate training gap score from training_completions table.
        
        Low score = good training compliance
        High score = incomplete or outdated training
        """
        try:
            if not user_id:
                return 0.5  # Default middle score
                
            # Get actual training data from training_completions
            training_data = Database.fetch_one("""
                SELECT 
                    COUNT(*) as total_modules,
                    COUNT(*) FILTER (WHERE passed = true) as passed_modules,
                    MAX(completed_at) as last_training,
                    AVG(score) as avg_score
                FROM training_completions
                WHERE user_id = %s
                AND completed_at > NOW() - INTERVAL '180 days'
            """, (user_id,))
            
            if not training_data or training_data.get('total_modules', 0) == 0:
                # No training in 180 days = high risk
                return 0.8
            
            total = training_data.get('total_modules', 0)
            passed = training_data.get('passed_modules', 0)
            avg_score = float(training_data.get('avg_score', 0) or 0)
            
            # Calculate training score (lower = better)
            if total >= 8 and passed >= 7 and avg_score >= 80:
                return 0.05  # Very well trained (DevSecOps, Security Analysts)
            elif total >= 5 and passed >= 4:
                return 0.2  # Well trained
            elif total >= 3:
                return 0.4  # Some training
            else:
                return 0.7  # Needs training
                
        except Exception:
            # Fall back to Jira-based training gap
            overdue = jira_stats.get('overdue_tasks', 0) or 0
            return min(1.0, overdue * 0.1)
    
    def _get_event_count(self, source: str, event_type: str, stats: dict) -> int:
        """Map event types to actual stats fields."""
        # Mapping from canonical event types to stats keys
        mappings = {
            "git": {
                "secrets_committed": stats.get("secrets_detected", 0) or 0,
                "force_push": stats.get("force_pushes", 0) or 0,
                "commits_without_review": stats.get("unreviewed_commits", 0) or 0,
                "vulnerable_deps": stats.get("vulnerable_deps", 0) or 0,
                "large_file_addition": stats.get("large_files", 0) or 0
            },
            "iam": {
                "privilege_escalation": stats.get("privileged_events", 0) or 0,
                "service_account_key_creation": stats.get("sa_key_creations", 0) or 0,
                "off_hours_access": stats.get("off_hours_events", 0) or 0,
                "unused_permissions": stats.get("unused_permissions", 0) or 0,
                "cross_account_access": stats.get("cross_account", 0) or 0
            },
            "siem": {
                "malware_detection": stats.get("malware_detections", 0) or 0,
                "phishing_click": stats.get("phishing_clicks", 0) or 0,
                "failed_auth_attempts": stats.get("failed_auth", 0) or 0,
                "policy_violation": stats.get("policy_violations", 0) or 0,
                "data_exfiltration_alert": stats.get("exfil_alerts", 0) or 0
            },
            "training": {
                "overdue_modules": stats.get("overdue_tasks", 0) or 0,
                "days_since_training": 1 if stats.get("days_since_training", 0) > 180 else 0,
                "failed_assessments": stats.get("failed_assessments", 0) or 0
            }
        }
        
        return mappings.get(source, {}).get(event_type, 0)
    
    def _get_user_role(self, user_id: str) -> str:
        """Get user's job role from database."""
        try:
            result = Database.fetch_one(
                "SELECT job_profile FROM users WHERE user_id = %s",
                (user_id,)
            )
            if result and result.get('job_profile'):
                # Normalize: "Backend Developer" -> "backend_developer"
                return result['job_profile'].lower().replace(' ', '_')
        except Exception as e:
            self.logger.warning(f"Could not get role for {user_id}: {e}")
        return "default"
    
    def _detect_correlation_patterns(self, source_stats: dict) -> float:
        """
        Detect cross-system correlation patterns.
        Returns multiplier (1.0 = no pattern, >1.0 = suspicious correlation)
        """
        multiplier = 1.0
        
        git_stats = source_stats.get("git", {})
        iam_stats = source_stats.get("iam", {})
        siem_stats = source_stats.get("siem", {})
        
        # Insider threat pattern
        if (iam_stats.get("off_hours_events", 0) > 0 and
            iam_stats.get("large_data_exports", 0) > 0):
            multiplier = max(multiplier, 1.5)
            self.logger.warning("⚠️ Insider threat pattern detected")
        
        # Compromised account pattern
        if (git_stats.get("total_commits", 0) == 0 and
            iam_stats.get("total_events", 0) > 20 and
            siem_stats.get("total_alerts", 0) > 3):
            multiplier = max(multiplier, 2.0)
            self.logger.warning("🚨 Compromised account pattern detected")
        
        # Burnout pattern - only on extreme cases
        if (git_stats.get("force_pushes", 0) > 10 and
            source_stats.get("training", {}).get("overdue_tasks", 0) > 15):
            multiplier = max(multiplier, 1.2)
            self.logger.info("📊 Burnout pattern detected")
        
        return multiplier
    
    def _build_metrics(self, source_stats: dict, source_scores: dict, overall: float) -> dict:
        """Build metrics dictionary for database storage."""
        git_stats = source_stats.get("git", {})
        iam_stats = source_stats.get("iam", {})
        siem_stats = source_stats.get("siem", {})
        training_stats = source_stats.get("training", {})
        
        return {
            # Raw counts
            'secrets_committed_count': git_stats.get('secrets_detected', 0) or 0,
            'force_pushes_count': git_stats.get('force_pushes', 0) or 0,
            'security_tickets_created': training_stats.get('security_tickets', 0) or 0,
            'overdue_security_tasks': training_stats.get('overdue_tasks', 0) or 0,
            'privilege_escalation_events': iam_stats.get('privileged_events', 0) or 0,
            'security_alerts_triggered': siem_stats.get('total_alerts', 0) or 0,
            'phishing_clicks': siem_stats.get('phishing_clicks', 0) or 0,
            'malware_detections': siem_stats.get('malware_detections', 0) or 0,
            # Normalized scores [0-1]
            'git_risk_score': round(source_scores.get('git', 0), 2),
            'iam_risk_score': round(source_scores.get('iam', 0), 2),
            'security_incident_score': round(source_scores.get('siem', 0), 2),
            'training_gap_score': round(source_scores.get('training', 0), 2),
            'overall_risk_score': round(overall, 2)
        }
    
    def _calculate_all_scores(self) -> dict:
        """Recalculate scores for all users (batch job)."""
        users = Database.fetch_all("SELECT user_id FROM users")
        
        results = {"processed": 0, "errors": 0, "high_risk_count": 0}
        for user in users:
            try:
                result = self._calculate_risk_score(str(user['user_id']))
                results["processed"] += 1
                if result.get('risk_level') in ['CRITICAL', 'HIGH']:
                    results["high_risk_count"] += 1
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
        """Map score to risk level."""
        if score >= 0.8: return "CRITICAL"
        if score >= 0.6: return "HIGH"
        if score >= 0.3: return "MEDIUM"
        return "LOW"
    
    def _get_training_frequency(self, score: float) -> str:
        """Map score to training frequency (per IEEE paper spec)."""
        if score >= 0.8: return "IMMEDIATE"
        if score >= 0.6: return "WEEKLY"
        if score >= 0.3: return "MONTHLY"
        return "QUARTERLY"
    
    def _add_source(self, source_name: str, default_weight: float = 0.1) -> dict:
        """
        Future extensibility: Add a new data source at runtime.
        Example: Adding Slack, GitHub Copilot, EDR, etc.
        """
        if source_name and source_name not in self.sources:
            self.sources.append(source_name)
            # Add default weight to all roles
            for role in ROLE_WEIGHTS:
                if source_name not in ROLE_WEIGHTS[role]:
                    ROLE_WEIGHTS[role][source_name] = default_weight
            return {"status": "added", "source": source_name}
        return {"status": "exists_or_invalid", "source": source_name}

    def calculate_organization_risk(self) -> dict:
        """
        Calculate organization-wide security risk posture.
        
        Formula:
        R_org = α × R_mean + β × R_max + γ × (High_Risk_Count / Total_Users)
        
        Where:
        - R_mean = Average individual risk score
        - R_max = Maximum individual risk score (worst case exposure)
        - High_Risk_Count = Users with score >= 0.6
        - α, β, γ = Weights (0.4, 0.3, 0.3)
        """
        # Get all user risk profiles
        risk_profiles = Database.fetch_all("""
            SELECT 
                overall_risk_score,
                git_risk_score,
                iam_risk_score,
                security_incident_score,
                training_gap_score
            FROM user_risk_profiles
            WHERE overall_risk_score IS NOT NULL
        """)
        
        if not risk_profiles:
            return {"error": "No risk profiles found. Run risk calculation first."}
        
        scores = [float(r['overall_risk_score'] or 0) for r in risk_profiles]
        total_users = len(scores)
        
        # Calculate components
        R_mean = sum(scores) / total_users
        R_max = max(scores)
        R_min = min(scores)
        high_risk_count = len([s for s in scores if s >= 0.6])
        critical_count = len([s for s in scores if s >= 0.8])
        
        # High risk ratio
        high_risk_ratio = high_risk_count / total_users if total_users > 0 else 0
        
        # Weighted organization risk
        alpha, beta, gamma = 0.4, 0.3, 0.3
        R_org = (alpha * R_mean) + (beta * R_max) + (gamma * high_risk_ratio)
        R_org = min(1.0, R_org)
        
        # Component breakdown
        git_avg = sum(float(r['git_risk_score'] or 0) for r in risk_profiles) / total_users
        iam_avg = sum(float(r['iam_risk_score'] or 0) for r in risk_profiles) / total_users
        siem_avg = sum(float(r['security_incident_score'] or 0) for r in risk_profiles) / total_users
        training_avg = sum(float(r['training_gap_score'] or 0) for r in risk_profiles) / total_users
        
        # Determine organization risk level
        if R_org >= 0.7:
            org_risk_level = "CRITICAL"
            recommendation = "Immediate org-wide security training required"
        elif R_org >= 0.5:
            org_risk_level = "HIGH"
            recommendation = "Targeted training for high-risk departments"
        elif R_org >= 0.3:
            org_risk_level = "MEDIUM"
            recommendation = "Standard quarterly training sufficient"
        else:
            org_risk_level = "LOW"
            recommendation = "Security posture is healthy"
        
        result = {
            "organization_risk_score": round(R_org, 3),
            "risk_level": org_risk_level,
            "recommendation": recommendation,
            "total_users": total_users,
            "statistics": {
                "mean_risk": round(R_mean, 3),
                "max_risk": round(R_max, 3),
                "min_risk": round(R_min, 3),
                "high_risk_count": high_risk_count,
                "critical_count": critical_count,
                "high_risk_percentage": round(high_risk_ratio * 100, 1)
            },
            "component_averages": {
                "git": round(git_avg, 3),
                "iam": round(iam_avg, 3),
                "siem": round(siem_avg, 3),
                "training": round(training_avg, 3)
            },
            "formula": "R_org = 0.4×R_mean + 0.3×R_max + 0.3×(HighRisk/Total)",
            "calculated_at": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"🏢 Organization Risk: {R_org:.2f} ({org_risk_level})")
        return result


if __name__ == '__main__':
    RiskScorer().run()
