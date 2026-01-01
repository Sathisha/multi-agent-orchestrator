"""Local embedding provider using Sentence Transformers."""

from typing import List, Optional
import logging

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .base import BaseEmbeddingProvider


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using Sentence Transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize local embedding provider.
        
        Args:
            model_name: Name of the Sentence Transformer model to use
        """
        super().__init__()
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers package not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
        self._dimension: Optional[int] = None
    
    async def initialize(self) -> None:
        """Initialize the Sentence Transformer model."""
        if self._model is None:
            self.logger.info(f"Loading local embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            
            # Get embedding dimension from model
            self._dimension = self._model.get_sentence_embedding_dimension()
            
            self.logger.info(
                f"Local embedding model loaded: {self.model_name} "
                f"(dimension: {self._dimension})"
            )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self._model:
            await self.initialize()
        
        try:
            embedding = self._model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Failed to generate local embedding: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self._model:
            await self.initialize()
        
        try:
            embeddings = self._model.encode(texts, convert_to_tensor=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            self.logger.error(f"Failed to generate local embeddings: {e}")
            raise
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        if self._dimension is None:
            # Return default dimension for all-MiniLM-L6-v2
            return 384
        return self._dimension
