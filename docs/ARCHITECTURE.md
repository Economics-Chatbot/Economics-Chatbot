# EconomyMate 아키텍처

## 1. 프로젝트 개요

EconomyMate는 한국은행 경제금융용어 데이터를 기반으로 사용자의 자연어 질문에 관련 경제용어와 쉬운 설명을 제공하는 RAG 챗봇이다.

현재 서비스는 다음 세 부분으로 구성한다.

- `frontend`: 사용자에게 챗봇 화면을 제공하는 Next.js 애플리케이션
- `backend`: 질문 처리와 답변 생성을 담당하는 FastAPI 애플리케이션
- `Supabase`: 경제용어 원문, 메타데이터, 임베딩을 저장하고 벡터 검색을 수행하는 PostgreSQL 데이터베이스

```text
사용자
  │
  ▼
Next.js frontend :3000
  │ HTTP
  ▼
FastAPI backend :8000
  ├─ 정확한 용어 검색
  ├─ 질문 임베딩 생성
  ├─ Supabase pgvector 검색
  └─ 검색 근거 기반 답변 생성
       │
       ├─ OpenAI API
       └─ Supabase PostgreSQL
```

## 2. 저장소 구조

```text
Economics-Chatbot/
├── README.md                     # 설치, 실행, 기본 사용법
├── PROJECT_FILES.md              # 주요 파일 목록과 역할
├── .env.example                 # 환경변수 예시
├── backend/                     # FastAPI 백엔드
│   ├── pyproject.toml           # Python 의존성 및 테스트 설정
│   ├── app/
│   │   ├── main.py              # FastAPI 앱과 HTTP 엔드포인트
│   │   ├── core/                # 환경설정 및 외부 서비스 클라이언트
│   │   ├── models/              # 요청·응답 스키마
│   │   └── services/            # 검색 및 답변 생성 로직
│   ├── scripts/                 # 데이터 추출·적재 일회성 작업
│   └── tests/                   # 백엔드 테스트
├── frontend/                    # Next.js 프론트엔드
│   ├── package.json             # Node.js 의존성 및 실행 명령
│   ├── app/                     # App Router 페이지와 전역 스타일
│   ├── components/              # 화면 컴포넌트
│   └── lib/                     # 백엔드 API 호출 코드
├── data/
│   ├── raw/                     # 원본 데이터
│   ├── processed/               # 추출·정제 결과
│   └── source_manifest.json     # 데이터 출처와 처리 기준
├── docs/
│   └── ARCHITECTURE.md          # 시스템 구조와 설계 원칙
└── supabase/
    └── migrations/              # 데이터베이스 스키마 변경
```

생성물과 비밀정보인 `.env`, `.venv`, `node_modules`, `.next`는 소스 구조에 포함하지 않는다. 원본 PDF도 `data/raw/`에 보관하고, 처리 결과는 `data/processed/`에 생성한다.

## 3. 요청 처리 흐름

### 질문 답변

1. 프론트엔드가 `POST /questions`으로 질문을 보낸다.
2. 백엔드가 질문의 앞뒤 공백을 제거하고 요청 스키마를 검증한다.
3. 질문 임베딩을 생성하고 Supabase pgvector 검색을 수행한다.
4. 검색 결과가 기준 점수보다 낮거나 없으면 실패 안내를 반환한다.
5. 검색된 공식 정의를 근거로 OpenAI가 쉬운 답변을 생성한다.
6. 백엔드가 답변, 관련 용어, 출처를 프론트엔드에 반환한다.

### 용어 직접 조회

`GET /terms/{term}` 요청은 용어명을 기준으로 Supabase에서 직접 조회한 뒤, 조회된 공식 정의를 사용해 답변을 생성한다. 용어가 없으면 `404`를 반환한다.

## 4. 데이터 처리 흐름

```text
한국은행 PDF
  ▼
backend/scripts/extract_terms_from_pdf.py
  ▼
data/processed/economic_terms.json
  ▼
backend/scripts/ingest_terms.py
  ├─ OpenAI 임베딩 생성
  └─ Supabase economic_terms 테이블 적재
```

데이터 추출과 적재는 애플리케이션 요청 처리와 분리된 일회성 작업이다. 운영 중 사용자 요청이 원본 PDF를 직접 읽거나 임베딩을 생성하지 않는다.

## 5. 서비스 책임

### Frontend

- 질문 입력과 전송
- 로딩·오류 상태 표시
- 답변, 관련 용어, 출처 표시
- 백엔드 API 주소를 `NEXT_PUBLIC_API_BASE_URL`로 관리

프론트엔드는 검색, 프롬프트 구성, OpenAI API 호출을 직접 수행하지 않는다.

### Backend

- HTTP 요청과 응답 처리
- 검색 순서와 검색 실패 정책 적용
- OpenAI 및 Supabase 호출 조정
- 클라이언트에 노출할 응답 형식 관리

OpenAI 키와 Supabase 서비스 역할 키는 백엔드에서만 사용한다.

### Supabase

- 경제용어와 출처 저장
- 임베딩 저장
- pgvector 유사도 검색

데이터베이스 스키마와 검색 함수는 `supabase/migrations/`에서 관리한다.

## 6. 주요 API

| Method | Path | 용도 |
|---|---|---|
| `GET` | `/api/health` | 백엔드 상태 확인 |
| `POST` | `/api/answers` | 자연어 질문 답변 |
| `GET` | `/api/terms/{term}` | 특정 경제용어 조회 및 답변 |

질문과 답변의 기본 데이터 구조는 `backend/app/models/schemas.py`에서 관리한다.

## 7. 환경과 실행

```bash
# 프로젝트 루트
cp .env.example .env

# 백엔드
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 별도 터미널에서 프론트엔드
cd frontend
npm install
npm run dev
```

- 프론트엔드: `http://localhost:3000`
- 백엔드: `http://127.0.0.1:8000`
- 상태 확인: `GET /health`

## 8. 설계 원칙

- 공식 데이터에 검색된 근거가 있을 때만 답변한다.
- 검색 실패 시 모델이 임의의 경제 설명을 생성하지 않는다.
- 데이터 처리 스크립트와 사용자 요청 처리를 분리한다.
- 외부 서비스 접근은 백엔드에 둔다.
- 기능이 늘어나기 전까지는 현재의 단순한 앱·서비스 구조를 유지한다.

## 9. 현재 범위 밖의 기능

- 로그인과 권한 관리
- 대화 이력 저장
- 관리자용 데이터 업로드 화면
- 모델 파인튜닝
- 별도 벡터 데이터베이스
- WebSocket 기반 실시간 통신
