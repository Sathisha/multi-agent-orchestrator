"""Ollama embedding provider implementation."""

from typing import List, Optional
import httpx
import logging
from .base import BaseEmbeddingProvider

class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using Ollama's API."""
    
    def __init__(self, base_url: str = "http://ollama:11434", model: str = "gemma:latest"):
        """Initialize Ollama embedding provider.
        
        Args:
            base_url: Base URL for Ollama API
            model: Model name to use for embeddings
        """
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        self._embedding_dimension = None

    async def initialize(self) -> None:
        """Initialize and verify connection to Ollama with retries."""
        import asyncio
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Check connection and retrieve embedding dimension if possible
                # We use a dummy text to check if the model supports embeddings
                result = await self.generate_embedding("test")
                self._embedding_dimension = len(result)
                self.logger.info(f"Ollama embedding provider initialized with model {self.model}, dimension {self._embedding_dimension}")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Failed to initialize Ollama (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to initialize Ollama embedding provider after {max_retries} attempts: {e}")
                    raise

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            response = await self.client.post("/api/embeddings", json=payload)
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            self.logger.error(f"Error generating Ollama embedding: {e}")
            raise

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        # Ollama currently doesn't support batch embeddings in one call in a standard way
        # that is consistent across all versions/models. We'll do it sequentially for now.
        return [await self.generate_embedding(text) for text in texts]

    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        if self._embedding_dimension is None:
            # This should ideally be set during initialize
            return 3072 # Fallback for gemma/llama if not yet initialized
        return self._embedding_dimension
