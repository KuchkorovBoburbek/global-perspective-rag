"""Smoke tests: verify every module imports cleanly with current supported
LangChain package layout. These do NOT call any external API."""

import importlib

import pytest

MODULES = [
    "utils.document_loader",
    "utils.vector_store",
    "utils.rag_chain",
    "utils.report_generator",
    "prompts.comparison_prompt",
    "prompts.qa_prompt",
    "prompts.executive_prompt",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    module = importlib.import_module(module_name)
    assert module is not None


def test_langchain_core_imports():
    from langchain_core.documents import Document  # noqa: F401
    from langchain_core.prompts import ChatPromptTemplate  # noqa: F401
    from langchain_core.runnables import RunnableLambda  # noqa: F401


def test_langchain_text_splitters_import():
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: F401


def test_langchain_community_import():
    from langchain_community.vectorstores import FAISS  # noqa: F401


def test_langchain_openai_import():
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # noqa: F401


def test_model_name_reads_from_env(monkeypatch):
    """OPENAI_MODEL must be read from the environment, with a safe
    fallback only when unset (per project requirements)."""
    from utils.rag_chain import DEFAULT_OPENAI_MODEL, get_model_name

    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert get_model_name() == DEFAULT_OPENAI_MODEL

    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    assert get_model_name() == "gpt-4o"
