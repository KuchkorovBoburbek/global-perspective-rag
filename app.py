"""Global News & Paper Multi-Angle Perspective Analyzer
다국어 관점 차이 및 프레이밍 분석 AI

Streamlit entry point.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from prompts.qa_prompt import qa_prompt  # noqa: F401  (imported for clarity / import-smoke test)
from utils.document_loader import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    process_uploaded_files,
)
from utils.rag_chain import (
    build_comparison_chain,
    build_executive_chain,
    build_qa_chain,
    get_model_name,
)
from utils.report_generator import executive_report_to_docx_bytes, markdown_report_to_bytes
from utils.vector_store import get_or_build_vector_store

load_dotenv()

st.set_page_config(
    page_title="Global News & Paper Multi-Angle Perspective Analyzer",
    page_icon="🌐",
    layout="wide",
)

LANGUAGE_OPTIONS = ["한국어", "English", "O'zbekcha", "中文", "日本語"]
SOURCE_LANGUAGE_OPTIONS = ["English", "한국어", "中文", "日本語", "O'zbekcha", "기타/Other"]


# ---------------------------------------------------------------------------
# API key resolution: secrets -> env vars -> sidebar input
# ---------------------------------------------------------------------------
def resolve_api_key(secret_name: str, env_name: str, sidebar_value: str | None) -> str | None:
    try:
        if secret_name in st.secrets:
            return st.secrets[secret_name]
    except Exception:
        pass
    if os.getenv(env_name):
        return os.getenv(env_name)
    if sidebar_value:
        return sidebar_value
    return None


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "vector_store_a": None,
        "vector_store_b": None,
        "processed_a": None,
        "processed_b": None,
        "comparison_result": None,
        "qa_history": [],  # list of {role, content}
        "executive_result": None,
        "topic_hint": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🌐 앱 정보")
    st.markdown(
        """
        **Global News & Paper Multi-Angle Perspective Analyzer**

        서로 다른 언어권의 두 문서(예: 영어 국제 언론/논문 vs 한국어 언론/논문)를
        업로드하면, 각 문서에서 **독립적으로** 근거를 검색하여 관점·프레이밍·편향
        신호·공통 사실·상충되는 주장·강조/누락 정보를 비교 분석하고, 출처가
        명시된 균형 잡힌 결론을 제공합니다.
        """
    )

    st.divider()
    st.subheader("제출 정보")
    student_name = st.text_input("이름 (Name)", key="student_name")
    student_id = st.text_input("학번 (Student ID)", key="student_id")

    st.divider()
    st.subheader("출력 언어")
    output_language = st.selectbox("Q&A 응답 언어", LANGUAGE_OPTIONS, index=0)

    st.divider()
    st.subheader("개발자 API 키 (선택)")
    st.caption("배포 환경에 secrets가 설정되어 있으면 여기 입력하지 않아도 됩니다.")
    sidebar_openai_key = st.text_input("OPENAI_API_KEY", type="password")

    openai_key = resolve_api_key("OPENAI_API_KEY", "OPENAI_API_KEY", sidebar_openai_key)

    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    st.divider()
    st.subheader("API 연결 상태")
    if openai_key:
        st.success("OpenAI ✅ (Chat + Embeddings)")
    else:
        st.error("OpenAI ❌")
    st.caption(f"사용 모델: `{get_model_name()}` (env: OPENAI_MODEL)")

# ---------------------------------------------------------------------------
# Main upload area
# ---------------------------------------------------------------------------
st.title("🌐 Global News & Paper Multi-Angle Perspective Analyzer")
st.caption("다국어 관점 차이 및 프레이밍 분석 AI")

col_source_a, col_source_b = st.columns(2)

with col_source_a:
    st.subheader("📰 Source A")
    files_a = st.file_uploader(
        "Source A 파일 업로드 (PDF/TXT, 여러 개 가능)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="uploader_a",
    )
    lang_a = st.selectbox("Source A 언어", SOURCE_LANGUAGE_OPTIONS, index=0, key="lang_a")

with col_source_b:
    st.subheader("📰 Source B")
    files_b = st.file_uploader(
        "Source B 파일 업로드 (PDF/TXT, 여러 개 가능)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="uploader_b",
    )
    lang_b = st.selectbox("Source B 언어", SOURCE_LANGUAGE_OPTIONS, index=1, key="lang_b")

topic_hint = st.text_input(
    "분석 주제 (선택, 비워두면 자동으로 일반 주제 요약 사용)",
    key="topic_hint_input",
)

process_clicked = st.button("📥 문서 처리 및 RAG 생성", type="primary", use_container_width=True)

if process_clicked:
    if not files_a or not files_b:
        st.error("Source A와 Source B 양쪽 모두 최소 1개 이상의 파일을 업로드해야 합니다.")
    elif not openai_key:
        st.error("OPENAI_API_KEY가 필요합니다. 사이드바를 확인하세요.")
    else:
        with st.status("문서 처리 및 벡터 저장소 생성 중...", expanded=True) as status:
            try:
                status.write("Source A 로딩 및 청크 분할 중...")
                processed_a = process_uploaded_files(
                    files=files_a,
                    filenames=[f.name for f in files_a],
                    source_label="Source A",
                    source_letter="A",
                    language=lang_a,
                )
                status.write(f"Source A: {len(processed_a.documents)}개 페이지, {len(processed_a.chunks)}개 청크")

                status.write("Source B 로딩 및 청크 분할 중...")
                processed_b = process_uploaded_files(
                    files=files_b,
                    filenames=[f.name for f in files_b],
                    source_label="Source B",
                    source_letter="B",
                    language=lang_b,
                )
                status.write(f"Source B: {len(processed_b.documents)}개 페이지, {len(processed_b.chunks)}개 청크")

                status.write("Source A 임베딩 (FAISS) 생성/캐시 확인 중...")
                store_a = get_or_build_vector_store(
                    processed_a.chunks,
                    source_label="Source A",
                    cache=st.session_state,
                    cache_key="vector_store_a",
                )

                status.write("Source B 임베딩 (FAISS) 생성/캐시 확인 중...")
                store_b = get_or_build_vector_store(
                    processed_b.chunks,
                    source_label="Source B",
                    cache=st.session_state,
                    cache_key="vector_store_b",
                )

                st.session_state.processed_a = processed_a
                st.session_state.processed_b = processed_b
                st.session_state.vector_store_a = store_a
                st.session_state.vector_store_b = store_b
                st.session_state.qa_history = []
                st.session_state.comparison_result = None
                st.session_state.executive_result = None

                status.update(label="✅ 처리 완료", state="complete", expanded=False)
            except (UnsupportedFileTypeError, EmptyDocumentError) as e:
                status.update(label="❌ 처리 실패", state="error")
                st.error(str(e))
            except Exception as e:  # noqa: BLE001
                status.update(label="❌ 처리 실패", state="error")
                st.error(f"오류가 발생했습니다: {e}")

# ---------------------------------------------------------------------------
# Status metrics
# ---------------------------------------------------------------------------
if st.session_state.processed_a and st.session_state.processed_b:
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "업로드 파일 수",
            len(st.session_state.processed_a.filenames) + len(st.session_state.processed_b.filenames),
        )
    with m2:
        st.metric(
            "추출된 페이지 수",
            st.session_state.processed_a.total_pages + st.session_state.processed_b.total_pages,
        )
    with m3:
        st.metric(
            "총 청크 수",
            len(st.session_state.processed_a.chunks) + len(st.session_state.processed_b.chunks),
        )
    with m4:
        st.metric("언어", f"{lang_a} / {lang_b}")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_compare, tab_qa, tab_exec = st.tabs(
    ["⚖️ 관점 및 프레이밍 분석", "❓ 다국어 문서 질의응답", "📊 Executive Report"]
)

ready = bool(st.session_state.vector_store_a and st.session_state.vector_store_b)

with tab_compare:
    if not ready:
        st.info("먼저 위에서 Source A / Source B 문서를 업로드하고 처리해주세요.")
    else:
        run_compare = st.button("🔍 관점 비교 분석 실행", key="run_compare")
        if run_compare:
            with st.spinner("OpenAI 모델이 두 출처를 독립적으로 검색하고 비교 분석 중입니다..."):
                topic = st.session_state.get("topic_hint_input") or "두 문서의 핵심 주제"
                chain = build_comparison_chain(
                    st.session_state.vector_store_a, st.session_state.vector_store_b
                )
                result = chain.invoke({"topic": topic})
                st.session_state.comparison_result = result

        if st.session_state.comparison_result:
            result = st.session_state.comparison_result
            st.markdown(result["report"])

            all_docs = result["source_a_docs"] + result["source_b_docs"]
            md_bytes = markdown_report_to_bytes(
                "관점 및 프레이밍 분석 결과", result["report"]
            )
            st.download_button(
                "⬇️ Markdown으로 다운로드",
                data=md_bytes,
                file_name="perspective_analysis.md",
                mime="text/markdown",
            )

with tab_qa:
    if not ready:
        st.info("먼저 위에서 Source A / Source B 문서를 업로드하고 처리해주세요.")
    else:
        for msg in st.session_state.qa_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_question = st.chat_input("Source A와 Source B에 대해 질문하세요 (다국어 지원)")
        if user_question:
            st.session_state.qa_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.markdown(user_question)

            with st.chat_message("assistant"):
                with st.spinner("검색 및 답변 생성 중..."):
                    qa_chain = build_qa_chain(
                        st.session_state.vector_store_a, st.session_state.vector_store_b
                    )
                    qa_result = qa_chain.invoke(
                        {"question": user_question, "output_language": output_language}
                    )
                    st.markdown(qa_result["answer"])

            st.session_state.qa_history.append(
                {"role": "assistant", "content": qa_result["answer"]}
            )

with tab_exec:
    if not ready:
        st.info("먼저 위에서 Source A / Source B 문서를 업로드하고 처리해주세요.")
    else:
        run_exec = st.button("📊 Executive Report 생성", key="run_exec")
        if run_exec:
            with st.spinner("Executive Report 생성 중..."):
                topic = st.session_state.get("topic_hint_input") or "두 문서의 핵심 주제"
                file_count = len(st.session_state.processed_a.filenames) + len(
                    st.session_state.processed_b.filenames
                )
                chunk_count = len(st.session_state.processed_a.chunks) + len(
                    st.session_state.processed_b.chunks
                )
                languages = f"{lang_a}, {lang_b}"
                chain = build_executive_chain(
                    st.session_state.vector_store_a,
                    st.session_state.vector_store_b,
                    topic=topic,
                    file_count=file_count,
                    chunk_count=chunk_count,
                    languages=languages,
                )
                result = chain.invoke({})
                st.session_state.executive_result = result

        if st.session_state.executive_result:
            result = st.session_state.executive_result
            st.markdown(result["report"])

            all_docs = result["source_a_docs"] + result["source_b_docs"]
            col_md, col_docx = st.columns(2)
            with col_md:
                md_bytes = markdown_report_to_bytes("Executive Report", result["report"])
                st.download_button(
                    "⬇️ Markdown 다운로드",
                    data=md_bytes,
                    file_name="executive_report.md",
                    mime="text/markdown",
                )
            with col_docx:
                docx_bytes = executive_report_to_docx_bytes(
                    "Executive Report", result["report"], all_docs
                )
                st.download_button(
                    "⬇️ Word(.docx) 다운로드",
                    data=docx_bytes,
                    file_name="executive_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
