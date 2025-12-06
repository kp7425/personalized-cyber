"""
Database utilities - shared by all collectors and services.
Uses connection pooling for efficiency.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List, Dict
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, execute_values, Json

logger = logging.getLogger(__name__)

class Database:
    """
    PostgreSQL database handler with connection pooling.
    Thread-safe for use in multi-threaded SPIFFE agents.
    """
    
    _pool: pool.ThreadedConnectionPool = None
    
    @classmethod
    def init_pool(cls, min_conn=2, max_conn=10):
        """Initialize connection pool. Call once at startup."""
        if cls._pool is None:
            try:
                cls._pool = pool.ThreadedConnectionPool(
                    min_conn, max_conn,
                    host=os.getenv('DB_HOST', 'localhost'),
                    port=os.getenv('DB_PORT', '5432'),
                    dbname=os.getenv('DB_NAME', 'security_training'),
                    user=os.getenv('DB_USER', 'postgres'),
                    password=os.getenv('DB_PASSWORD', 'postgres')
                )
                logger.info(f"✅ Database pool initialized ({min_conn}-{max_conn} connections)")
            except Exception as e:
                logger.error(f"Failed to init DB pool: {e}")
                # Don't crash immediately, allow retry?
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a connection from the pool (context manager)."""
        if cls._pool is None:
            cls.init_pool()
        
        conn = cls._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cls._pool.putconn(conn)
    
    @classmethod
    def execute(cls, query: str, params: tuple = None) -> None:
        """Execute a query (INSERT, UPDATE, DELETE)."""
        with cls.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
    
    @classmethod
    def fetch_one(cls, query: str, params: tuple = None) -> Optional[Dict]:
        """Fetch a single row as dict."""
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchone()
    
    @classmethod
    def fetch_all(cls, query: str, params: tuple = None) -> List[Dict]:
        """Fetch all rows as list of dicts."""
        with cls.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
    
    @classmethod
    def insert_many(cls, table: str, columns: List[str], values: List[tuple]) -> int:
        """Bulk insert rows efficiently."""
        with cls.get_connection() as conn:
            with conn.cursor() as cur:
                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
                execute_values(cur, query, values)
                return cur.rowcount


# =============================================================================
# REPOSITORY CLASSES - One per table/entity
# =============================================================================

class UserRepository:
    """Database operations for users table."""
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM users WHERE email = %s", (email,)
        )
    
    @staticmethod
    def get_by_workday_id(workday_id: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM users WHERE workday_id = %s", (workday_id,)
        )
    
    @staticmethod
    def upsert(workday_id: str, email: str, full_name: str, 
               department: str, job_title: str) -> Dict:
        """Insert or update user."""
        return Database.fetch_one("""
            INSERT INTO users (workday_id, email, full_name, department, job_title, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (workday_id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                department = EXCLUDED.department,
                job_title = EXCLUDED.job_title,
                updated_at = NOW()
            RETURNING *
        """, (workday_id, email, full_name, department, job_title))


class GitActivityRepository:
    """Database operations for git_activity table."""
    
    @staticmethod
    def insert(user_id: str, event_type: str, repository: str,
               branch: str = None, commit_sha: str = None,
               secret_type: str = None, event_timestamp: datetime = None,
               raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO git_activity 
            (user_id, event_type, repository, branch, commit_sha, 
             secret_type, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, event_type, repository, branch, commit_sha,
              secret_type, event_timestamp or datetime.utcnow(),
              Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        """Get aggregated stats for a user."""
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE event_type = 'commit') as commits,
                COUNT(*) FILTER (WHERE event_type = 'force_push') as force_pushes,
                COUNT(*) FILTER (WHERE event_type = 'secret_detected') as secrets_detected
            FROM git_activity
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))
    
    @staticmethod
    def bulk_insert(events: List[Dict]) -> int:
        """Bulk insert git events."""
        columns = ['user_id', 'event_type', 'repository', 'branch', 
                   'commit_sha', 'event_timestamp']
        values = [
            (e['user_id'], e['event_type'], e['repository'], 
             e.get('branch'), e.get('commit_sha'), e.get('event_timestamp'))
            for e in events
        ]
        return Database.insert_many('git_activity', columns, values)


