"""Embedding services powered by Gemini-compatible integrations."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

import google.generativeai as genai

try:
	from sentence_transformers import SentenceTransformer
except Exception:  # noqa: BLE001
	SentenceTransformer = None


class EmbeddingServiceError(Exception):
	"""Raised for embedding provider failures."""


@dataclass
class EmbeddingConfig:
	"""Configuration container for Gemini embedding calls."""

	api_key: str
	model_name: str = "models/text-embedding-004"
	max_retries: int = 4
	initial_retry_delay_sec: float = 1.0
	timeout_sec: int = 45


def load_embedding_config_from_env() -> EmbeddingConfig:
	"""Load embedding settings from environment variables."""
	api_key = os.getenv("GEMINI_API_KEY", "").strip()
	if not api_key:
		raise EmbeddingServiceError("GEMINI_API_KEY bulunamadi. .env ayarini kontrol edin.")

	return EmbeddingConfig(
		api_key=api_key,
		model_name=os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"),
		max_retries=int(os.getenv("EMBEDDING_MAX_RETRIES", "4")),
		initial_retry_delay_sec=float(os.getenv("EMBEDDING_RETRY_DELAY_SEC", "1.0")),
		timeout_sec=int(os.getenv("EMBEDDING_TIMEOUT_SEC", "45")),
	)


class GeminiEmbeddingService:
	"""Gemini embedding client with retry-aware async helpers."""

	def __init__(self, config: EmbeddingConfig | None = None) -> None:
		self.config = config or load_embedding_config_from_env()
		genai.configure(api_key=self.config.api_key)
		self._local_model = None

	def _get_local_model(self):
		"""Lazy-load local embedding model for fallback mode."""
		if SentenceTransformer is None:
			raise EmbeddingServiceError("Local embedding modeli kullanilamiyor (sentence-transformers yok).")
		if self._local_model is None:
			model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
			self._local_model = SentenceTransformer(model_name)
		return self._local_model

	def _embed_one_local_sync(self, text: str) -> list[float]:
		"""Generate embedding using local model when API embedding is unavailable."""
		model = self._get_local_model()
		vector = model.encode(text, normalize_embeddings=True)
		return vector.tolist()

	def _is_retryable_error(self, error: Exception) -> bool:
		message = str(error).lower()
		retry_markers = [
			"429",
			"rate",
			"quota",
			"timeout",
			"tempor",
			"unavailable",
			"deadline",
		]
		return any(marker in message for marker in retry_markers)

	def _embed_one_sync(self, text: str) -> list[float]:
		"""Blocking single embedding call with exponential backoff."""
		retry_delay = self.config.initial_retry_delay_sec

		for attempt in range(1, self.config.max_retries + 1):
			try:
				response = genai.embed_content(
					model=self.config.model_name,
					content=text,
					task_type="retrieval_document",
				)
				embedding = response.get("embedding")
				if not embedding:
					raise EmbeddingServiceError("Gemini embedding yaniti bos dondu.")
				return embedding
			except Exception as exc:  # noqa: BLE001
				is_last_attempt = attempt == self.config.max_retries
				if is_last_attempt or not self._is_retryable_error(exc):
					raise EmbeddingServiceError(
						f"Embedding cagrisinda hata olustu (attempt={attempt}): {exc}"
					) from exc
				time.sleep(retry_delay)
				retry_delay *= 2

		raise EmbeddingServiceError("Embedding islemi tamamlanamadi.")

	async def embed_texts(self, texts: list[str]) -> list[list[float]]:
		"""Create embeddings for multiple texts with timeout control."""
		if not texts:
			return []

		async def embed_with_timeout(text: str) -> list[float]:
			return await asyncio.wait_for(
				asyncio.to_thread(self._embed_one_sync, text),
				timeout=self.config.timeout_sec,
			)

		tasks = [embed_with_timeout(text) for text in texts]

		try:
			return await asyncio.gather(*tasks)
		except asyncio.TimeoutError as exc:
			raise EmbeddingServiceError("Embedding islemi zaman asimina ugradi.") from exc
		except Exception as exc:  # noqa: BLE001
			message = str(exc).lower()
			api_model_unavailable = (
				"not found" in message
				or "not supported for embedcontent" in message
				or "embedcontent" in message
			)
			if not api_model_unavailable and isinstance(exc, EmbeddingServiceError):
				raise

			# Fallback: use local sentence-transformers model to keep pipeline operational.
			local_tasks = [
				asyncio.to_thread(self._embed_one_local_sync, text)
				for text in texts
			]
			try:
				return await asyncio.gather(*local_tasks)
			except Exception as local_exc:  # noqa: BLE001
				raise EmbeddingServiceError(
					f"Toplu embedding islemi basarisiz (API+local): {local_exc}"
				) from local_exc

	async def embed_query(self, query: str) -> list[float]:
		"""Create embedding for a query string."""
		if not query.strip():
			raise EmbeddingServiceError("Sorgu embedding icin bos olamaz.")

		results = await self.embed_texts([query])
		return results[0]
