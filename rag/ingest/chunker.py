"""
rag/ingest/chunker.py
======================
Step 4 of RAG Ingest: Text Chunking.

Splits cleaned text into overlapping chunks for embedding.

Strategies supported (TODO):
  - Fixed-size with overlap (default)
  - Sentence-boundary aware (better for RAG)
  - Semantic chunking (group semantically similar sentences)
  - Hierarchical chunking (parent + child chunks for re-ranking)

TODO: Implement using langchain_text_splitters.RecursiveCharacterTextSplitter.
TODO: Add chunk metadata (chunk_index, doc_id, page_number).
"""

import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    chunk_index: int
    document_id: str
    metadata: dict


async def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[TextChunk]:
    """
    Split text into overlapping chunks.

    TODO: Implement RecursiveCharacterTextSplitter with sentence boundary awareness.
    TODO: Assign chunk_id as uuid and track chunk_index.
    """
    logger.info("chunk_text called", document_id=document_id, text_length=len(text))
    raise NotImplementedError("Text chunker not yet implemented")
