"""Local embedding services powered by HuggingFace sentence-transformers."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from langchain_huggingface import HuggingFaceEmbeddings


class EmbeddingServiceError(Exception):
	"""Raised for embedding provider failures."""


@dataclass
class EmbeddingConfig:
	"""Configuration container for local HuggingFace embedding calls."""

	model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
	encode_batch_size: int = 32


def load_embedding_config_from_env() -> EmbeddingConfig:
	"""Load local embedding settings from environment variables."""
	return EmbeddingConfig(
		model_name=os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
		encode_batch_size=int(os.getenv("HF_EMBEDDING_BATCH_SIZE", "32")),
	)


class LocalEmbeddingService:
	"""Local HuggingFace embedding client with async helpers."""

	def __init__(self, config: EmbeddingConfig | None = None) -> None:
		self.config = config or load_embedding_config_from_env()
		self._model = HuggingFaceEmbeddings(
			model_name=self.config.model_name,
			encode_kwargs={"batch_size": self.config.encode_batch_size, "normalize_embeddings": True},
		)

	def _embed_documents_sync(self, texts: list[str]) -> list[list[float]]:
		return self._model.embed_documents(texts)

	def _embed_query_sync(self, query: str) -> list[float]:
		return self._model.embed_query(query)

	async def embed_texts(self, texts: list[str]) -> list[list[float]]:
		"""Create embeddings for multiple texts locally."""
		if not texts:
			return []
		try:
			return await asyncio.to_thread(self._embed_documents_sync, texts)
		except Exception as exc:  # noqa: BLE001
			raise EmbeddingServiceError(f"Local embedding islemi basarisiz: {exc}") from exc

	async def embed_query(self, query: str) -> list[float]:
		"""Create embedding for a query string locally."""
		if not query.strip():
			raise EmbeddingServiceError("Sorgu embedding icin bos olamaz.")
		try:
			return await asyncio.to_thread(self._embed_query_sync, query)
		except Exception as exc:  # noqa: BLE001
			raise EmbeddingServiceError(f"Sorgu embedding uretilemedi: {exc}") from exc
