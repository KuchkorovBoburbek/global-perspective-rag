"""Document loading and chunking for the Perspective Analyzer.

Handles PDF and TXT ingestion, per-source metadata tagging, and chunking.
Source A and Source B are always processed independently and never mixed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import BinaryIO, List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

# Minimum number of extracted characters per PDF page below which we treat
# the page as "empty" (e.g. a scanned image with no embedded text layer).
MIN_CHARS_PER_PAGE = 20

EMPTY_PDF_ERROR_KO = (
    "❌ 텍스트를 추출할 수 없습니다. 이 PDF는 스캔된 이미지로만 구성되어 있거나 "
    "내용이 비어 있는 것으로 보입니다. 현재 MVP는 OCR을 지원하지 않으므로, "
    "텍스트가 포함된 PDF 또는 TXT 파일을 업로드해 주세요."
)


class UnsupportedFileTypeError(ValueError):
    """Raised when a file extension is not .pdf or .txt."""


class EmptyDocumentError(ValueError):
    """Raised when a document contains no extractable text (e.g. scanned PDF)."""


def _normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace while preserving paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _validate_extension(filename: str) -> str:
    lower = filename.lower()
    for ext in SUPPORTED_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    raise UnsupportedFileTypeError(
        f"지원하지 않는 파일 형식입니다: '{filename}'. "
        f"PDF 또는 TXT 파일만 업로드할 수 있습니다."
    )


def _load_pdf_pages(file: BinaryIO, filename: str) -> List[str]:
    """Return normalized text for each page of a PDF. Raises EmptyDocumentError
    if every page is effectively empty (e.g. scanned/image-only PDF)."""
    reader = PdfReader(file)
    pages_text: List[str] = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        pages_text.append(_normalize_whitespace(raw))

    if not pages_text or all(len(p) < MIN_CHARS_PER_PAGE for p in pages_text):
        raise EmptyDocumentError(EMPTY_PDF_ERROR_KO)

    return pages_text


def _load_txt(file: BinaryIO, filename: str) -> str:
    raw_bytes = file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="ignore")
    normalized = _normalize_whitespace(text)
    if not normalized:
        raise EmptyDocumentError(
            "❌ 텍스트 파일이 비어 있습니다. 내용이 포함된 TXT 파일을 업로드해 주세요."
        )
    return normalized


def load_file_to_documents(
    file: BinaryIO,
    filename: str,
    source_label: str,
    language: str,
) -> List[Document]:
    """Load a single uploaded file (PDF or TXT) into one Document per page
    (PDF) or one Document (TXT), tagged with source metadata.

    Args:
        file: file-like object opened in binary mode.
        filename: original filename, used for extension detection + metadata.
        source_label: "Source A" or "Source B".
        language: language code/label selected or detected for this file.

    Raises:
        UnsupportedFileTypeError: if extension is not .pdf/.txt
        EmptyDocumentError: if no text could be extracted (Korean message).
    """
    ext = _validate_extension(filename)
    documents: List[Document] = []

    if ext == ".pdf":
        pages = _load_pdf_pages(file, filename)
        for i, page_text in enumerate(pages, start=1):
            if len(page_text) < MIN_CHARS_PER_PAGE:
                continue
            documents.append(
                Document(
                    page_content=page_text,
                    metadata={
                        "source_label": source_label,
                        "filename": filename,
                        "language": language,
                        "page": i,
                    },
                )
            )
        if not documents:
            raise EmptyDocumentError(EMPTY_PDF_ERROR_KO)
    else:  # .txt
        text = _load_txt(file, filename)
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source_label": source_label,
                    "filename": filename,
                    "language": language,
                    "page": 1,
                },
            )
        )

    return documents


def make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
    )


def chunk_documents(documents: List[Document], source_letter: str) -> List[Document]:
    """Split page/file-level Documents into chunks, assigning a stable
    chunk_id of the form '<A|B>-<file_index:03d>-<chunk_index:02d>'.

    source_letter should be "A" or "B".
    """
    splitter = make_splitter()
    chunks: List[Document] = []

    # Group by filename so file_index is stable and human-legible.
    filenames_seen: List[str] = []
    for doc in documents:
        fname = doc.metadata["filename"]
        if fname not in filenames_seen:
            filenames_seen.append(fname)

    per_file_chunk_counter = {fname: 0 for fname in filenames_seen}

    for doc in documents:
        fname = doc.metadata["filename"]
        file_index = filenames_seen.index(fname) + 1
        split_docs = splitter.split_documents([doc])
        for split_doc in split_docs:
            per_file_chunk_counter[fname] += 1
            chunk_idx = per_file_chunk_counter[fname]
            chunk_id = f"{source_letter}-{file_index:03d}-{chunk_idx:02d}"
            split_doc.metadata["chunk_id"] = chunk_id
            chunks.append(split_doc)

    return chunks


@dataclass
class ProcessedSource:
    """Container for one side (Source A or Source B) of the analysis."""

    source_label: str
    documents: List[Document]
    chunks: List[Document]
    filenames: List[str]
    total_pages: int


def process_uploaded_files(
    files: List[BinaryIO],
    filenames: List[str],
    source_label: str,
    source_letter: str,
    language: str,
) -> ProcessedSource:
    """Full pipeline: load -> validate -> chunk for one source (A or B),
    across one or more uploaded files."""
    all_documents: List[Document] = []
    for file, filename in zip(files, filenames):
        docs = load_file_to_documents(
            file=file,
            filename=filename,
            source_label=source_label,
            language=language,
        )
        all_documents.extend(docs)

    chunks = chunk_documents(all_documents, source_letter=source_letter)

    return ProcessedSource(
        source_label=source_label,
        documents=all_documents,
        chunks=chunks,
        filenames=list(dict.fromkeys(filenames)),
        total_pages=len(all_documents),
    )
