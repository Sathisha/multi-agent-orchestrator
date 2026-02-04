
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
import io
from pypdf import PdfReader

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.rag import RAGSource, AgentRAGSource, RAGSourceType, RAGStatus
from shared.models.agent import Agent
from shared.services.base import BaseService
from shared.services.memory_manager import MemoryManager, MemoryConfig

# We can reuse MemoryManager's embedding and vector logic, 
# or instantiate a minimal version of it just for embeddings/chroma.
# actually, let's create a dedicated method in MemoryManager or similar to get the collection/embedding provider,
# but for now, to avoid refactoring MemoryManager too much, I'll adapt the logic here 
# or make RAGService accept a MemoryManager instance to leverage its initialized clients.

class RAGService(BaseService):
    def __init__(self, session: AsyncSession, memory_manager: MemoryManager):
        super().__init__(session, RAGSource)
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)

    async def create_source(
        self,
        name: str,
        source_type: RAGSourceType,
        content_source: str, # URL or file path (if uploaded, handle elsewhere?)
        owner_id: uuid.UUID,
        is_public: bool = False,
        file_content: bytes = None 
    ) -> RAGSource:
        source = RAGSource(
            name=name,
            source_type=source_type,
            content_source=content_source,
            owner_id=owner_id,
            is_public=is_public,
            status=RAGStatus.PENDING,
            processing_metadata={}
        )
        self.session.add(source)
        await self.session.commit()
        await self.session.refresh(source)
        
        # Trigger processing
        # In a real app, use a task queue. Here we verify functionality with await or background task.
        try:
            await self.process_source(source, file_content)
        except Exception as e:
            self.logger.error(f"Failed to process source {source.id}: {e}")
            source.status = RAGStatus.FAILED
            source.processing_metadata = {"error": str(e)}
            await self.session.commit()
            await self.session.refresh(source)
            
        return source

    async def process_source(self, source: RAGSource, file_content: bytes = None):
        source.status = RAGStatus.PROCESSING
        await self.session.commit()
        await self.session.refresh(source)
        
        try:
            text_content = ""
            if source.source_type == RAGSourceType.WEBSITE:
                text_content = await self._scrape_website(source.content_source)
            elif source.source_type == RAGSourceType.PDF:
                if file_content:
                    text_content = await self._parse_pdf_bytes(file_content)
                else:
                    # Maybe stored locally?
                    # For now assume file_content is passed if it's a new upload
                    pass
            elif source.source_type == RAGSourceType.TEXT:
                # content_source is the text itself? Or a file path?
                # let's assume content_source IS the text for simplicity if needed, or we read a file.
                text_content = source.content_source 

            if not text_content:
                raise ValueError("No content extracted")
                
            chunks = self._chunk_text(text_content)
            
            # Store chunks in Vector DB
            # We use a specific collection for RAG, maybe "rag_collection_{owner_id}"?
            # Or one big collection with metadata filter "source_id".
            # "rag_collection_shared" with filters is easier for querying across multiple sources.
            
            # We need to access the chroma client from memory manager
            # This relies on MemoryManager being initialized.
            if not self.memory_manager._chroma_client:
                await self.memory_manager.initialize()
                
            collection = self.memory_manager._chroma_client.get_or_create_collection(
                name=f"rag_kb_{source.owner_id}",
                metadata={"owner_id": str(source.owner_id)}
            )
            
            ids = [f"{source.id}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"source_id": str(source.id), "chunk_index": i, "source_name": source.name} for i in range(len(chunks))]
            
            # Generate embeddings
            embeddings = []
            for chunk in chunks:
                emb = await self.memory_manager._generate_embedding(chunk)
                embeddings.append(emb)
            
            collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings, # optimized to batch?
                metadatas=metadatas
            )
            
            source.status = RAGStatus.COMPLETED
            source.processing_metadata = {
                "chunks_count": len(chunks),
                "processed_at": datetime.utcnow().isoformat()
            }
            await self.session.commit()
            await self.session.refresh(source)
            
        except Exception as e:
            self.logger.exception("Error processing RAG source")
            raise e

    async def _scrape_website(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text

    async def _parse_pdf_bytes(self, content: bytes) -> str:
        text = ""
        with io.BytesIO(content) as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks
        
    async def get_sources_for_user(self, owner_id: uuid.UUID) -> List[RAGSource]:
        stmt = select(RAGSource).where(RAGSource.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
        
    async def delete_source(self, source_id: uuid.UUID, owner_id: uuid.UUID):
        stmt = select(RAGSource).where(and_(RAGSource.id == source_id, RAGSource.owner_id == owner_id))
        result = await self.session.execute(stmt)
        source = result.scalar_one_or_none()
        if source:
             # Cleanup vector DB
            if not self.memory_manager._chroma_client:
                await self.memory_manager.initialize()
            
            try:
                collection = self.memory_manager._chroma_client.get_collection(name=f"rag_kb_{owner_id}")
                collection.delete(where={"source_id": str(source.id)})
            except Exception:
                pass # Collection might not exist
                
            await self.session.delete(source)
            await self.session.commit()
            return True
        return False

    async def query(self, query_text: str, owner_id: uuid.UUID, limit: int = 5, agent_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        if not self.memory_manager._chroma_client:
            await self.memory_manager.initialize()
            
        try:
            collection = self.memory_manager._chroma_client.get_collection(name=f"rag_kb_{owner_id}")
        except Exception:
            return []
            
        where_filter = None
        if agent_id:
            # Get allowed sources for this agent
            stmt = select(AgentRAGSource.rag_source_id).where(AgentRAGSource.agent_id == agent_id)
            result = await self.session.execute(stmt)
            allowed_ids = [str(uid) for uid in result.scalars().all()]
            
            # If agent has specific sources assigned, invoke filtering
            # NOTE: If no sources are assigned, do we allow ALL or NONE? 
            # The user requirement: "assign RAG sources to Agents". 
            # If assignment exists, strict filter. If NO assignment, maybe default to all? 
            # Or "DO not always look...".
            # Let's assume: If I pass agent_id, and assignments exist, I restrict.
            # If NO assignments exist, maybe the agent shouldn't leverage RAG or leverage all?
            # It's safer to separate: "RAG Availability" vs "Source Scope".
            # If agent_id is passed, we check if there are ANY assignments.
            
            if allowed_ids:
                 where_filter = {"source_id": {"$in": allowed_ids}}
            else:
                 # No specific assignments -> User can access all their sources via this agent.
                 # This makes the tool useful immediately without explicit assignment.
                 # If user WANTS strictness, they just assign 1 source, then only that 1 is used.
                 where_filter = None 

        query_embedding = await self.memory_manager._generate_embedding(query_text)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
            where=where_filter
        )
        
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1.0 - results["distances"][0][i]
                })
        
        return formatted

    async def assign_source_to_agent(self, agent_id: uuid.UUID, source_id: uuid.UUID, owner_id: uuid.UUID):
        """Assign a RAG source to an agent."""
        # Verify source ownership
        source = await self.session.get(RAGSource, source_id)
        if not source or source.owner_id != owner_id:
            raise ValueError("Source not found or access denied")
            
        # Check existing assignment
        stmt = select(AgentRAGSource).where(
            and_(AgentRAGSource.agent_id == agent_id, AgentRAGSource.rag_source_id == source_id)
        )
        existing = await self.session.execute(stmt)
        if existing.scalar_one_or_none():
            return # Already assigned
            
        assignment = AgentRAGSource(
            agent_id=agent_id,
            rag_source_id=source_id
        )
        self.session.add(assignment)
        await self.session.commit()
        
    async def remove_source_from_agent(self, agent_id: uuid.UUID, source_id: uuid.UUID, owner_id: uuid.UUID):
        """Remove a RAG source assignment from an agent."""
        # Verify source ownership (optional, but safer)
        # source = await self.session.get(RAGSource, source_id)
        # if not source or source.owner_id != owner_id:
        #    raise ValueError("Access denied")
            
        stmt = select(AgentRAGSource).where(
            and_(AgentRAGSource.agent_id == agent_id, AgentRAGSource.rag_source_id == source_id)
        )
        result = await self.session.execute(stmt)
        assignment = result.scalar_one_or_none()
        
        if assignment:
            await self.session.delete(assignment)
            await self.session.commit()
            
    async def get_agent_sources(self, agent_id: uuid.UUID) -> List[RAGSource]:
        """Get all sources assigned to an agent."""
        stmt = select(RAGSource).join(AgentRAGSource).where(AgentRAGSource.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # ===== RBAC Methods =====
    
    async def check_access(
        self, 
        source_id: uuid.UUID, 
        user_id: uuid.UUID, 
        required_access: str = "view",
        user_roles: Optional[List[uuid.UUID]] = None
    ) -> bool:
        """
        Check if user has required access to a RAG source.
        
        Access is granted if:
        1. User is the owner
        2. Source is public (for 'view' and 'query' access)
        3. User has role-based permission
        """
        source = await self.session.get(RAGSource, source_id)
        if not source:
            return False
        
        # Owner has full access
        if source.owner_id == user_id:
            return True
        
        # Public sources allow view and query
        if source.is_public and required_access in ['view', 'query']:
            return True
        
        # Check role-based permissions
        if user_roles:
            from shared.models.rag import RAGSourceRole
            stmt = select(RAGSourceRole).where(
                and_(
                    RAGSourceRole.rag_source_id == source_id,
                    RAGSourceRole.role_id.in_(user_roles),
                    RAGSourceRole.access_type == required_access
                )
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                return True
        
        return False
    
    async def get_accessible_sources(
        self, 
        user_id: uuid.UUID, 
        user_roles: Optional[List[uuid.UUID]] = None
    ) -> List[RAGSource]:
        """Get all RAG sources accessible to the user (owned, public, or role-granted)."""
        from shared.models.rag import RAGSourceRole
        from sqlalchemy import or_
        
        conditions = [RAGSource.owner_id == user_id]  # Owned sources
        
        # Public sources
        conditions.append(RAGSource.is_public == True)
        
        # Role-granted sources
        if user_roles:
            role_source_ids = select(RAGSourceRole.rag_source_id).where(
                RAGSourceRole.role_id.in_(user_roles)
            )
            conditions.append(RAGSource.id.in_(role_source_ids))
        
        stmt = select(RAGSource).where(or_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def assign_role_to_source(
        self, 
        source_id: uuid.UUID, 
        role_id: uuid.UUID, 
        access_type: str,
        owner_id: uuid.UUID
    ):
        """Assign a role to a RAG source (owner only)."""
        from shared.models.rag import RAGSourceRole
        
        # Verify ownership
        source = await self.session.get(RAGSource, source_id)
        if not source or source.owner_id != owner_id:
            raise ValueError("Only the owner can assign roles")
        
        # Check if assignment already exists
        stmt = select(RAGSourceRole).where(
            and_(
                RAGSourceRole.rag_source_id == source_id,
                RAGSourceRole.role_id == role_id,
                RAGSourceRole.access_type == access_type
            )
        )
        existing = await self.session.execute(stmt)
        if existing.scalar_one_or_none():
            return  # Already assigned
        
        assignment = RAGSourceRole(
            rag_source_id=source_id,
            role_id=role_id,
            access_type=access_type
        )
        self.session.add(assignment)
        await self.session.commit()
    
    async def remove_role_from_source(
        self, 
        source_id: uuid.UUID, 
        role_id: uuid.UUID,
        owner_id: uuid.UUID
    ):
        """Remove a role from a RAG source (owner only)."""
        from shared.models.rag import RAGSourceRole
        
        # Verify ownership
        source = await self.session.get(RAGSource, source_id)
        if not source or source.owner_id != owner_id:
            raise ValueError("Only the owner can remove roles")
        
        stmt = select(RAGSourceRole).where(
            and_(
                RAGSourceRole.rag_source_id == source_id,
                RAGSourceRole.role_id == role_id
            )
        )
        result = await self.session.execute(stmt)
        assignments = result.scalars().all()
        
        for assignment in assignments:
            await self.session.delete(assignment)
        
        await self.session.commit()
    
    async def get_source_roles(self, source_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all role assignments for a RAG source."""
        from shared.models.rag import RAGSourceRole
        from shared.models.rbac import Role
        
        stmt = select(RAGSourceRole, Role).join(Role).where(
            RAGSourceRole.rag_source_id == source_id
        )
        result = await self.session.execute(stmt)
        
        roles = []
        for assignment, role in result:
            roles.append({
                "role_id": str(assignment.role_id),
                "role_name": role.name,
                "access_type": assignment.access_type
            })
        
        return roles

