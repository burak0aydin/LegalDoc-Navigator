"""Centralized logging configuration."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
	"""Configure root logger once for API lifecycle and request handlers."""
	if logging.getLogger().handlers:
		logging.getLogger().setLevel(level)
		return

	logging.basicConfig(
		level=level,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)
