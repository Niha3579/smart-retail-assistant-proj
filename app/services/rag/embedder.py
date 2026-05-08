"""
Embedder service using Azure OpenAI embedding deployments (no Hugging Face / local models).
"""
import logging
import os
from typing import Dict, List, Tuple

from flask import current_app

logger = logging.getLogger(__name__)


class Embedder:
    """Produces dense vectors via Azure OpenAI embeddings API."""

    API_VERSION = "2024-02-15-preview"

    def _resolve_config(self) -> Tuple[str, str, str]:
        cfg: Dict = {}
        try:
            cfg = dict(current_app.config)  # type: ignore[arg-type]
        except Exception:
            cfg = {}

        key = cfg.get("AZURE_OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY", "")
        endpoint = (cfg.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        deployment = cfg.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""
        )

        missing = []
        if not key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not deployment:
            missing.append("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        if missing:
            raise ValueError(f"Azure OpenAI embedding configuration missing: {', '.join(missing)}")

        return key, endpoint, deployment.rstrip("/")

    def _client_and_deployment(self):
        try:
            from openai import AzureOpenAI
        except ImportError as exc:
            raise ImportError("openai package required for embeddings.") from exc

        api_key, endpoint, deployment = self._resolve_config()
        client = AzureOpenAI(
            api_key=api_key,
            api_version=self.API_VERSION,
            azure_endpoint=endpoint,
        )
        return client, deployment

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Embed many strings; returns vectors in the same order as ``texts``."""
        if not texts:
            return []

        client, deployment = self._client_and_deployment()
        out: List[List[float]] = []

        batch_size = 64
        for start in range(0, len(texts), batch_size):
            chunk = texts[start : start + batch_size]
            response = client.embeddings.create(model=deployment, input=chunk)
            ordered = sorted(response.data, key=lambda d: d.index)
            for item in ordered:
                out.append(list(item.embedding))

        logger.debug("Embedded %s text fragments with deployment %s", len(out), deployment)
        return out

    def encode_single(self, text: str) -> List[float]:
        return self.encode([text])[0]
