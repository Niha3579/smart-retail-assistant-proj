"""
Document Assistant Agent for handling PDF search and RAG-based Q&A.
Uses Azure AI Search for retrieval and Azure OpenAI for embeddings / answer generation.
"""
import csv
import logging
import os
from typing import List, Dict, Optional

from flask import current_app

from app.services.rag.embedder import Embedder
from app.services.rag.pdf_processor import PDFProcessor
from app.services.rag.azure_search_store import AzureSearchStore

logger = logging.getLogger(__name__)


class DocumentAssistantAgent:
    """Agent for document search and question answering using RAG on Azure."""

    def __init__(self):
        self.embedder = Embedder()
        self.pdf_processor = PDFProcessor()
        self.vector_store = AzureSearchStore()

    def upload_document(self, file_path: str, filename: str) -> bool:
        """Upload and process a document through chunking → embedding → Azure Search."""
        try:
            ext = os.path.splitext(filename.lower())[1]
            text = self._extract_text(file_path, ext)
            if not text:
                logger.error(f"Failed to extract text from {filename}")
                return False

            chunks = self.pdf_processor.chunk_text(text)
            if not chunks:
                logger.error(f"No chunks generated from {filename}")
                return False

            embeddings = self.embedder.encode(chunks)

            metadata = [
                {
                    "filename": filename,
                    "text": chunk,
                    "chunk_id": i,
                }
                for i, chunk in enumerate(chunks)
            ]

            self.vector_store.add_documents(embeddings, metadata)

            logger.info(f"Successfully uploaded document: {filename}")
            return True

        except Exception as e:
            logger.error(f"Error uploading document {filename}: {e}")
            return False

    def _extract_text(self, file_path: str, ext: str) -> Optional[str]:
        """Extract document text for supported file types."""
        if ext == ".pdf":
            return self.pdf_processor.extract_text(file_path)

        if ext in {".txt", ".csv"}:
            if not os.path.exists(file_path):
                logger.error(f"Document file not found: {file_path}")
                return None

            try:
                if ext == ".csv":
                    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as handle:
                        reader = csv.reader(handle)
                        rows = [", ".join(cell.strip() for cell in row if cell.strip()) for row in reader]
                    return "\n".join(row for row in rows if row).strip()

                with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                    return handle.read().strip()
            except Exception as exc:
                logger.error(f"Error extracting text from {file_path}: {exc}")
                return None

        logger.warning(f"Unsupported document type for RAG ingestion: {ext}")
        return None

    def delete_document(self, filename: str) -> bool:
        """Remove all chunks for a document from Azure AI Search."""
        try:
            self.vector_store.delete_document(filename)
            logger.info(f"Successfully deleted document: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {filename}: {e}")
            return False

    def search_documents(self, query: str, k: int = 3) -> List[Dict]:
        """Vector search via Azure AI Search."""
        try:
            query_embedding = self.embedder.encode_single(query)

            results = self.vector_store.search(query_embedding, k)

            logger.info(f"Found {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    def answer_question(self, query: str, use_openai: bool = True) -> Dict:
        """Answer a question using retrieved context and Azure OpenAI (or extractive fallback)."""
        try:
            search_results = self.search_documents(query, k=3)

            if not search_results:
                return {
                    "agent": "Document Assistant",
                    "response": "I couldn't find any relevant information in the uploaded documents.",
                    "confidence": 0.0,
                    "sources": [],
                }

            context_parts = []
            sources = []

            for result in search_results:
                context_parts.append(f"Document ({result['filename']}): {result['text']}")
                src = {
                    "filename": result["filename"],
                    "relevance_score": result.get("relevance_score"),
                }
                legacy = result.get("distance")
                if legacy is not None:
                    src["distance"] = legacy
                sources.append(src)

            context = "\n\n".join(context_parts)

            if use_openai:
                answer = self._generate_openai_answer(query, context)
            else:
                answer = context[:500] + "..." if len(context) > 500 else context

            return {
                "agent": "Document Assistant",
                "response": answer,
                "confidence": 0.8,
                "sources": sources,
            }

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "agent": "Document Assistant",
                "response": f"Sorry, I encountered an error while processing your question: {str(e)}",
                "confidence": 0.0,
                "sources": [],
            }

    def _generate_openai_answer(self, query: str, context: str) -> str:
        """Generate an answer using Azure OpenAI chat deployment (fallback: public OpenAI, then extractive)."""
        try:
            try:
                from openai import AzureOpenAI, OpenAI
            except Exception as exc:
                logger.warning(f"OpenAI client unavailable, falling back to extractive answer: {exc}")
                return self._extractive_answer(context)

            app_config = {}
            try:
                app_config = current_app.config
            except Exception:
                app_config = {}

            azure_key = app_config.get("AZURE_OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY", "")
            azure_endpoint = app_config.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            azure_deployment = app_config.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get(
                "AZURE_OPENAI_DEPLOYMENT", ""
            )
            openai_key = app_config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

            if azure_key and azure_endpoint and azure_deployment:
                client = AzureOpenAI(
                    api_key=azure_key,
                    api_version=self.embedder.API_VERSION,
                    azure_endpoint=azure_endpoint,
                )
                model = azure_deployment
            elif openai_key:
                client = OpenAI(api_key=openai_key)
                model = "gpt-4o-mini"
            else:
                logger.info("No OpenAI credentials configured, using extractive answer fallback.")
                return self._extractive_answer(context)

            prompt = f"""Answer the user's question based ONLY on the provided context. If the information is not in the context, say so.

Context:
{context}

Question: {query}

Answer:"""

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful document assistant. Answer questions based only on the provided context.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating OpenAI answer: {e}")
            return self._extractive_answer(context)

    @staticmethod
    def _extractive_answer(context: str) -> str:
        """Return a safe fallback when an LLM is unavailable."""
        if not context:
            return "I couldn't find any relevant information in the uploaded documents."
        return context[:1200] + ("..." if len(context) > 1200 else "")

    def get_stats(self) -> Dict:
        """Statistics from Azure AI Search index."""
        return self.vector_store.get_stats()


document_agent = DocumentAssistantAgent()
