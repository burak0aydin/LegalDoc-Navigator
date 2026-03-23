"""Persistent vector store abstractions (ChromaDB/FAISS)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
	"""Raised for vector database operation failures."""


@dataclass
class RetrievedChunk:
	"""Represents a retrieved chunk from vector store search."""

	chunk_id: str
	content: str
	metadata: dict[str, Any]
	score: float


@dataclass
class ChromaConfig:
	"""Configuration options for ChromaDB persistence."""

	persist_dir: str = "./data/chroma"
	collection_name: str = "legal_documents"


def load_chroma_config_from_env() -> ChromaConfig:
	"""Load ChromaDB settings from environment variables."""
	return ChromaConfig(
		persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
		collection_name=os.getenv("CHROMA_COLLECTION_NAME", "legal_documents"),
	)


class ChromaVectorStore:
	"""Minimal ChromaDB wrapper for document upsert and retrieval."""

	def __init__(self, config: ChromaConfig | None = None) -> None:
		self.config = config or load_chroma_config_from_env()
		persist_path = Path(self.config.persist_dir)
		persist_path.mkdir(parents=True, exist_ok=True)

		self.client = chromadb.PersistentClient(path=str(persist_path))
		self.collection = self.client.get_or_create_collection(
			name=self.config.collection_name,
			metadata={"hnsw:space": "cosine"},
		)

	def _recreate_collection(self) -> None:
		"""Recreate collection when dimensionality drift occurs."""
		try:
			self.client.delete_collection(name=self.config.collection_name)
		except Exception:
			# Best-effort delete; create_collection below is authoritative.
			pass

		self.collection = self.client.get_or_create_collection(
			name=self.config.collection_name,
			metadata={"hnsw:space": "cosine"},
		)

	def upsert_documents(
		self,
		documents: list[Document],
		embeddings: list[list[float]],
		source_id: str,
		filename: str | None = None,
	) -> list[str]:
		"""Upsert document chunks and embeddings into persistent ChromaDB."""
		if len(documents) != len(embeddings):
			raise VectorStoreError("Dokuman ve embedding sayilari esit olmali.")

		ids: list[str] = []
		payload_documents: list[str] = []
		payload_metadatas: list[dict[str, Any]] = []

		for index, doc in enumerate(documents):
			chunk_id = f"{source_id}:{index}"
			ids.append(chunk_id)
			payload_documents.append(doc.page_content)
			metadata = {**doc.metadata, "source_id": source_id}
			if filename:
				metadata["filename"] = filename
			payload_metadatas.append(metadata)

		try:
			# Keep source_id idempotent: remove previous chunks before rewriting.
			self.collection.delete(where={"source_id": source_id})
		except Exception:
			# Deletion is best-effort; continue to upsert.
			pass

		try:
			self.collection.upsert(
				ids=ids,
				documents=payload_documents,
				metadatas=payload_metadatas,
				embeddings=embeddings,
			)
		except Exception as exc:  # noqa: BLE001
			message = str(exc).lower()
			dimension_mismatch = "does not match collection dimensionality" in message
			if not dimension_mismatch:
				raise VectorStoreError(f"ChromaDB upsert hatasi: {exc}") from exc

			logger.warning("Chroma dimension mismatch detected. Recreating collection and retrying upsert.")
			try:
				self._recreate_collection()
				self.collection.upsert(
					ids=ids,
					documents=payload_documents,
					metadatas=payload_metadatas,
					embeddings=embeddings,
				)
			except Exception as retry_exc:  # noqa: BLE001
				raise VectorStoreError(f"ChromaDB upsert hatasi: {retry_exc}") from retry_exc

		return ids

	def source_exists(self, source_id: str) -> bool:
		"""Check if any chunks already exist for a source_id."""
		try:
			payload = self.collection.get(where={"source_id": source_id}, include=[])
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"Kaynak varlik kontrolu hatasi: {exc}") from exc

		ids = payload.get("ids", [])
		return bool(ids)

	def filename_exists(self, filename: str) -> bool:
		"""Check if any chunks already exist for a filename."""
		try:
			payload = self.collection.get(where={"filename": filename}, include=[])
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"Dosya adi varlik kontrolu hatasi: {exc}") from exc

		ids = payload.get("ids", [])
		return bool(ids)

	def get_source_chunk_ids(self, source_id: str) -> list[str]:
		"""Return existing chunk IDs for a source if present."""
		try:
			payload = self.collection.get(where={"source_id": source_id}, include=[])
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"Kaynak chunk id okuma hatasi: {exc}") from exc

		return list(payload.get("ids", []))

	def get_filename_chunk_ids(self, filename: str) -> list[str]:
		"""Return existing chunk IDs for a filename if present."""
		try:
			payload = self.collection.get(where={"filename": filename}, include=[])
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"Dosya adi chunk id okuma hatasi: {exc}") from exc

		return list(payload.get("ids", []))

	def get_collection_dimension(self) -> int | None:
		"""Return current collection embedding dimension when available."""
		try:
			payload = self.collection.peek(limit=1)
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"Koleksiyon boyut bilgisi okunamadi: {exc}") from exc

		embeddings = payload.get("embeddings") if payload else None
		if embeddings is None:
			return None
		try:
			if len(embeddings) == 0:
				return None
		except TypeError:
			return None

		first = embeddings[0]
		if first is None:
			return None
		try:
			return len(first)
		except TypeError:
			return None

	def similarity_search(
		self,
		query_embedding: list[float],
		top_k: int = 8,
		filters: dict[str, Any] | None = None,
	) -> list[RetrievedChunk]:
		"""Run vector similarity search and return normalized chunk results."""
		if not query_embedding:
			raise VectorStoreError("Sorgu embedding bos olamaz.")

		try:
			results = self.collection.query(
				query_embeddings=[query_embedding],
				n_results=top_k,
				where=filters,
			)
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"ChromaDB similarity search hatasi: {exc}") from exc

		result_ids = results.get("ids", [[]])[0]
		result_docs = results.get("documents", [[]])[0]
		result_metas = results.get("metadatas", [[]])[0]
		result_distances = results.get("distances", [[]])[0]

		chunks: list[RetrievedChunk] = []
		for idx, chunk_id in enumerate(result_ids):
			distance = float(result_distances[idx]) if idx < len(result_distances) else 0.0
			score = 1.0 - distance
			chunks.append(
				RetrievedChunk(
					chunk_id=chunk_id,
					content=result_docs[idx] if idx < len(result_docs) else "",
					metadata=result_metas[idx] if idx < len(result_metas) else {},
					score=score,
				)
			)

		return chunks

	def keyword_search(
		self,
		query: str,
		top_k: int = 8,
		filters: dict[str, Any] | None = None,
	) -> list[RetrievedChunk]:
		"""Run lexical keyword search over stored chunks for exact-term recall.

		This method complements embedding search when model quality or language
		coverage is limited.
		"""
		if not query.strip():
			return []

		def tokenize(text: str) -> set[str]:
			tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
			return {token for token in tokens if len(token) >= 3}

		query_tokens = tokenize(query)
		if not query_tokens:
			return []

		try:
			payload = self.collection.get(where=filters, include=["documents", "metadatas"])
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"ChromaDB keyword search hatasi: {exc}") from exc

		ids = payload.get("ids", [])
		docs = payload.get("documents", [])
		metas = payload.get("metadatas", [])

		scored: list[tuple[str, str, dict[str, Any], float]] = []
		for idx, chunk_id in enumerate(ids):
			content = docs[idx] if idx < len(docs) and docs[idx] else ""
			if not content:
				continue
			content_tokens = tokenize(content)
			overlap = len(query_tokens.intersection(content_tokens))
			if overlap <= 0:
				continue
			score = overlap / max(len(query_tokens), 1)
			metadata = metas[idx] if idx < len(metas) and metas[idx] else {}
			scored.append((chunk_id, content, metadata, float(score)))

		scored.sort(key=lambda item: item[3], reverse=True)
		results: list[RetrievedChunk] = []
		for chunk_id, content, metadata, score in scored[:top_k]:
			results.append(
				RetrievedChunk(
					chunk_id=chunk_id,
					content=content,
					metadata=metadata,
					score=score,
				)
			)

		return results
