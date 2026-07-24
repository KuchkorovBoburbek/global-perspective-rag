# Global News & Paper Multi-Angle Perspective Analyzer
### 다국어 관점 차이 및 프레이밍 분석 AI

- 이름: [YOUR NAME]
- 학번: [YOUR STUDENT ID]

> 이 파일은 `PROJECT_REPORT.docx`의 편집 가능한 원본(source of truth)입니다.
> 내용을 수정한 뒤 `python -c "..."` 스크립트나 `docx` 스킬을 이용해
> `.docx`를 재생성할 수 있습니다.

---

## 1. Project Background (프로젝트 배경)

같은 이슈에 대해서도 국가·언어권에 따라 보도 프레이밍과 강조점이 다르게
나타나는 경우가 많습니다. 특히 AI 규제, 데이터 프라이버시, 국제 정책과 같은
주제는 영어권 매체와 한국어 매체가 서로 다른 가치(혁신 대 소비자 보호 등)를
중심으로 서술하는 경향이 있습니다. 본 프로젝트는 이러한 관점 차이를 사람이
일일이 대조하지 않고, RAG 기반 AI가 근거를 명시하며 자동으로 비교·분석하도록
설계되었습니다.

## 2. Problem Definition (문제 정의)

- 단순 기계 번역은 "무엇이 다른가"만 보여줄 뿐 "왜 다르게 프레이밍되었는가"는
  설명하지 못한다.
- 두 언어 문서를 하나의 벡터 저장소에 섞어 검색하면 한쪽 언어로 검색 결과가
  편중되어 공정한 비교가 어렵다.
- "이 기사는 편향되었다"는 판단은 텍스트 근거 없이 내려질 경우 신뢰할 수
  없으며, 사실/해석/추론을 구분하지 않으면 오해를 유발할 수 있다.

## 3. Service Objective (서비스 목표)

1. 두 개의 독립된 출처(Source A, Source B)에서 근거를 독립적으로 검색
2. 공통 사실 / 상충 주장 / 강조·누락 정보를 구조화된 형식으로 비교
3. 모든 주요 주장에 문서·페이지·청크 단위의 출처 표시 부여
4. 다국어(한국어/영어/우즈베크어/중국어/일본어) 질의응답 지원
5. 스크린샷 제출이 가능한 Executive Report 자동 생성

## 4. Technical Stack (기술 스택)

| 구성 요소 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| UI | Streamlit |
| LLM 오케스트레이션 | LangChain (LCEL) |
| LLM | OpenAI ChatOpenAI (langchain-openai), 모델 id는 `OPENAI_MODEL` 환경변수로 관리 |
| 임베딩 | OpenAI Embeddings (langchain-openai) — LLM과 동일한 OpenAI API 사용 |
| 벡터 저장소 | FAISS (langchain-community) |
| 문서 처리 | pypdf, langchain-text-splitters |
| 리포트 생성 | python-docx |
| 환경변수 관리 | python-dotenv |

## 5. RAG Architecture (RAG 아키텍처)

```text
Source A Files
    ↓
Document Loader A
    ↓
Multilingual Chunking
    ↓
OpenAI Embeddings
    ↓
FAISS Vector Store A
    ↓
Retriever A ───────────────┐
                           ├── OpenAI (ChatOpenAI) Analysis Chain
Retriever B ───────────────┘
    ↑
FAISS Vector Store B
    ↑
Multilingual Chunking
    ↑
Document Loader B
    ↑
Source B Files
```

핵심 설계 원칙: **Source A와 Source B는 검색 시점까지 완전히 분리되며, 결과는
검색 이후에만 결합됩니다.** 이를 통해 한쪽 언어/출처가 다른 쪽을 압도하는
현상을 방지합니다.

## 6. Data Processing Flow (데이터 처리 흐름)

