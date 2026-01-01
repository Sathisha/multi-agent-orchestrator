import httpx
from typing import List, Dict, Any, Optional

class OllamaService:
    def __init__(self, ollama_base_url: str = "http://ollama:11434"):
        self.ollama_base_url = ollama_base_url
        self.client = httpx.AsyncClient()

    async def list_local_models(self) -> List[Dict[str, Any]]:
        """
        Lists all models that are available locally.
        https://github.com/ollama/ollama/blob/main/docs/api.md#list-local-models
        """
        try:
            response = await self.client.get(f"{self.ollama_base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except httpx.RequestError as e:
            print(f"Error connecting to Ollama: {e}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"Error from Ollama API: {e}")
            return []

    async def list_running_models(self) -> List[Dict[str, Any]]:
        """
        Lists models that are currently running.
        https://github.com/ollama/ollama/blob/main/docs/api.md#list-running-models
        """
        try:
            response = await self.client.get(f"{self.ollama_base_url}/api/ps")
            response.raise_for_status()
            return response.json().get("models", [])
        except httpx.RequestError as e:
            print(f"Error connecting to Ollama: {e}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"Error from Ollama API: {e}")
            return []

    async def generate_response(self, model_name: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates a response from a specified Ollama model.
        https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False # We want a single response
        }
        
        try:
            response = await self.client.post(f"{self.ollama_base_url}/api/chat", json=payload, timeout=600.0) # Increased timeout
            response.raise_for_status()
            return response.json()["message"]["content"]
        except httpx.RequestError as e:
            print(f"Error connecting to Ollama for generation: {e}")
            raise
        except httpx.HTTPStatusError as e:
            print(f"Error from Ollama API during generation: {e}")
            raise
        except KeyError:
            print(f"Unexpected response format from Ollama: {response.json()}")
            raise ValueError("Unexpected response format from Ollama")


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def __aenter__(self, ):
        return self

async def get_ollama_service() -> OllamaService:
    """Dependency injection for OllamaService."""
    service = OllamaService()
    try:
        yield service
    finally:
        await service.client.aclose()
