"""Route definitions for document upload and query endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agent.graph import get_agent_graph
from core.config import get_settings
from database.vector_store import ChromaVectorStore, VectorStoreError
from services.embedding import EmbeddingServiceError, GeminiEmbeddingService
from services.pdf_processor import PDFProcessingError, ingest_pdf_to_chunks


logger = logging.getLogger(__name__)
router = APIRouter(tags=["legaldoc-navigator"])


class UploadResponse(BaseModel):
	"""Response schema for successful PDF ingestion."""

	message: str
	file_name: str
	stored_path: str
	chunks_count: int
	indexed_chunk_ids: list[str]


class QueryRequest(BaseModel):
	"""Request schema for agent query execution."""

	query: str = Field(min_length=3, description="User's legal question")
	max_attempts: int = Field(default=2, ge=1, le=5)


class QueryResponse(BaseModel):
	"""Response schema for agent query execution."""

	answer_markdown: str
	attempts: int
	relevant_results_count: int
	errors: list[str] = Field(default_factory=list)
	metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/document/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
	"""Upload, process, embed, and index a legal PDF document."""
	settings = get_settings()

	try:
		stored_path, chunks = await ingest_pdf_to_chunks(
			upload_file=file,
			destination_dir=settings.upload_dir,
			chunk_size=settings.chunk_size,
			chunk_overlap=settings.chunk_overlap,
		)
	except PDFProcessingError as exc:
		logger.warning("PDF processing failed: %s", exc)
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:  # noqa: BLE001
		logger.exception("Unexpected upload pipeline failure")
		raise HTTPException(status_code=500, detail="PDF isleme asamasinda beklenmeyen hata olustu.") from exc

	try:
		embedding_service = GeminiEmbeddingService()
		embeddings = await embedding_service.embed_texts([chunk.page_content for chunk in chunks])
	except EmbeddingServiceError as exc:
		logger.exception("Embedding generation failed")
		raise HTTPException(status_code=500, detail=f"Embedding olusturulamadi: {exc}") from exc

	try:
		vector_store = ChromaVectorStore()
		indexed_chunk_ids = vector_store.upsert_documents(
			documents=chunks,
			embeddings=embeddings,
			source_id=stored_path.stem,
		)
	except VectorStoreError as exc:
		logger.exception("Vector DB write failed")
		raise HTTPException(status_code=500, detail=f"Vektor veritabani yazma hatasi: {exc}") from exc

	return UploadResponse(
		message="PDF basariyla yuklendi, islenip indekslendi.",
		file_name=file.filename or "unknown.pdf",
		stored_path=str(stored_path),
		chunks_count=len(chunks),
		indexed_chunk_ids=indexed_chunk_ids,
	)


@router.post("/agent/query", response_model=QueryResponse)
async def agent_query(request: QueryRequest) -> QueryResponse:
	"""Execute LangGraph legal analysis flow and return markdown answer."""
	graph = get_agent_graph()
	initial_state: dict[str, Any] = {
		"query": request.query,
		"attempts": 0,
		"max_attempts": request.max_attempts,
		"errors": [],
	}

	try:
		if hasattr(graph, "ainvoke"):
			result_state = await graph.ainvoke(initial_state)
		else:
			result_state = await asyncio.to_thread(graph.invoke, initial_state)
	except HTTPException:
		raise
	except Exception as exc:  # noqa: BLE001
		logger.exception("Agent query flow failed")
		raise HTTPException(status_code=500, detail=f"Ajan sorgu akisi basarisiz: {exc}") from exc

	answer_markdown = result_state.get("answer_markdown", "") if isinstance(result_state, dict) else ""
	if not answer_markdown:
		raise HTTPException(status_code=500, detail="Ajan gecerli bir rapor uretemedi.")

	relevant_results = result_state.get("relevant_results", []) if isinstance(result_state, dict) else []
	errors = result_state.get("errors", []) if isinstance(result_state, dict) else []
	attempts = int(result_state.get("attempts", 0)) if isinstance(result_state, dict) else 0

	return QueryResponse(
		answer_markdown=answer_markdown,
		attempts=attempts,
		relevant_results_count=len(relevant_results),
		errors=errors,
		metadata={
			"query": request.query,
			"max_attempts": request.max_attempts,
		},
	)
