"""PDF ingestion, extraction, and chunking services."""

from __future__ import annotations

import asyncio
import hashlib
import re
from pathlib import Path

import fitz
from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class PDFProcessingError(Exception):
	"""Raised when PDF write/read/chunk operations fail."""


ALLOWED_EXTENSIONS = {".pdf"}
DEFAULT_MAX_FILE_SIZE_MB = 40
DEFAULT_PARSE_TIMEOUT_SEC = 90
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 500


def _sanitize_filename(filename: str) -> str:
	"""Sanitize incoming file names to avoid traversal and OS issues."""
	cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename.strip())
	return cleaned or "document.pdf"


def _normalize_extracted_text(raw_text: str) -> str:
	"""Normalize extracted text while preserving legal section boundaries."""
	text = raw_text.replace("\r", "\n")
	text = re.sub(r"\n{3,}", "\n\n", text)
	text = re.sub(r"[\t ]+", " ", text)
	return text.strip()


def _extract_text_sync(pdf_path: Path) -> str:
	"""Blocking PDF text extraction, intended to run in thread executor."""
	pages: list[str] = []

	with fitz.open(pdf_path) as doc:
		for page in doc:
			pages.append(page.get_text("text"))

	return _normalize_extracted_text("\n\n".join(pages))


async def save_uploaded_pdf(
	upload_file: UploadFile,
	destination_dir: str | Path,
	max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
) -> tuple[Path, str]:
	"""Persist uploaded PDF securely to disk.

	Raises:
		PDFProcessingError: If input file is invalid or write fails.
	"""

	if upload_file.filename is None:
		raise PDFProcessingError("Yuklenen dosya ad bilgisi icermiyor.")

	extension = Path(upload_file.filename).suffix.lower()
	if extension not in ALLOWED_EXTENSIONS:
		raise PDFProcessingError("Sadece PDF uzantili dosyalar kabul edilir.")

	try:
		file_bytes = await upload_file.read()
	except Exception as exc:
		raise PDFProcessingError("Dosya okunamadi.") from exc

	if not file_bytes:
		raise PDFProcessingError("Bos dosya yuklenemez.")

	max_size = max_file_size_mb * 1024 * 1024
	if len(file_bytes) > max_size:
		raise PDFProcessingError(
			f"Dosya boyutu limiti asildi. En fazla {max_file_size_mb} MB desteklenir."
		)

	target_dir = Path(destination_dir)
	target_dir.mkdir(parents=True, exist_ok=True)

	safe_name = _sanitize_filename(upload_file.filename)
	file_hash = hashlib.sha256(file_bytes).hexdigest()
	target_path = target_dir / f"{file_hash[:12]}_{safe_name}"

	try:
		if not target_path.exists():
			await asyncio.to_thread(target_path.write_bytes, file_bytes)
	except Exception as exc:
		raise PDFProcessingError("Yuklenen PDF diske kaydedilemedi.") from exc

	return target_path, file_hash


async def extract_text_from_pdf(
	pdf_path: str | Path,
	timeout_sec: int = DEFAULT_PARSE_TIMEOUT_SEC,
) -> str:
	"""Extract text from PDF file using PyMuPDF.

	Raises:
		PDFProcessingError: If file cannot be parsed or extraction times out.
	"""

	path = Path(pdf_path)
	if not path.exists():
		raise PDFProcessingError(f"PDF dosyasi bulunamadi: {path}")

	try:
		text = await asyncio.wait_for(
			asyncio.to_thread(_extract_text_sync, path),
			timeout=timeout_sec,
		)
	except asyncio.TimeoutError as exc:
		raise PDFProcessingError("PDF metin cikarma islemi zaman asimina ugradi.") from exc
	except Exception as exc:
		raise PDFProcessingError("PDF metni okunurken beklenmeyen hata olustu.") from exc

	if not text:
		raise PDFProcessingError("PDF iceriginden metin cikartilamadi.")

	return text


def chunk_legal_text(
	text: str,
	source_name: str,
	chunk_size: int = DEFAULT_CHUNK_SIZE,
	chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
	"""Split legal text into context-preserving chunks for downstream RAG."""

	if not text or not text.strip():
		raise PDFProcessingError("Chunkleme icin gecerli metin bulunamadi.")

	# Improve article boundary detection so legal clauses are less likely to split mid-rule.
	text = re.sub(r"(?<!\n)(Madde\s+\d+\s*-)", r"\n\1", text)

	splitter = RecursiveCharacterTextSplitter(
		chunk_size=chunk_size,
		chunk_overlap=chunk_overlap,
		separators=[
			"\n\n",
			"\n",
			" ",
			"",
		],
	)

	chunks = splitter.split_text(text)
	return [
		Document(
			page_content=chunk,
			metadata={
				"source": source_name,
				"chunk_index": index,
				"total_chunks": len(chunks),
			},
		)
		for index, chunk in enumerate(chunks)
	]


async def ingest_pdf_to_chunks(
	upload_file: UploadFile,
	destination_dir: str | Path,
	max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
	chunk_size: int = DEFAULT_CHUNK_SIZE,
	chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> tuple[Path, str, list[Document]]:
	"""End-to-end helper for upload -> extract -> chunk pipeline."""

	stored_path, file_hash = await save_uploaded_pdf(
		upload_file,
		destination_dir,
		max_file_size_mb=max_file_size_mb,
	)
	text = await extract_text_from_pdf(stored_path)
	chunks = chunk_legal_text(text, source_name=stored_path.name, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
	return stored_path, file_hash, chunks
