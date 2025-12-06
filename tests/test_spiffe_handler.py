import pytest
from unittest.mock import MagicMock, patch
from src.base.spiffe_agent import SPIFFEMTLSHandler

@patch('src.base.spiffe_agent.WorkloadApiClient')
def test_refresh_certificates_failure(mock_client_cls):
    """Test that handler handles SPIRE unavailability gracefully."""
    # Setup mock to raise exception
    mock_client_cls.side_effect = Exception("SPIRE not available")
    
    # Init handler (should not crash)
    handler = SPIFFEMTLSHandler()
    
    # Verify no certs charged
    assert handler.cert_file is None
    assert handler.key_file is None
    
    # Verify we can still create a default (insecure) context
    context = handler.create_server_ssl_context()
    assert context is not None

@patch('src.base.spiffe_agent.WorkloadApiClient')
def test_refresh_certificates_success(mock_client_cls):
    """Test successful certificate fetch."""
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    
    # Mock SVID
    mock_svid = MagicMock()
    mock_svid.spiffe_id = "spiffe://example.org/myservice"
    mock_svid.cert_chain = b"cert_data"
    mock_svid.private_key = b"key_data"
    mock_client.fetch_x509_svid.return_value = mock_svid
    
    # Mock Bundle
    mock_bundle = MagicMock()
    # Mock _bundles dict approach
    mock_bundle._bundles = {} 
    mock_client.fetch_x509_bundles.return_value = mock_bundle
    
    handler = SPIFFEMTLSHandler()
    
    # Should have refreshed
    assert handler.spiffe_id == "spiffe://example.org/myservice"
    assert handler.cert_file is not None
    assert handler.key_file is not None
