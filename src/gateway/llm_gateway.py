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
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')

class LLMGateway(BaseSPIFFEAgent):
    
    def __init__(self):
        super().__init__(
            service_name="llm-gateway",
            port=8520,
            allowed_callers=[
                f"spiffe://{os.getenv('TRUST_DOMAIN', 'security-training.example.org')}/lms-api"
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
        """Call Google Gemini API."""
        if not GEMINI_API_KEY:
            return {"error": "GEMINI_API_KEY not set"}
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        
        # Convert OpenAI-style messages to Gemini format
        contents = []
        system_instruction = None
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'system':
                system_instruction = content
            elif role == 'user':
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == 'assistant':
                contents.append({"role": "model", "parts": [{"text": content}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.get('temperature', 0.3),
                "maxOutputTokens": config.get('max_tokens', 500)
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        try:
            response = requests.post(
                f"{url}?key={GEMINI_API_KEY}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code != 200:
                return {"error": f"Gemini error: {response.status_code} - {response.text}"}
            
            result = response.json()
            # Handle safety blockings or other structures
            if 'candidates' in result and result['candidates']:
                return {
                    "content": result['candidates'][0]['content']['parts'][0]['text'],
                    "model": GEMINI_MODEL,
                    "backend": "gemini"
                }
            else:
                 return {"error": f"No candidates returned: {result}"}
                 
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
