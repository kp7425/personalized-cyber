"""
LLM Gateway - Supports multiple backends (LM Studio local, Gemini cloud)

Isolate API keys to the gateway only!
AI agents never see the API key - they authenticate via SPIFFE.
"""

import os
import requests
from src.base.spiffe_agent import BaseSPIFFEAgent

LLM_BACKEND = os.getenv('LLM_BACKEND', 'gemini').lower()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')  # Updated to 2.5

TRUST_DOMAIN = os.getenv('TRUST_DOMAIN', 'security-training.example.org')

class LLMGateway(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="llm-gateway",
            port=8520,
            allowed_callers=[
                # Allow LMS and other services to call the gateway
                f"spiffe://{TRUST_DOMAIN}/lms",
                f"spiffe://{TRUST_DOMAIN}/lms-api",
                f"spiffe://{TRUST_DOMAIN}/risk-scorer",
            ]
        )
    
    def handle_request(self, path: str, data: dict, peer_spiffe_id: str) -> dict:
        if path == '/generate':
            return self._generate(data.get('messages', []), data.get('config', {}))
        return {"error": "Unknown path"}
    
    def _generate(self, messages: list, config: dict) -> dict:
        """Route to appropriate backend."""
        if LLM_BACKEND == 'gemini':
            return self._call_gemini(messages, config)
        elif LLM_BACKEND == 'lmstudio':
            return self._call_lmstudio(messages, config)
        else:
            return {"error": f"Unknown backend: {LLM_BACKEND}"}
    
    def _call_gemini(self, messages: list, config: dict) -> dict:
        """Call Google Gemini API using google-generativeai library."""
        if not GEMINI_API_KEY:
            return {"error": "GEMINI_API_KEY not set"}
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            # Build prompt from messages
            prompt_parts = []
            for msg in messages:
                role = msg['role']
                content = msg['content']
                if role == 'system':
                    prompt_parts.insert(0, f"Instructions: {content}\n\n")
                else:
                    prompt_parts.append(content)
            
            prompt = "\n".join(prompt_parts)
            
            # Generate content
            response = model.generate_content(prompt)
            
            # Extract text from response
            if response and hasattr(response, 'text') and response.text:
                return {
                    "content": response.text,
                    "model": GEMINI_MODEL,
                    "backend": "gemini"
                }
            elif response.candidates:
                # Try to extract from candidates
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    return {
                        "content": candidate.content.parts[0].text,
                        "model": GEMINI_MODEL,
                        "backend": "gemini"
                    }
                return {"error": f"No content in candidate: finish_reason={candidate.finish_reason}"}
            else:
                return {"error": "No response from Gemini"}
                
        except Exception as e:
            return {"error": str(e)}

    def _call_lmstudio(self, messages: list, config: dict) -> dict:
        """Call local LM Studio (OpenAI compatible)."""
        url = "http://host.docker.internal:1234/v1/chat/completions"
        try:
            response = requests.post(
                url,
                json={
                    "messages": messages,
                    "temperature": config.get('temperature', 0.7),
                    "max_tokens": config.get('max_tokens', -1),
                    "stream": False
                },
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            if response.status_code == 200:
                return {
                     "content": response.json()['choices'][0]['message']['content'],
                     "model": "local",
                     "backend": "lmstudio"
                }
            return {"error": f"LM Studio error: {response.text}"}
        except Exception as e:
            return {"error": str(e)}


if __name__ == '__main__':
    LLMGateway().run()
