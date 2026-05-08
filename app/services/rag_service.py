"""
Lightweight RAG helper for scripts/tests: chunk, Azure OpenAI embeddings, Azure AI Search.
Same backend index as ``DocumentAssistantAgent``, without file uploads.
"""
import logging
from typing import Dict, List

from app.services.rag.embedder import Embedder
from app.services.rag.pdf_processor import PDFProcessor
from app.services.rag.azure_search_store import AzureSearchStore

logger = logging.getLogger(__name__)


class RAGService:
    """Index plain text snippets into Azure AI Search for vector queries."""

    def __init__(self):
        self.processor = PDFProcessor()
        self.embedder = Embedder()
        self.store = AzureSearchStore()

    def chunk_text(self, text: str) -> List[str]:
        return self.processor.chunk_text(text)

    def add_document(self, filename: str, text: str) -> None:
        chunks = self.chunk_text(text)
        if not chunks:
            logger.warning("No chunks for document %s", filename)
            return

        embeddings = self.embedder.encode(chunks)
        metadata = [{"filename": filename, "text": c, "chunk_id": i} for i, c in enumerate(chunks)]
        self.store.add_documents(embeddings, metadata)
        logger.info("Indexed %s chunks for %s", len(chunks), filename)

    def search(self, query: str, k: int = 3) -> List[Dict]:
        try:
            qvec = self.embedder.encode_single(query)
            rows = self.store.search(qvec, k=k)
            return [
                {
                    "filename": r["filename"],
                    "text": r["text"],
                    "relevance_score": r.get("relevance_score"),
                    "distance": r.get("distance"),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []


rag_service = RAGService()
