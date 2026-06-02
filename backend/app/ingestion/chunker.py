"""Chunking de páginas parseadas → chunks con índice global y página."""
from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.ingestion.parsers.base import ParsedPage


@dataclass
class Chunk:
    text: str
    chunk_index: int  # global, secuencial → preserva el orden del documento
    page: int | None


def chunk_pages(pages: list[ParsedPage]) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks: list[Chunk] = []
    idx = 0
    for page in pages:
        for piece in splitter.split_text(page.text):
            chunks.append(Chunk(text=piece, chunk_index=idx, page=page.page))
            idx += 1
    return chunks
