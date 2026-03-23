"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _get_int(name: str, default: int) -> int:
	try:
		return int(os.getenv(name, str(default)))
	except ValueError:
		return default


@dataclass
class Settings:
	"""Application settings loaded from environment variables."""

	app_name: str
	app_env: str
	log_level: str
	api_v1_prefix: str
	cors_origins: list[str]
	upload_dir: Path
	chunk_size: int
	chunk_overlap: int
	max_pdf_size_mb: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Return cached application settings."""
	raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
	cors_origins = [item.strip() for item in raw_origins.split(",") if item.strip()]

	upload_dir = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
	upload_dir.mkdir(parents=True, exist_ok=True)

	return Settings(
		app_name=os.getenv("APP_NAME", "LegalDoc Navigator API"),
		app_env=os.getenv("APP_ENV", "development"),
		log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
		api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
		cors_origins=cors_origins,
		upload_dir=upload_dir,
		chunk_size=_get_int("PDF_CHUNK_SIZE", 1400),
		chunk_overlap=_get_int("PDF_CHUNK_OVERLAP", 250),
		max_pdf_size_mb=_get_int("PDF_MAX_FILE_SIZE_MB", 40),
	)
