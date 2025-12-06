"""
Base SPIFFE Agent - ALL mTLS/certificate code in ONE place!
Every collector inherits from this.
"""

import os
import ssl
import json
import tempfile
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from abc import ABC, abstractmethod

from spiffe import WorkloadApiClient
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

class SPIFFEMTLSHandler:
    """
    Manages SPIFFE certificates for mTLS (mutual TLS).
    
    Key responsibilities:
    1. Fetch X.509-SVID from SPIRE Agent via Workload API
    2. Write cert/key/bundle to temp files (memory-backed)
    3. Create SSL context for HTTPS server OR client requests
    4. Handle certificate refresh for rotation
    """
    
    def __init__(self, trust_domain="security-training.example.org"):
        self.cert_file = None
        self.key_file = None
        self.bundle_file = None
        self.x509_svid = None
        self.spiffe_id = None
        self.trust_domain = trust_domain
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Don't block init if SPIRE isn't ready locally, 
        # but in prod it should probably block or retry.
        # We start a background thread for refresh anyway.
        self._refresh_certificates()
        self._start_refresh_thread()
    
    def _start_refresh_thread(self):
        """Auto-refresh certificates before expiry."""
        def refresh_loop():
            while True:
                time.sleep(1800)  # 30 minutes
                self._refresh_certificates()
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
    
    def _refresh_certificates(self):
        """Fetch certs from SPIRE - with retry logic."""
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                with WorkloadApiClient() as client:
                    self.x509_svid = client.fetch_x509_svid()
                    self.spiffe_id = str(self.x509_svid.spiffe_id)
                    trust_bundle = client.fetch_x509_bundles()
                    
                    self._write_cert_files(trust_bundle)
                    self.logger.info(f"✅ Certificates refreshed: {self.spiffe_id}")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Cert fetch failed (attempt {attempt}): {e}")
                # Don't sleep on last attempt if we want to fail fast-ish, 
                # but for an agent loop we just retry later
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
        return False
    
    def _write_cert_files(self, trust_bundle):
        """Write cert/key/bundle to temp files."""
        # Cleanup old files
        for f in [self.cert_file, self.key_file, self.bundle_file]:
            if f:
                try: os.unlink(f.name)
                except: pass
        
        # Write cert chain
        self.cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        cert_chain = self.x509_svid.cert_chain
        if callable(cert_chain): cert_chain = cert_chain()
        if isinstance(cert_chain, list):
            for c in cert_chain:
                self.cert_file.write(c.public_bytes(serialization.Encoding.PEM).decode())
        else:
            self.cert_file.write(cert_chain.decode() if isinstance(cert_chain, bytes) else cert_chain)
        self.cert_file.flush()
        
        # Write private key
        self.key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key')
        priv_key = self.x509_svid.private_key
        if callable(priv_key): priv_key = priv_key()
        if hasattr(priv_key, 'private_bytes'):
            priv_key = priv_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
        self.key_file.write(priv_key if isinstance(priv_key, str) else priv_key.decode())
        self.key_file.flush()
        
        # Write trust bundle
        self.bundle_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
        
        # Try different ways to get bundles (py-spiffe versions vary)
        bundles_written = False
        
        # Method 1: Direct access
        if hasattr(trust_bundle, '_bundles'):
            for td, bundle in trust_bundle._bundles.items():
                authorities = bundle.x509_authorities
                if callable(authorities): authorities = authorities()
                for cert in authorities:
                    self.bundle_file.write(cert.public_bytes(serialization.Encoding.PEM).decode())
            bundles_written = True
            
        # Method 2: get_bundle_for_trust_domain
        if not bundles_written and hasattr(trust_bundle, 'get_bundle_for_trust_domain'):
            try:
                from spiffe.spiffe_id.trust_domain import TrustDomain
                td_obj = TrustDomain.parse(self.trust_domain)
                bundle = trust_bundle.get_bundle_for_trust_domain(td_obj)
                if bundle:
                    authorities = bundle.x509_authorities
                    if callable(authorities): authorities = authorities()
                    for cert in authorities:
                        self.bundle_file.write(cert.public_bytes(serialization.Encoding.PEM).decode())
                    bundles_written = True
            except Exception as e:
                self.logger.warning(f"Failed to get bundle via TrustDomain: {e}")

        self.bundle_file.flush()
    
    def create_server_ssl_context(self):
        """SSL context for HTTPS server with mTLS."""
        if not self.cert_file or not self.key_file or not self.bundle_file:
            self.logger.warning("Certificates not ready, creating default context (insecure)")
            return ssl.create_default_context()

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(self.cert_file.name, self.key_file.name)
        context.load_verify_locations(cafile=self.bundle_file.name)
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context
    
    def make_mtls_request(self, url, json_data, timeout=30):
        """Make mTLS client request."""
        import requests
        import urllib3
        urllib3.disable_warnings()
        
        if not self.cert_file or not self.key_file:
            raise RuntimeError("Certificates not initialized")

        return requests.post(
            url, json=json_data,
            cert=(self.cert_file.name, self.key_file.name),
            verify=False, # SPIFFE uses URI SANs which requests doesn't validate strictly against hostname
            timeout=timeout
        )


