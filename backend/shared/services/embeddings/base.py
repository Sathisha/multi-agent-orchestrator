"""Embedding providers for memory system."""

from abc import ABC, abstractmethod
from typing import List
import logging


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the embedding provider."""
        pass
    
    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        pass
