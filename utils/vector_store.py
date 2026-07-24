"""Vector store management: two independent FAISS stores (Source A / Source B).

We never build a single unfiltered index across both sources. Every retrieval
call explicitly targets Store A or Store B, and results are only combined
after retrieval, preserving all metadata for traceability.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

DEFAULT_K_MIN = 4
DEFAULT_K_MAX = 6


def compute_documents_hash(chunks: List[Document]) -> str:
    """Stable hash of a list of chunks, used to detect whether the uploaded
    document(s) for a source have changed since the last embedding run."""
    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(chunk.page_content.encode("utf-8"))
        hasher.update(str(sorted(chunk.metadata.items())).encode("utf-8"))
    return hasher.hexdigest()


@dataclass
class SourceVectorStore:
    """Wraps a single FAISS index for one source (A or B) plus the hash of
    the chunks it was built from, so callers can skip re-embedding unchanged
    documents."""

    source_label: str
    documents_hash: str
    store: FAISS

    def retrieve(self, query: str, k: int = 6) -> List[Document]:
        k = max(DEFAULT_K_MIN, min(k, DEFAULT_K_MAX))
        return self.store.similarity_search(query, k=k)


def build_vector_store(
    chunks: List[Document],
    source_label: str,
    embedding_model: Optional[str] = None,
) -> SourceVectorStore:
    """Embed `chunks` (already tagged with source_label/filename/page/chunk_id
    metadata) into a fresh FAISS index."""
    if not chunks:
        raise ValueError(f"{source_label}: 임베딩할 청크가 없습니다.")

    embeddings = OpenAIEmbeddings(model=embedding_model or DEFAULT_EMBEDDING_MODEL)
    store = FAISS.from_documents(chunks, embeddings)
    doc_hash = compute_documents_hash(chunks)

    return SourceVectorStore(
        source_label=source_label,
        documents_hash=doc_hash,
        store=store,
    )


def get_or_build_vector_store(
    chunks: List[Document],
    source_label: str,
    cache: dict,
    cache_key: str,
    embedding_model: Optional[str] = None,
) -> SourceVectorStore:
    """Reuse a cached SourceVectorStore (typically from st.session_state) if
    the incoming chunks hash identically to what's already embedded;
    otherwise, embed fresh and update the cache in place.

    `cache` is expected to be a plain dict (e.g. st.session_state), and
    `cache_key` the key under which the SourceVectorStore is stored.
    """
    new_hash = compute_documents_hash(chunks)
    existing: Optional[SourceVectorStore] = cache.get(cache_key)

    if existing is not None and existing.documents_hash == new_hash:
        return existing

    built = build_vector_store(chunks, source_label=source_label, embedding_model=embedding_model)
    cache[cache_key] = built
    return built


def retrieve_from_both(
    store_a: SourceVectorStore,
    store_b: SourceVectorStore,
    query: str,
    k: int = 6,
) -> List[Document]:
    """Retrieve independently from Store A and Store B for the same query,
    then combine results after retrieval. Metadata is preserved untouched."""
    docs_a = store_a.retrieve(query, k=k)
    docs_b = store_b.retrieve(query, k=k)
    return docs_a + docs_b


def format_docs_for_prompt(docs: List[Document]) -> str:
    """Render retrieved chunks with explicit source markers so the LLM can
    (and must) cite them, e.g. [Source A | file.pdf | page 3 | A-001-04]."""
    lines = []
    for doc in docs:
        meta = doc.metadata
        marker = (
            f"[{meta.get('source_label', '?')} | {meta.get('filename', '?')} | "
            f"page {meta.get('page', '?')} | {meta.get('chunk_id', '?')}]"
        )
        lines.append(f"{marker}\n{doc.page_content}")
    return "\n\n---\n\n".join(lines)
