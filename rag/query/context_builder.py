"""
rag/query/context_builder.py
=============================
Step 4 of RAG Query: Context Building.

Assembles the final prompt context from reranked chunks.

Responsibilities:
  - Format chunks into a readable context block
  - Apply token budget (ensure context fits LLM window)
  - Add source citations for each chunk
  - Structure context for the LLM prompt template

TODO: Implement context formatting with token counting (tiktoken).
TODO: Add source citation formatting.
TODO: Implement context compression for long documents (LLMLingua or similar).
"""

import structlog

logger = structlog.get_logger(__name__)


async def build_context(
    query: str,
    chunks: list[dict],
    max_tokens: int = 3000,
) -> dict:
    """
    Build the final LLM prompt context from reranked chunks.

    Returns:
        dict with keys:
          - context_text: str (formatted context for the LLM)
          - sources: list[dict] (citations for the response)
          - token_count: int
    """
    logger.info("build_context called", chunk_count=len(chunks))
    
    # 1. Format chunks and keep track of source files
    sources = []
    formatted_blocks = []
    
    # For token calculation fallback
    total_estimated_tokens = 0
    
    # Try importing tiktoken for exact tokens, fallback to estimation
    tokenizer = None
    try:
        import tiktoken
        tokenizer = tiktoken.get_encoding("cl100k_base")
    except ImportError:
        pass

    for i, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "")
        meta = chunk.get("metadata", {})
        doc_id = meta.get("document_id", "unknown")
        filename = meta.get("filename", "unknown")
        chunk_idx = meta.get("chunk_index", 0)

        # Block text
        block = f"[Source {i}]: {filename} (Chunk {chunk_idx})\nContent:\n{text}\n"
        
        # Count tokens for this block
        if tokenizer:
            block_tokens = len(tokenizer.encode(block))
        else:
            # Heuristic estimation: ~4 chars per token
            block_tokens = int(len(block) / 4)

        if total_estimated_tokens + block_tokens > max_tokens:
            logger.info("Context length exceeded token budget, stopping chunk inclusion", index=i)
            break

        formatted_blocks.append(block)
        total_estimated_tokens += block_tokens

        # Record citation
        sources.append({
            "citation_index": i,
            "document_id": doc_id,
            "filename": filename,
            "chunk_index": chunk_idx,
        })

    context_text = "\n---\n".join(formatted_blocks)

    return {
        "context_text": context_text,
        "sources": sources,
        "token_count": total_estimated_tokens,
    }

