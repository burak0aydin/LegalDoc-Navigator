"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router as api_router
from core.config import get_settings
from core.logger import configure_logging


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
	title=settings.app_name,
	version="0.1.0",
	description="LegalDoc Navigator backend API",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
	"""Log request duration and status code for observability."""
	start_time = time.perf_counter()
	response = await call_next(request)
	elapsed_ms = (time.perf_counter() - start_time) * 1000
	logger.info(
		"request completed | method=%s path=%s status=%s duration_ms=%.2f",
		request.method,
		request.url.path,
		response.status_code,
		elapsed_ms,
	)
	return response


@app.get("/health")
async def health_check() -> dict[str, str]:
	"""Simple health endpoint for runtime checks."""
	return {"status": "ok", "environment": settings.app_env}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
	request: Request,
	exc: RequestValidationError,
) -> JSONResponse:
	"""Return structured 422 errors for invalid request payloads."""
	logger.warning("Validation error on %s: %s", request.url.path, exc)
	return JSONResponse(
		status_code=422,
		content={
			"error": "ValidationError",
			"message": "Istek dogrulama hatasi.",
			"details": exc.errors(),
		},
	)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
	"""Catch-all handler for unexpected server errors."""
	logger.exception("Unhandled exception on %s", request.url.path)
	return JSONResponse(
		status_code=500,
		content={
			"error": "InternalServerError",
			"message": "Sunucu tarafinda beklenmeyen bir hata olustu.",
			"details": str(exc),
		},
	)
