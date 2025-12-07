"""
API Client - Handles mTLS communication with backend services.
"""

import os
import requests
from src.base.spiffe_agent import SPIFFEMTLSHandler

class APIClient:
    
    _mtls_handler = None
    
    @classmethod
    def get_mtls_handler(cls):
        if cls._mtls_handler is None:
            try:
                cls._mtls_handler = SPIFFEMTLSHandler()
            except Exception as e:
                print(f"Warning: SPIFFE init failed: {e}")
                return None
        return cls._mtls_handler

    @staticmethod
    def _get_service_url(service_name, use_https=True):
        """Get service URL - uses K8s DNS in cluster, localhost for dev."""
        
        # Service port mapping
        ports = {
            "risk-scorer": 8510,
            "training-recommender": 8511,
            "llm-gateway": 8520,
            "git-collector": 8501
        }
        
        # In K8s, use service DNS names; otherwise localhost
        in_k8s = os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount')
        
        if in_k8s:
            namespace = os.getenv('K8S_NAMESPACE', 'security-training')
            host = f"{service_name}-svc.{namespace}.svc.cluster.local"
        else:
            host = os.getenv('SERVICE_HOST', 'localhost')
        
        port = ports.get(service_name, 80)
        protocol = "https" if use_https else "http"
        return f"{protocol}://{host}:{port}"

    @classmethod
    def post(cls, service, path, data, timeout=30):
        handler = cls.get_mtls_handler()
        
        if handler and handler.cert_file:
            # Use HTTPS + mTLS
            url = f"{cls._get_service_url(service, use_https=True)}{path}"
            try:
                return handler.make_mtls_request(url, data, timeout=timeout)
            except Exception as e:
                print(f"mTLS request failed: {e}")
                return None
        else:
            # Fallback HTTP (only works if service allows)
            url = f"{cls._get_service_url(service, use_https=False)}{path}"
            return requests.post(url, json=data, timeout=timeout)

