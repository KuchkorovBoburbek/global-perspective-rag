"""Minimal tests for utils/document_loader.py.

These tests do not require any API keys — they only exercise local file
parsing, chunking, and metadata logic.
"""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from utils.document_loader import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    chunk_documents,
    load_file_to_documents,
    process_uploaded_files,
)


def _txt_file(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


def _blank_pdf_file() -> io.BytesIO:
    """A syntactically valid PDF with a blank page (no text layer) — used to
    simulate a scanned/image-only PDF for the empty-document test."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


def test_txt_loading_basic():
    docs = load_file_to_documents(
        _txt_file("Hello world.   \n\n\n\nThis is a test."),
        filename="sample.txt",
        source_label="Source A",
        language="English",
    )
    assert len(docs) == 1
    assert "Hello world." in docs[0].page_content
    # repeated whitespace / blank lines collapsed
    assert "\n\n\n" not in docs[0].page_content


def test_metadata_presence():
    docs = load_file_to_documents(
        _txt_file("Some content for metadata check."),
        filename="meta.txt",
        source_label="Source A",
        language="한국어",
    )
    meta = docs[0].metadata
    for key in ("source_label", "filename", "language", "page"):
        assert key in meta
    assert meta["source_label"] == "Source A"
    assert meta["filename"] == "meta.txt"
    assert meta["language"] == "한국어"
    assert meta["page"] == 1


def test_chunk_id_format_and_source_separation():
    docs_a = load_file_to_documents(
        _txt_file("A" * 2000), filename="a.txt", source_label="Source A", language="English"
    )
    docs_b = load_file_to_documents(
        _txt_file("B" * 2000), filename="b.txt", source_label="Source B", language="한국어"
    )

    chunks_a = chunk_documents(docs_a, source_letter="A")
    chunks_b = chunk_documents(docs_b, source_letter="B")

    assert len(chunks_a) > 1  # 2000 chars with chunk_size=900 should split
    for c in chunks_a:
        assert c.metadata["chunk_id"].startswith("A-")
        assert c.metadata["source_label"] == "Source A"

    for c in chunks_b:
        assert c.metadata["chunk_id"].startswith("B-")
        assert c.metadata["source_label"] == "Source B"

    # Sources never mix
    a_ids = {c.metadata["chunk_id"] for c in chunks_a}
    b_ids = {c.metadata["chunk_id"] for c in chunks_b}
    assert a_ids.isdisjoint(b_ids)


def test_unsupported_extension_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        load_file_to_documents(
            _txt_file("irrelevant"),
            filename="not_supported.docx",
            source_label="Source A",
            language="English",
        )


def test_empty_txt_raises():
    with pytest.raises(EmptyDocumentError):
        load_file_to_documents(
            _txt_file("   \n\n   "),
            filename="empty.txt",
            source_label="Source A",
            language="English",
        )


def test_empty_scanned_pdf_raises_korean_message():
    with pytest.raises(EmptyDocumentError) as exc_info:
        load_file_to_documents(
            _blank_pdf_file(),
            filename="scanned.pdf",
            source_label="Source A",
            language="English",
        )
    assert "텍스트를 추출할 수 없습니다" in str(exc_info.value)


def test_process_uploaded_files_end_to_end():
    files = [_txt_file("Line one.\n\nLine two about AI regulation." * 20)]
    processed = process_uploaded_files(
        files=files,
        filenames=["doc.txt"],
        source_label="Source A",
        source_letter="A",
        language="English",
    )
    assert processed.total_pages == 1
    assert len(processed.chunks) >= 1
    assert processed.filenames == ["doc.txt"]
