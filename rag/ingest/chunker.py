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

import uuid
import structlog
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
    """
    logger.info("chunk_text called", document_id=document_id, text_length=len(text))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    raw_chunks = splitter.split_text(text)
    
    chunks = []
    for index, raw_chunk in enumerate(raw_chunks):
        chunk_id = str(uuid.uuid4())
        chunks.append(
            TextChunk(
                chunk_id=chunk_id,
                text=raw_chunk,
                chunk_index=index,
                document_id=document_id,
                metadata={
                    "chunk_index": index,
                    "document_id": document_id,
                },
            )
        )

    logger.info("chunking complete", document_id=document_id, chunk_count=len(chunks))
    return chunks

