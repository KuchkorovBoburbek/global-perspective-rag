# 🌐 Global News & Paper Multi-Angle Perspective Analyzer
### 다국어 관점 차이 및 프레이밍 분석 AI

## 1. 프로젝트 개요

같은 사건이나 이슈라도 언어권과 매체에 따라 보도 방식, 강조점, 프레이밍이
크게 달라집니다. 이 프로젝트는 서로 다른 언어의 문서 두 개(예: 영어 국제
언론/논문과 한국어 언론/논문)를 업로드하면, 각 문서에서 **독립적으로** 근거를
검색(RAG)하여 두 관점을 비교 분석하고, 모든 주장에 출처를 명시하는 다국어
RAG(Retrieval-Augmented Generation) 애플리케이션입니다.

이 프로젝트는 단순 번역기가 아닙니다. 두 개의 독립된 FAISS 벡터 저장소를
구축하고, 각 질의마다 두 저장소에서 각각 검색한 뒤 결과를 결합하여 OpenAI
모델(ChatOpenAI)이 비교·분석하도록 설계되었습니다. 채팅(분석)과 임베딩 모두
OpenAI API 하나로 동작합니다.

## 2. 핵심 문제 정의

- 다국어 뉴스/논문은 번역만으로는 "왜 다르게 보이는지"를 설명하지 못합니다.
- 단일 벡터 저장소에 두 문서를 섞으면, 검색 결과가 한쪽 언어로 편중되기 쉽고
  두 출처를 공정하게 비교하기 어렵습니다.
- "이 기사는 편향되었다"는 주장은 텍스트 근거 없이는 신뢰할 수 없습니다.

## 3. 주요 기능

1. Source A / Source B 각각 PDF·TXT 업로드 (다중 파일 지원)
2. 독립된 FAISS 벡터 저장소 2개 생성 (Source A 전용, Source B 전용)
3. **⚖️ 관점 및 프레이밍 분석**: 9개 섹션의 구조화된 비교 리포트
   (주제 요약 → 핵심 관점 → 공통 사실 → 프레이밍 차이 → 사실관계 차이 →
   강조/누락 정보 → 균형 잡힌 결론 → 분석의 한계)
4. **❓ 다국어 문서 질의응답**: 한국어/영어/우즈베크어/중국어/일본어로 질문 가능,
   문서에 근거가 없으면 "정보 없음"이라고 명시
5. **📊 Executive Report**: 스크린샷 제출용 요약 리포트 (Markdown/Word 다운로드)
6. 모든 주요 주장에 `[Source A | 파일명 | page | chunk_id]` 형식의 출처 표시
7. 문서 해시 기반 캐싱으로 동일 문서 재임베딩 방지

## 4. 스크린샷 (자리 표시자)

> 실제 배포 후 아래에 스크린샷을 추가하세요.

- `screenshots/upload.png` — 업로드 화면
- `screenshots/comparison.png` — 관점 비교 분석 결과
- `screenshots/qa.png` — 다국어 Q&A 채팅 화면
- `screenshots/executive.png` — Executive Report 화면

## 5. 아키텍처

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

## 6. 로컬 설치

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd global-perspective-rag

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## 7. 환경 변수

`.env.example`을 복사하여 `.env`를 만들고 값을 채워주세요.

```bash
cp .env.example .env
```

| 변수 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (필수, 채팅/분석과 임베딩 양쪽 모두에 사용) |
| `OPENAI_MODEL` | 분석/Q&A/Executive Report에 사용할 채팅 모델 id. 미설정 시 안전한 기본값(`gpt-4o-mini`) 사용 (코드 수정 불필요) |
| `OPENAI_EMBEDDING_MODEL` | 임베딩 모델명 (기본값: `text-embedding-3-small`) |

`.env`는 절대 GitHub에 커밋하지 마세요 (`.gitignore`에 이미 포함되어 있습니다).

## 8. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속.

## 9. 사용 예시

1. 사이드바에서 이름/학번 입력, 출력 언어 선택
2. Source A에 `sample_data/us_tech_regulation.txt` 업로드, 언어 "English" 선택
3. Source B에 `sample_data/kr_tech_regulation.txt` 업로드, 언어 "한국어" 선택
4. "📥 문서 처리 및 RAG 생성" 클릭
5. "⚖️ 관점 및 프레이밍 분석" 탭에서 비교 분석 실행
6. "❓ 다국어 문서 질의응답" 탭에서 예: "두 문서가 스타트업에 미치는 영향을
   어떻게 다르게 설명하나요?"라고 질문
7. "📊 Executive Report" 탭에서 요약 리포트 생성 및 다운로드

## 10. 배포 (Streamlit Community Cloud)

1. GitHub 저장소 생성 및 코드 푸시:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Global Perspective RAG Analyzer"
   git branch -M main
   git remote add origin <YOUR_GITHUB_REPO_URL>
   git push -u origin main
   ```
2. [share.streamlit.io](https://share.streamlit.io) 접속 → "New app" 클릭
3. 저장소, 브랜치, **Main file path: `app.py`** 지정
4. **Secrets 설정** (App settings → Secrets):
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   ```
5. Deploy 클릭 후 공개 URL 확인 및 정상 동작 테스트
6. Secrets가 설정되어 있으면 일반 사용자는 API 키를 직접 입력할 필요가 없습니다.

## 11. 한계 (Limitations)

- OCR을 지원하지 않으므로 스캔된 이미지 PDF는 처리할 수 없습니다.
- 검색 결과는 `k=4~6`개 청크로 제한되어 문서 전체를 완벽히 반영하지 못할 수
  있습니다.
- 다국어 번역/의미 전달 과정에서 뉘앙스가 손실될 수 있습니다.
- "편향" 여부에 대한 판단은 AI의 해석이며, 법적·학술적 판단으로 사용할 수
  없습니다.
- 표본 문서가 적을 경우 일반화된 결론을 내리기 어렵습니다.

## 12. 보안 경고 (Security Warning)

- `.env` 파일과 API 키를 절대 GitHub에 커밋하지 마세요.
- 사이드바에 입력한 개발자 API 키는 화면에 표시되거나 로그에 남지 않도록
  설계되어 있으나, 공용 컴퓨터에서 입력 후 반드시 재발급/폐기하는 것을
  권장합니다.
- 업로드한 문서는 세션 동안 벡터 저장소(FAISS, 로컬 인메모리)에만 저장되며,
  별도 데이터베이스에 영구 저장되지 않습니다.

## 13. 제출 체크리스트

```text
[ ] Name and student ID inserted
[ ] Application runs locally
[ ] Source A and Source B retrieve independently
[ ] Evidence references appear in answers
[ ] GitHub repository pushed
[ ] Streamlit public URL works
[ ] project_code.ipynb completed
[ ] PROJECT_REPORT.docx completed
[ ] No API keys committed
[ ] Slack submission message prepared
```

## 14. 제출 Slack DM 템플릿

```text
안녕하세요, 과제 제출합니다.

- 이름: [이름]
- 학번: [학번]
- 배포 URL: [Streamlit 공개 URL]
- GitHub URL: [저장소 URL]
- 노트북 파일: project_code.ipynb (첨부)
- Word 보고서: PROJECT_REPORT.docx (첨부)

감사합니다.
```
