"""OpenAI embedding provider using OpenAI's embedding API."""

from typing import List, Optional
import logging
import os

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using text-embedding-3-small."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimensions: Optional[int] = None
    ):
        """Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI embedding model to use
            dimensions: Optional dimension reduction (for text-embedding-3-* models)
        """
        super().__init__()
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. "
                "Install with: pip install openai"
            )
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        self.model = model
        self.dimensions = dimensions
        self._client: Optional[AsyncOpenAI] = None
        
        # Set default dimensions based on model
        if self.dimensions is None:
            if "text-embedding-3-small" in model:
                self._dimensions = 1536
            elif "text-embedding-3-large" in model:
                self._dimensions = 3072
            elif "text-embedding-ada-002" in model:
                self._dimensions = 1536
            else:
                self._dimensions = 1536  # Default
    
    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
            self.logger.info(f"OpenAI embedding provider initialized with model: {self.model}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using OpenAI API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self._client:
            await self.initialize()
        
        try:
            # Prepare parameters
            params = {
                "input": text,
                "model": self.model
            }
            
            # Add dimensions parameter for models that support it
            if self.dimensions and "text-embedding-3" in self.model:
                params["dimensions"] = self.dimensions
            
            response = await self._client.embeddings.create(**params)
            
            return response.data[0].embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate OpenAI embedding: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using OpenAI API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self._client:
            await self.initialize()
        
        try:
            # OpenAI supports batch embedding
            params = {
                "input": texts,
                "model": self.model
            }
            
            # Add dimensions parameter for models that support it
            if self.dimensions and "text-embedding-3" in self.model:
                params["dimensions"] = self.dimensions
            
            response = await self._client.embeddings.create(**params)
            
            # Return embeddings in the same order as input
            return [item.embedding for item in response.data]
            
        except Exception as e:
            self.logger.error(f"Failed to generate OpenAI embeddings: {e}")
            raise
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        return self.dimensions if self.dimensions else self._dimensions
