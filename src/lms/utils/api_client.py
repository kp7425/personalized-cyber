"""
API Client - Handles mTLS communication with backend services.
"""

import os
import requests
import streamlit as st
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
    def _get_service_url(service_name):
        # Map service names to K8s DNS or local ports
        # For local dev (docker-compose or similar), we might mapping ports
        # But here assuming K8s DNS or local ports matching what we set in code
        
        # Local dev port mapping
        ports = {
            "risk-scorer": 8510,
            "training-recommender": 8511,
            "llm-gateway": 8520,
            "git-collector": 8501
        }
        
        host = os.getenv('SERVICE_HOST', 'localhost')
        port = ports.get(service_name, 80)
        return f"https://{host}:{port}" # HTTPS for mTLS

    @classmethod
    def post(cls, service, path, data, timeout=10):
        handler = cls.get_mtls_handler()
        url = f"{cls._get_service_url(service)}{path}"
        
        if handler and handler.cert_file:
            return handler.make_mtls_request(url, data, timeout=timeout)
        else:
            # Fallback for dev mode without mTLS certificates
            # Note: Services will reject this if they enforce mTLS check
            return requests.post(url.replace("https", "http"), json=data, timeout=timeout)
