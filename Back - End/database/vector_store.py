"""Persistent vector store abstractions (ChromaDB/FAISS)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.documents import Document


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

	def upsert_documents(
		self,
		documents: list[Document],
		embeddings: list[list[float]],
		source_id: str,
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
			payload_metadatas.append({**doc.metadata, "source_id": source_id})

		try:
			self.collection.upsert(
				ids=ids,
				documents=payload_documents,
				metadatas=payload_metadatas,
				embeddings=embeddings,
			)
		except Exception as exc:  # noqa: BLE001
			raise VectorStoreError(f"ChromaDB upsert hatasi: {exc}") from exc

		return ids

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