1. 파일 업로드 (PDF/TXT, Source A·B 각각 다중 파일 허용)
2. 확장자 검증 → 미지원 형식은 즉시 거부
3. PDF는 페이지 단위 텍스트 추출, 이미지 전용/빈 PDF는 한국어 오류 메시지로 안내
4. 공백/개행 정규화
5. `RecursiveCharacterTextSplitter` (chunk_size=900, chunk_overlap=150)로 청크 분할
6. 각 청크에 `source_label`, `filename`, `language`, `page`, `chunk_id` 메타데이터 부여
7. 문서 해시 계산 → 세션 상태에 캐시된 해시와 비교하여 변경 없으면 재임베딩 생략
8. OpenAI Embeddings로 벡터화 → FAISS 저장소 A/B 각각 구축

## 7. Main Features (주요 기능)

- ⚖️ 관점 및 프레이밍 분석 (9단계 구조화 리포트)
- ❓ 다국어 문서 질의응답 (출처 없는 질문에는 "정보 없음" 명시)
- 📊 Executive Report (Markdown/Word 다운로드)
- 세션 상태 기반 채팅 기록 및 결과 보존
- 사이드바 API 키 우선순위: secrets → 환경변수 → 사용자 입력

## 8. Prompt Design (프롬프트 설계)

세 개의 프롬프트(`prompts/comparison_prompt.py`, `qa_prompt.py`,
`executive_prompt.py`)는 공통적으로 다음 원칙을 강제합니다:

1. 검색된 컨텍스트 밖의 내용을 생성하지 말 것 (hallucination 방지)
2. 모든 중요한 주장에 `[Source X | 파일명 | page | chunk_id]` 출처 표시
3. 사실(fact) / 해석(interpretation) / 프레이밍 신호 / 불확실한 AI 추론을
   명확히 구분
4. 근거 없이 "편향되었다"고 단정하지 않을 것
5. 정보가 부족하면 "정보 없음"이라고 명시 (일반 지식으로 답변 금지)

## 9. Screenshots (스크린샷 자리 표시자)

- [스크린샷 1: 업로드 화면]
- [스크린샷 2: 관점 비교 분석 결과]
- [스크린샷 3: 다국어 Q&A]
- [스크린샷 4: Executive Report]

## 10. Testing Results (테스트 결과)

아래는 실제로 실행하여 확인한 결과입니다 (API 키 없이 실행 가능한 항목만
검증했습니다. 실제 OpenAI API 통합 테스트는 유효한 API 키가 있는
환경에서 별도로 수행해야 합니다).

| 테스트 | 결과 |
|---|---|
| `python -m compileall .` | ✅ 통과 (구문 오류 없음) |
| `python -m pytest tests -q` | ✅ 20 passed (TXT 로딩, PDF 빈 문서 감지, 메타데이터, 소스 분리, import 스모크 테스트 등) |
| `streamlit run app.py` 기동 확인 | ✅ 정상 기동 및 HTTP 200 응답 확인 (API 키 미설정 상태에서도 크래시 없이 오류 상태를 표시) |
| OpenAI 실제 API 호출 (채팅 + 임베딩) | ⚠️ 미검증 — 유효한 `OPENAI_API_KEY`가 필요하며, 본 자동화 환경에는 키가 제공되지 않았습니다. 실제 배포 전 반드시 실행하여 확인하세요. |

## 11. Limitations (한계)

- OCR 미지원으로 스캔 이미지 PDF 처리 불가
- 검색 k값(4~6) 제한으로 문서 전체 내용을 완벽히 반영하지 못할 수 있음
- 다국어 처리 과정에서 뉘앙스 손실 가능성
- "편향" 판단은 AI의 해석이며 법적 판단으로 사용 불가
- 소규모 표본 문서에서는 일반화된 결론 도출에 한계

## 12. Future Improvements (향후 개선 방향)

- OCR 지원 추가 (스캔 PDF 대응)
- 세 번째 이상 출처 비교 지원 (다자간 비교)
- 벡터 저장소 영구 저장 (세션 간 유지)
- 사용자별 문서 접근 제어 및 인증
- 자동 언어 감지 정확도 개선

## 13. GitHub URL

[YOUR GITHUB REPOSITORY URL]

## 14. Deployed URL

[YOUR STREAMLIT DEPLOYED URL]
