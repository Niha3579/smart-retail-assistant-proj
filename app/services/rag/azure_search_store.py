"""
Azure AI Search vector index for chunked documents and similarity search.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List

from flask import current_app

logger = logging.getLogger(__name__)


def _escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


class AzureSearchStore:
    """Upload, search, and delete documents in Azure AI Search (vector index)."""

    def __init__(self):
        cfg: Dict[str, Any] = {}
        try:
            cfg = dict(current_app.config)  # type: ignore[arg-type]
        except Exception:
            cfg = {}

        import os

        self.endpoint = (cfg.get("AZURE_SEARCH_ENDPOINT") or os.environ.get("AZURE_SEARCH_ENDPOINT", "")).rstrip("/")
        self.key = cfg.get("AZURE_SEARCH_KEY") or os.environ.get("AZURE_SEARCH_KEY", "")
        self.index_name = cfg.get("AZURE_SEARCH_INDEX") or os.environ.get("AZURE_SEARCH_INDEX", "")
        self.vector_field = (
            cfg.get("AZURE_SEARCH_VECTOR_FIELD") or os.environ.get("AZURE_SEARCH_VECTOR_FIELD", "contentVector")
        )
        self.content_field = (
            cfg.get("AZURE_SEARCH_CONTENT_FIELD") or os.environ.get("AZURE_SEARCH_CONTENT_FIELD", "content")
        )
        self._client = None

    def _configured(self) -> bool:
        return bool(self.endpoint and self.key and self.index_name)

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self._configured():
            raise ValueError(
                "Azure AI Search is not configured. Set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY, and AZURE_SEARCH_INDEX."
            )
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
        except ImportError as exc:
            raise ImportError("Install azure-search-documents to use Azure AI Search.") from exc

        self._client = SearchClient(self.endpoint, self.index_name, AzureKeyCredential(self.key))
        return self._client

    def _sanitize_key_part(self, s: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", s)[:128]

    def add_documents(self, embeddings: List[List[float]], metadata: List[Dict]) -> None:
        """Upload chunk documents with embeddings. metadata entries use keys: filename, text, chunk_id."""
        if len(embeddings) != len(metadata):
            raise ValueError("embeddings and metadata lengths must match")
        client = self._get_client()
        docs: List[Dict] = []
        for emb, meta in zip(embeddings, metadata):
            cid = meta.get("chunk_id", 0)
            fname = meta.get("filename", "unknown")
            safe = self._sanitize_key_part(fname)
            doc_id = f"{uuid.uuid4().hex}_{safe}_{cid}"
            body = {
                "id": doc_id,
                "filename": fname,
                "chunk_id": int(cid),
                self.content_field: meta.get("text", ""),
                self.vector_field: list(emb),
            }
            docs.append(body)

        batch_size = 50
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            result = client.merge_or_upload_documents(documents=batch)
            for r in result:
                if not r.succeeded:
                    logger.error("Azure Search upload failed for key %s: %s", r.key, r.error_message)

    def search(self, query_embedding: List[float], k: int = 3) -> List[Dict]:
        """Vector search; returns rows compatible with DocumentAssistantAgent (filename, text, relevance_score)."""
        try:
            client = self._get_client()
        except Exception as exc:
            logger.warning("%s", exc)
            return []

        try:
            from azure.search.documents.models import VectorizedQuery
        except ImportError:
            logger.error("azure-search-documents is required for AzureSearchStore.")
            return []

        qv = VectorizedQuery(vector=query_embedding, k_nearest_neighbors=k, fields=self.vector_field)
        fields = ["filename", self.content_field, "chunk_id"]

        kwargs: Dict[str, Any] = {
            "vector_queries": [qv],
            "top": k,
            "select": fields,
        }
        try:
            results_iter = client.search(search_text=None, **kwargs)
        except Exception:
            results_iter = client.search(search_text="*", **kwargs)

        rows: List[Dict] = []
        for raw in results_iter:
            payload = dict(raw)
            vec_text = payload.get(self.content_field) or ""
            score = payload.get("@search.score", 0.0) or 0.0
            rows.append(
                {
                    "filename": payload.get("filename", ""),
                    "text": vec_text,
                    "chunk_id": payload.get("chunk_id"),
                    "relevance_score": float(score) if score is not None else 0.0,
                }
            )
        logger.info("Azure AI Search returned %s vector hits", len(rows))
        return rows

    def delete_document(self, filename: str) -> None:
        client = self._get_client()
        esc = _escape_odata_string(filename)
        filt = f"filename eq '{esc}'"

        ids: List[str] = []
        skip = 0
        page_size = 1000
        while True:
            page = list(
                client.search(
                    search_text="*",
                    filter=filt,
                    select=["id"],
                    top=page_size,
                    skip=skip,
                )
            )
            if not page:
                break
            for hit in page:
                hid = hit.get("id")
                if hid:
                    ids.append(str(hid))
            skip += len(page)
            if len(page) < page_size:
                break

        if not ids:
            logger.info("No Azure Search chunks for filename=%s", filename)
            return

        seen = set()
        uniq = []
        for i in ids:
            if i and i not in seen:
                seen.add(i)
                uniq.append(i)

        chunk_size = 500
        for i in range(0, len(uniq), chunk_size):
            batch = uniq[i : i + chunk_size]
            client.delete_documents(documents=[{"id": dok} for dok in batch])
        logger.info("Deleted %s Azure Search chunks for %s", len(uniq), filename)

    def get_stats(self) -> Dict:
        if not self._configured():
            return {"total_vectors": 0, "dimension": None, "total_documents": 0}

        try:
            client = self._get_client()
            results = client.search(
                search_text="*",
                include_total_count=True,
                facets=["filename,count:1000"],
                select=["id"],
                top=1,
            )
            for _ in results:
                break

            total = int(results.get_count()) if hasattr(results, "get_count") else 0

            facets = results.get_facets() or {}
            doc_count = len(facets.get("filename") or []) if facets else 0

            return {
                "total_vectors": total,
                "dimension": None,
                "total_documents": doc_count,
            }
        except Exception as exc:
            logger.error("Azure Search stats error: %s", exc)
            return {"total_vectors": 0, "dimension": None, "total_documents": 0}
