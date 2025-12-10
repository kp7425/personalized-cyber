#!/usr/bin/env python3
"""
Live Training Test Module - Run inside LMS pod to test mTLS LLM Gateway
"""
import json
import time
import sys
import os

sys.path.insert(0, "/app")

def test_training_generation(job_role, git_risk, iam_risk):
    """Test personalized training generation via mTLS"""
    start_time = time.time()
    result = {
        "success": False,
        "test_type": "LMS → mTLS → LLM Gateway → Gemini API"
    }
    
    try:
        from src.base.spiffe_agent import SPIFFEMTLSHandler
        
        handler = SPIFFEMTLSHandler()
        result["mtls_handler_initialized"] = True
        
        # Build personalized prompt
        prompt = f"""Create a 3-bullet personalized security training summary for:
- Job Role: {job_role}
- Git Risk Score: {git_risk:.2f} (secrets in commits, force pushes)
- IAM Risk Score: {iam_risk:.2f} (privilege escalation attempts)

Focus on their specific risks. Keep it to exactly 3 bullet points."""

        payload = {
            "messages": [
                {"role": "system", "content": "You are a cybersecurity training assistant."},
                {"role": "user", "content": prompt}
            ],
            "config": {"temperature": 0.7, "max_tokens": 500}
        }
        
        namespace = os.getenv("K8S_NAMESPACE", "security-training")
        gateway_url = f"https://llm-gateway-svc.{namespace}.svc.cluster.local:8520/generate"
        
        result["gateway_url"] = gateway_url
        
        response = handler.make_mtls_request(gateway_url, payload, timeout=30)
        
        duration = time.time() - start_time
        result["duration_seconds"] = duration
        
        if response and response.status_code == 200:
            resp_json = response.json()
            result["success"] = True
            result["model"] = resp_json.get("model", "unknown")
            result["backend"] = resp_json.get("backend", "unknown")
            result["content"] = resp_json.get("content", "")
            result["content_length"] = len(result["content"])
            result["mtls_verified"] = True
        else:
            result["error"] = f"Status {response.status_code if response else 'None'}"
            if response:
                result["response_text"] = response.text[:500]
                
    except Exception as e:
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        result["duration_seconds"] = time.time() - start_time
    
    return result

if __name__ == "__main__":
    # Get args from command line or use defaults
    job_role = sys.argv[1] if len(sys.argv) > 1 else "Security Engineer"
    git_risk = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
    iam_risk = float(sys.argv[3]) if len(sys.argv) > 3 else 0.75
    
    result = test_training_generation(job_role, git_risk, iam_risk)
    print(json.dumps(result, indent=2))
