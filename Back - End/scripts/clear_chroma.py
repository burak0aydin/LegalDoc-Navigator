"""Utility script to remove local ChromaDB persistence directory."""

from __future__ import annotations

import shutil
from pathlib import Path


def clear_chroma_directory() -> None:
    chroma_dir = Path("./data/chroma")
    if chroma_dir.exists() and chroma_dir.is_dir():
        shutil.rmtree(chroma_dir)
        print("Chroma klasoru temizlendi: ./data/chroma")
    else:
        print("Chroma klasoru bulunamadi: ./data/chroma")


if __name__ == "__main__":
    clear_chroma_directory()
