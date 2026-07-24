"""LCEL-based RAG chains: comparative analysis, cross-language Q&A, and
executive report generation.

This project runs entirely on OpenAI APIs (chat + embeddings). The chat
model id is never hardcoded. It is read from the OPENAI_MODEL environment
variable and falls back to a safe, currently supported default only when
that variable is not set, so operators can swap models without touching
this file.
"""

from __future__ import annotations

import os
from typing import List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI

from prompts.comparison_prompt import comparison_prompt
from prompts.executive_prompt import executive_prompt
from prompts.qa_prompt import qa_prompt
from utils.vector_store import (
    SourceVectorStore,
    format_docs_for_prompt,
    retrieve_from_both,
)

# Safe, currently-supported default. Override via the OPENAI_MODEL env var
# without touching any application code.
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL


def build_llm(temperature: float = 0.2, max_tokens: int = 4096) -> ChatOpenAI:
    return ChatOpenAI(
        model=get_model_name(),
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _retrieve_pair(
    store_a: SourceVectorStore,
    store_b: SourceVectorStore,
    query: str,
    k: int = 6,
) -> dict:
    docs_a: List[Document] = store_a.retrieve(query, k=k)
    docs_b: List[Document] = store_b.retrieve(query, k=k)
    return {
        "source_a_context": format_docs_for_prompt(docs_a),
        "source_b_context": format_docs_for_prompt(docs_b),
        "source_a_docs": docs_a,
        "source_b_docs": docs_b,
    }


def build_comparison_chain(store_a: SourceVectorStore, store_b: SourceVectorStore, k: int = 6):
    """Comparative Analysis Chain (A). Returns a dict with the rendered
    Korean markdown report plus the raw retrieved docs for citation display."""
    llm = build_llm(temperature=0.2, max_tokens=4096)

    def _run(inputs: dict) -> dict:
        topic = inputs["topic"]
        retrieved = _retrieve_pair(store_a, store_b, topic, k=k)
        chain = comparison_prompt | llm | StrOutputParser()
        report = chain.invoke(
            {
                "topic": topic,
                "source_a_context": retrieved["source_a_context"],
                "source_b_context": retrieved["source_b_context"],
            }
        )
        return {
            "report": report,
            "source_a_docs": retrieved["source_a_docs"],
            "source_b_docs": retrieved["source_b_docs"],
        }

    return RunnableLambda(_run)


def build_qa_chain(store_a: SourceVectorStore, store_b: SourceVectorStore, k: int = 6):
    """Cross-Language Q&A Chain (B)."""
    llm = build_llm(temperature=0.2, max_tokens=3072)

    def _run(inputs: dict) -> dict:
        question = inputs["question"]
        output_language = inputs.get("output_language", "한국어")
        retrieved = _retrieve_pair(store_a, store_b, question, k=k)

        prompt_filled = qa_prompt.partial(output_language=output_language)
        chain = prompt_filled | llm | StrOutputParser()
        answer = chain.invoke(
            {
                "question": question,
                "source_a_context": retrieved["source_a_context"],
                "source_b_context": retrieved["source_b_context"],
            }
        )
        return {
            "answer": answer,
            "source_a_docs": retrieved["source_a_docs"],
            "source_b_docs": retrieved["source_b_docs"],
        }

    return RunnableLambda(_run)


def build_executive_chain(
    store_a: SourceVectorStore,
    store_b: SourceVectorStore,
    topic: str,
    file_count: int,
    chunk_count: int,
    languages: str,
    k: int = 6,
):
    """Executive Report Chain (C)."""
    llm = build_llm(temperature=0.15, max_tokens=2048)

    def _run(_inputs: dict) -> dict:
        retrieved = _retrieve_pair(store_a, store_b, topic, k=k)
        prompt_filled = executive_prompt.partial(
            topic=topic,
            file_count=str(file_count),
            chunk_count=str(chunk_count),
            languages=languages,
        )
        chain = prompt_filled | llm | StrOutputParser()
        report = chain.invoke(
            {
                "source_a_context": retrieved["source_a_context"],
                "source_b_context": retrieved["source_b_context"],
            }
        )
        return {
            "report": report,
            "source_a_docs": retrieved["source_a_docs"],
            "source_b_docs": retrieved["source_b_docs"],
        }

    return RunnableLambda(_run)