class JiraActivityRepository:
    """Database operations for jira_activity table."""
    
    @staticmethod
    def insert(user_id: str, event_type: str, ticket_key: str,
               ticket_type: str, priority: str, status: str,
               due_date: datetime = None, raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO jira_activity 
            (user_id, event_type, ticket_key, ticket_type, priority, 
             status, due_date, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (user_id, event_type, ticket_key, ticket_type, priority,
              status, due_date,
              Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE ticket_type = 'security_vulnerability') as security_tickets,
                COUNT(*) FILTER (WHERE status != 'Done' AND due_date < NOW()) as overdue_tasks
            FROM jira_activity
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class IAMEventsRepository:
    """Database operations for iam_events table."""
    
    @staticmethod
    def insert(user_id: str, cloud_provider: str, event_type: str,
               resource_arn: str = None, action: str = None,
               is_privileged: bool = False, source_ip: str = None,
               raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO iam_events 
            (user_id, cloud_provider, event_type, resource_arn, action,
             is_privileged, event_timestamp, source_ip, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        """, (user_id, cloud_provider, event_type, resource_arn, action,
              is_privileged, source_ip,
              Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE is_privileged = true) as privileged_events,
                COUNT(*) FILTER (WHERE event_type = 'AssumeRole') as role_assumptions,
                COUNT(DISTINCT cloud_provider) as cloud_providers_used
            FROM iam_events
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class SIEMAlertRepository:
    """Database operations for siem_alerts table."""
    
    @staticmethod
    def insert(user_id: str, alert_type: str, severity: str,
               source_system: str, alert_name: str,
               description: str = None, raw_data: dict = None) -> None:
        Database.execute("""
            INSERT INTO siem_alerts 
            (user_id, alert_type, severity, source_system, alert_name,
             description, event_timestamp, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (user_id, alert_type, severity, source_system, alert_name,
              description,
              Json(raw_data) if raw_data else None))
    
    @staticmethod
    def get_user_stats(user_id: str, days: int = 30) -> Dict:
        return Database.fetch_one("""
            SELECT 
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE alert_type = 'phishing') as phishing_clicks,
                COUNT(*) FILTER (WHERE alert_type = 'malware') as malware_detections,
                COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as high_severity
            FROM siem_alerts
            WHERE user_id = %s 
            AND event_timestamp > NOW() - INTERVAL '%s days'
        """, (user_id, days))


class RiskProfileRepository:
    """Database operations for user_risk_profiles table."""
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[Dict]:
        return Database.fetch_one(
            "SELECT * FROM user_risk_profiles WHERE user_id = %s", (user_id,)
        )
    
    @staticmethod
    def upsert(user_id: str, metrics: Dict) -> Dict:
        """Update or create risk profile with new metrics."""
        return Database.fetch_one("""
            INSERT INTO user_risk_profiles (user_id, 
                secrets_committed_count, force_pushes_count, commits_without_review,
                security_tickets_created, overdue_security_tasks,
                privilege_escalation_events, mfa_disabled_services,
                security_alerts_triggered, phishing_clicks, malware_detections,
                git_risk_score, iam_risk_score, security_incident_score,
                training_gap_score, overall_risk_score,
                last_calculated_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                secrets_committed_count = EXCLUDED.secrets_committed_count,
                force_pushes_count = EXCLUDED.force_pushes_count,
                commits_without_review = EXCLUDED.commits_without_review,
                security_tickets_created = EXCLUDED.security_tickets_created,
                overdue_security_tasks = EXCLUDED.overdue_security_tasks,
                privilege_escalation_events = EXCLUDED.privilege_escalation_events,
                mfa_disabled_services = EXCLUDED.mfa_disabled_services,
                security_alerts_triggered = EXCLUDED.security_alerts_triggered,
                phishing_clicks = EXCLUDED.phishing_clicks,
                malware_detections = EXCLUDED.malware_detections,
                git_risk_score = EXCLUDED.git_risk_score,
                iam_risk_score = EXCLUDED.iam_risk_score,
                security_incident_score = EXCLUDED.security_incident_score,
                training_gap_score = EXCLUDED.training_gap_score,
                overall_risk_score = EXCLUDED.overall_risk_score,
                last_calculated_at = NOW(),
                updated_at = NOW()
            RETURNING *
        """, (user_id,
              metrics.get('secrets_committed_count', 0),
              metrics.get('force_pushes_count', 0),
              metrics.get('commits_without_review', 0),
              metrics.get('security_tickets_created', 0),
              metrics.get('overdue_security_tasks', 0),
              metrics.get('privilege_escalation_events', 0),
              metrics.get('mfa_disabled_services', 0),
              metrics.get('security_alerts_triggered', 0),
              metrics.get('phishing_clicks', 0),
              metrics.get('malware_detections', 0),
              metrics.get('git_risk_score', 0.0),
              metrics.get('iam_risk_score', 0.0),
              metrics.get('security_incident_score', 0.0),
              metrics.get('training_gap_score', 0.0),
              metrics.get('overall_risk_score', 0.0)))
    
    @staticmethod
    def get_high_risk_users(threshold: float = 0.7) -> List[Dict]:
        """Get all users above risk threshold."""
        return Database.fetch_all("""
            SELECT urp.*, u.email, u.full_name, u.department
            FROM user_risk_profiles urp
            JOIN users u ON urp.user_id = u.user_id
            WHERE urp.overall_risk_score >= %s
            ORDER BY urp.overall_risk_score DESC
        """, (threshold,))
    
    @staticmethod
    def save_history(user_id: str, scores: Dict) -> None:
        """Save score snapshot for trending."""
        Database.execute("""
            INSERT INTO risk_scores_history 
            (user_id, overall_risk_score, git_risk_score, iam_risk_score,
             security_incident_score, training_gap_score, calculated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (user_id, scores['overall_risk_score'], scores['git_risk_score'],
              scores['iam_risk_score'], scores['security_incident_score'],
              scores['training_gap_score']))