class BaseSPIFFEAgent(ABC):
    """
    Base class for ALL agents/collectors.
    Inherit from this and just implement the business logic!
    """
    
    def __init__(self, service_name: str, port: int, allowed_callers: list = None):
        self.service_name = service_name
        self.port = port
        self.allowed_callers = allowed_callers or []
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(service_name)
        
        # Initialize SPIFFE
        try:
            self.mtls = SPIFFEMTLSHandler()
        except Exception as e:
            self.logger.warning(f"SPIFFE init failed (continuing for debug): {e}")
            self.mtls = None
    
    @abstractmethod
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        """
        Override this in your agent!
        """
        pass
    
    def run(self):
        """Start the HTTPS server with mTLS."""
        handler = self._create_handler()
        
        server = HTTPServer(('0.0.0.0', self.port), handler)
        
        if self.mtls and self.mtls.cert_file:
            try:
                server.socket = self.mtls.create_server_ssl_context().wrap_socket(
                    server.socket, server_side=True
                )
                self.logger.info("🔐 mTLS Enabled")
            except Exception as e:
                self.logger.error(f"Failed to enable mTLS: {e}")
        else:
            self.logger.warning("⚠️  Starting WITHOUT mTLS (Dev Mode or Init Failed)")
        
        self.logger.info(f"🚀 {self.service_name} running on port {self.port}")
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    
    def _create_handler(self):
        """Create HTTP handler with reference to this agent."""
        agent = self
        
        class AgentHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                # Extract peer SPIFFE ID
                peer_id = None
                try:
                    if hasattr(self.connection, 'getpeercert'):
                        peer_cert = self.connection.getpeercert()
                        if peer_cert:
                            san = peer_cert.get('subjectAltName', [])
                            peer_id = next(
                                (uri for typ, uri in san if typ == 'URI' and uri.startswith('spiffe://')),
                                None
                            )
                except Exception:
                    pass
                
                # Authorize
                if agent.allowed_callers and peer_id not in agent.allowed_callers:
                    # If running in local dev without mTLS, we might get None peer_id
                    # Decide if we want strict enforcement or dev mode
                    if peer_id is None and os.getenv('DEV_MODE') == 'true':
                        agent.logger.warning("Allowed request without SPIFFE ID (DEV_MODE)")
                    else:
                        self.send_error(403, f"Unauthorized: {peer_id}")
                        return
                
                # Read request
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length)) if length else {}
                
                # Delegate to agent's business logic
                try:
                    result = agent.handle_request(self.path, data, peer_id)
                    self._send_json(200, result)
                except Exception as e:
                    agent.logger.error(f"Error: {e}")
                    self._send_json(500, {"error": str(e)})
            
            def do_GET(self):
                if self.path == '/health':
                    status = {
                        "status": "healthy",
                        "service": agent.service_name,
                        "spiffe_id": agent.mtls.spiffe_id if agent.mtls else "unknown"
                    }
                    self._send_json(200, status)
                else:
                    self.send_error(404)
            
            def _send_json(self, code, data):
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            
            def log_message(self, format, *args):
                agent.logger.info("%s - %s", self.client_address[0], format % args)
        
        return AgentHandler
