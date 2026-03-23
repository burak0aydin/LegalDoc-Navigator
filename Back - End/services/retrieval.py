"""Semantic retrieval and reranking services."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from database.vector_store import ChromaVectorStore, RetrievedChunk, VectorStoreError
from services.embedding import EmbeddingServiceError, GeminiEmbeddingService

try:
	from sentence_transformers import CrossEncoder
except Exception:  # noqa: BLE001
	CrossEncoder = None


class RetrievalServiceError(Exception):
	"""Raised when semantic retrieval pipeline fails."""


@dataclass
class RetrievalResult:
	"""Final retrieval output for downstream agent use."""

	chunk_id: str
	content: str
	metadata: dict[str, Any]
	similarity_score: float
	rerank_score: float | None = None


class RetrievalService:
	"""Semantic retrieval + optional cross-encoder reranking."""

	def __init__(
		self,
		embedding_service: GeminiEmbeddingService | None = None,
		vector_store: ChromaVectorStore | None = None,
	) -> None:
		self.embedding_service = embedding_service or GeminiEmbeddingService()
		self.vector_store = vector_store or ChromaVectorStore()
		self.reranker = self._load_reranker()

	def _load_reranker(self) -> CrossEncoder | None:
		"""Load reranker model if available, otherwise continue without it."""
		if CrossEncoder is None:
			return None

		model_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
		try:
			return CrossEncoder(model_name)
		except Exception:  # noqa: BLE001
			return None

	async def _rerank_chunks(
		self,
		query: str,
		chunks: list[RetrievedChunk],
		rerank_top_n: int,
	) -> list[RetrievalResult]:
		"""Apply cross-encoder reranking when model is available."""
		if not chunks:
			return []

		if self.reranker is None:
			return [
				RetrievalResult(
					chunk_id=chunk.chunk_id,
					content=chunk.content,
					metadata=chunk.metadata,
					similarity_score=chunk.score,
					rerank_score=None,
				)
				for chunk in chunks[:rerank_top_n]
			]

		pairs = [[query, chunk.content] for chunk in chunks]
		try:
			scores = await asyncio.to_thread(self.reranker.predict, pairs)
		except Exception as exc:  # noqa: BLE001
			raise RetrievalServiceError(f"Reranking asamasinda hata olustu: {exc}") from exc

		combined = list(zip(chunks, scores))
		combined.sort(key=lambda item: float(item[1]), reverse=True)

		reranked: list[RetrievalResult] = []
		for chunk, score in combined[:rerank_top_n]:
			reranked.append(
				RetrievalResult(
					chunk_id=chunk.chunk_id,
					content=chunk.content,
					metadata=chunk.metadata,
					similarity_score=chunk.score,
					rerank_score=float(score),
				)
			)
		return reranked

	async def search(
		self,
		query: str,
		top_k: int = 8,
		rerank_top_n: int = 5,
		filters: dict[str, Any] | None = None,
	) -> list[RetrievalResult]:
		"""Run end-to-end semantic retrieval for a user query."""
		if not query.strip():
			raise RetrievalServiceError("Sorgu metni bos olamaz.")

		try:
			query_embedding = await self.embedding_service.embed_query(query)
		except EmbeddingServiceError as exc:
			raise RetrievalServiceError(f"Sorgu embedding uretilemedi: {exc}") from exc

		try:
			raw_chunks = self.vector_store.similarity_search(
				query_embedding=query_embedding,
				top_k=max(top_k, rerank_top_n),
				filters=filters,
			)
		except VectorStoreError as exc:
			raise RetrievalServiceError(f"Vektor arama basarisiz: {exc}") from exc

		# Hybrid recall: add lexical matches for legal phrase-heavy queries.
		try:
			keyword_chunks = self.vector_store.keyword_search(
				query=query,
				top_k=max(top_k, rerank_top_n),
				filters=filters,
			)
		except VectorStoreError:
			keyword_chunks = []

		merged: dict[str, RetrievedChunk] = {}
		for chunk in raw_chunks:
			merged[chunk.chunk_id] = chunk
		for chunk in keyword_chunks:
			existing = merged.get(chunk.chunk_id)
			if existing is None:
				merged[chunk.chunk_id] = chunk
			else:
				# Keep richer score signal between semantic and lexical retrieval.
				existing.score = max(existing.score, chunk.score)

		candidate_chunks = list(merged.values())
		candidate_chunks.sort(key=lambda item: item.score, reverse=True)

		return await self._rerank_chunks(query, candidate_chunks, rerank_top_n=rerank_top_n)
