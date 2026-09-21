"""
Local RAG (Retrieval-Augmented Generation) Tool

ChromaDB-based vector store for document ingestion and semantic search.
Uses nomic-embed-text for embeddings (local, air-gapped).
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional import - chromadb not required for basic functionality
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None

from src.tools.base import Tool
from src.models.ollama_backend import OllamaBackend
from src.utils.constants import (
    CHROMA_PATH,
    EMBEDDING_MODEL,
    RAG_TOP_K,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    KB_DIR,
    SUPPORTED_DOCUMENT_FORMATS,
)

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunk documents for RAG ingestion."""
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = RAG_CHUNK_SIZE,
        overlap: int = RAG_CHUNK_OVERLAP
    ) -> List[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Input text
            chunk_size: Characters per chunk
            overlap: Overlap between chunks
        
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence ending
                last_period = chunk.rfind('. ')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return [c for c in chunks if c]  # Remove empty chunks
    
    @staticmethod
    def extract_text_from_file(file_path: Path) -> str:
        """
        Extract text from various file formats.
        
        Args:
            file_path: Path to document
        
        Returns:
            Extracted text
        """
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.txt' or ext == '.md':
                return file_path.read_text(encoding='utf-8')
            
            elif ext == '.pdf':
                import pdfplumber
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text_parts.append(page.extract_text() or "")
                return "\n\n".join(text_parts)
            
            elif ext == '.docx':
                from docx import Document
                doc = Document(file_path)
                return "\n\n".join([p.text for p in doc.paragraphs])
            
            elif ext == '.csv':
                import pandas as pd
                df = pd.read_csv(file_path)
                return df.to_string()
            
            elif ext == '.xlsx':
                import pandas as pd
                df = pd.read_excel(file_path)
                return df.to_string()
            
            else:
                raise ValueError(f"Unsupported file format: {ext}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            raise


class LocalRAGTool(Tool):
    """Tool for ingesting documents into local knowledge base."""
    
    def __init__(self, backend: OllamaBackend):
        super().__init__(
            name="ingest_document",
            description=(
                "Ingest a document into the local knowledge base for later retrieval. "
                "Supports: PDF, DOCX, TXT, MD, CSV, XLSX. "
                "Document is chunked, embedded, and stored in ChromaDB. "
                "Input: file_path (required), metadata (optional dict with tags/category)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to document file to ingest"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata (tags, category, date, etc.)"
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Characters per chunk (default: 500)"
                    }
                },
                "required": ["file_path"]
            }
        )
        self.backend = backend
        self.chunker = DocumentChunker()
        
        # Initialize ChromaDB
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"description": "Sentinel AI local knowledge base"}
        )
        
        logger.info(f"ChromaDB initialized at {CHROMA_PATH}")

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Ollama."""
        try:
            embeddings = []
            for text in texts:
                response = await self.backend.embed(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                
                if isinstance(response, dict) and "embeddings" in response:
                    embeddings.append(response["embeddings"][0])
                elif isinstance(response, dict) and "embedding" in response:
                    embeddings.append(response["embedding"])
                elif isinstance(response, list):
                    embeddings.append(response)
                else:
                    raise ValueError(f"Unexpected embedding response: {type(response)}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _execute_impl(self, **kwargs) -> str:
        """Execute document ingestion."""
        file_path_str = kwargs.get("file_path")
        metadata = kwargs.get("metadata", {})
        chunk_size = kwargs.get("chunk_size", RAG_CHUNK_SIZE)
        
        if not file_path_str:
            return json.dumps({"error": "file_path is required"})
        
        try:
            file_path = Path(file_path_str).resolve()
            
            if not file_path.exists():
                return json.dumps({"error": f"File not found: {file_path}"})
            
            if file_path.suffix.lower() not in SUPPORTED_DOCUMENT_FORMATS:
                return json.dumps({
                    "error": f"Unsupported format: {file_path.suffix}",
                    "supported": list(SUPPORTED_DOCUMENT_FORMATS)
                })
            
            logger.info(f"Ingesting document: {file_path}")
            
            # Extract text
            text = self.chunker.extract_text_from_file(file_path)
            
            if not text or len(text.strip()) < 10:
                return json.dumps({"error": "Document appears empty or invalid"})
            
            # Chunk text
            chunks = self.chunker.chunk_text(text, chunk_size=chunk_size)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Generate embeddings
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                embeddings = loop.run_until_complete(self._get_embeddings(chunks))
            finally:
                loop.close()
            
            # Generate document ID
            doc_id = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
            
            # Prepare metadata for each chunk
            chunk_metadatas = []
            chunk_ids = []
            
            for idx in range(len(chunks)):
                chunk_meta = {
                    "source": str(file_path),
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "doc_id": doc_id,
                    **metadata  # Add user-provided metadata
                }
                chunk_metadatas.append(chunk_meta)
                chunk_ids.append(f"{doc_id}_chunk_{idx}")
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Ingested {len(chunks)} chunks into ChromaDB")
            
            result = {
                "status": "success",
                "file_path": str(file_path),
                "doc_id": doc_id,
                "chunks_created": len(chunks),
                "total_characters": len(text),
                "metadata": metadata
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            return json.dumps({"error": str(e)})


class SemanticSearchTool(Tool):
    """Tool for semantic search in knowledge base."""
    
    def __init__(self, backend: OllamaBackend):
        super().__init__(
            name="search_knowledge_base",
            description=(
                "Search the local knowledge base using semantic similarity. "
                "Returns relevant document chunks with sources and metadata. "
                "Input: query (required), top_k (optional, default 5), filter_metadata (optional dict)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (semantic search)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)"
                    },
                    "filter_metadata": {
                        "type": "object",
                        "description": "Filter results by metadata (e.g., {'category': 'manual'})"
                    }
                },
                "required": ["query"]
            }
        )
        self.backend = backend
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection("knowledge_base")
        except Exception:
            # Collection doesn't exist yet
            self.collection = None

    async def _embed_query(self, query: str) -> List[float]:
        """Embed search query."""
        response = await self.backend.embed(
            model=EMBEDDING_MODEL,
            input=query
        )
        
        if isinstance(response, dict) and "embeddings" in response:
            return response["embeddings"][0]
        elif isinstance(response, dict) and "embedding" in response:
            return response["embedding"]
        elif isinstance(response, list):
            return response
        else:
            raise ValueError(f"Unexpected embedding response: {type(response)}")

    def _execute_impl(self, **kwargs) -> str:
        """Execute semantic search."""
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", RAG_TOP_K)
        filter_metadata = kwargs.get("filter_metadata")
        
        if not query:
            return json.dumps({"error": "query is required"})
        
        if not self.collection:
            return json.dumps({
                "error": "Knowledge base is empty. Ingest documents first using ingest_document tool."
            })
        
        try:
            logger.info(f"Searching knowledge base: '{query}' (top_k={top_k})")
            
            # Embed query
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                query_embedding = loop.run_until_complete(self._embed_query(query))
            finally:
                loop.close()
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata if filter_metadata else None
            )
            
            # Format results
            formatted_results = []
            
            if results and results.get("documents") and results["documents"][0]:
                for idx in range(len(results["documents"][0])):
                    result_item = {
                        "rank": idx + 1,
                        "text": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx] if results.get("metadatas") else {},
                        "distance": results["distances"][0][idx] if results.get("distances") else None,
                    }
                    formatted_results.append(result_item)
            
            output = {
                "query": query,
                "results_count": len(formatted_results),
                "results": formatted_results
            }
            
            return json.dumps(output, indent=2)
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return json.dumps({"error": str(e)})


class KBStatsTool(Tool):
    """Tool for knowledge base statistics."""
    
    def __init__(self):
        super().__init__(
            name="kb_stats",
            description=(
                "Get statistics about the local knowledge base. "
                "Returns document count, chunk count, and metadata summary."
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection("knowledge_base")
        except Exception:
            self.collection = None

    def _execute_impl(self, **kwargs) -> str:
        """Execute stats query."""
        if not self.collection:
            return json.dumps({
                "status": "empty",
                "message": "Knowledge base is empty"
            })
        
        try:
            # Get all items
            count = self.collection.count()
            
            if count == 0:
                return json.dumps({
                    "status": "empty",
                    "message": "Knowledge base is empty"
                })
            
            # Get sample to analyze
            sample = self.collection.get(limit=min(count, 100))
            
            # Extract unique documents
            doc_ids = set()
            sources = set()
            
            if sample and sample.get("metadatas"):
                for meta in sample["metadatas"]:
                    if "doc_id" in meta:
                        doc_ids.add(meta["doc_id"])
                    if "source" in meta:
                        sources.add(meta["source"])
            
            stats = {
                "total_chunks": count,
                "unique_documents": len(doc_ids),
                "unique_sources": len(sources),
                "sources": list(sources)[:10],  # First 10 sources
                "chroma_path": str(CHROMA_PATH)
            }
            
            return json.dumps(stats, indent=2)
            
        except Exception as e:
            logger.error(f"Stats query failed: {e}")
            return json.dumps({"error": str(e)})


class KBDeleteTool(Tool):
    """Tool for deleting documents from knowledge base."""
    
    def __init__(self):
        super().__init__(
            name="kb_delete",
            description=(
                "Delete a document from the knowledge base by doc_id or source path. "
                "Use kb_stats to find doc_ids and sources first."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID to delete"
                    },
                    "source": {
                        "type": "string",
                        "description": "Source file path to delete (alternative to doc_id)"
                    }
                },
                "required": []
            }
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.client.get_collection("knowledge_base")
        except Exception:
            self.collection = None

    def _execute_impl(self, **kwargs) -> str:
        """Execute deletion."""
        doc_id = kwargs.get("doc_id")
        source = kwargs.get("source")
        
        if not doc_id and not source:
            return json.dumps({"error": "Either doc_id or source is required"})
        
        if not self.collection:
            return json.dumps({"error": "Knowledge base is empty"})
        
        try:
            # Build filter
            if doc_id:
                where_filter = {"doc_id": doc_id}
            else:
                where_filter = {"source": source}
            
            # Get matching items
            items = self.collection.get(where=where_filter)
            
            if not items or not items.get("ids"):
                return json.dumps({
                    "status": "not_found",
                    "message": f"No documents found matching filter: {where_filter}"
                })
            
            # Delete items
            self.collection.delete(ids=items["ids"])
            
            result = {
                "status": "success",
                "deleted_chunks": len(items["ids"]),
                "filter": where_filter
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            return json.dumps({"error": str(e)})
