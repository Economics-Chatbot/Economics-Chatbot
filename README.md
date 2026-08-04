# EconomyMate

한국은행 경제금융용어 데이터를 기반으로 자연어 질문에 관련 경제용어, 쉬운 설명, 생활 예시, 출처를 제공하는 RAG 챗봇 PoC입니다.

## 핵심 구조

- Frontend: Next.js 단일 챗봇 화면
- Backend: Python FastAPI
- Database: Supabase PostgreSQL + pgvector
- AI: OpenAI Embeddings + Chat Completions
- Source Data: 한국은행 경제금융용어 PDF 정제 데이터

## 개발 순서

1. `data/raw/economic_terms_800_2026.pdf`를 기준 원본으로 사용합니다.
2. `backend/scripts/extract_terms_from_pdf.py`로 `data/processed/economic_terms.json`을 생성합니다.
3. `backend/scripts/ingest_terms.py`로 임베딩을 생성하고 Supabase에 적재합니다.
4. `supabase/migrations/001_create_economic_terms.sql`을 Supabase에 적용합니다.
5. FastAPI에서 정확 검색 및 벡터 검색을 구현합니다.
6. Next.js 챗봇 화면에서 FastAPI SSE 응답을 표시합니다.

## 초기 실행 준비

```bash
cp .env.example .env
```

`.env`에 OpenAI와 Supabase 값을 채운 뒤 백엔드와 프론트엔드를 각각 실행합니다.

## 백엔드 실행

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

상태 확인:

```bash
curl http://127.0.0.1:8000/health
```

## API

질문하기:

```bash
curl -X POST http://127.0.0.1:8000/questions \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"물가가 계속 오르는 현상이 뭐야?\"}"
```

용어 조회:

```bash
curl http://127.0.0.1:8000/terms/인플레이션
```

## 데이터 추출

```bash
cd backend
python scripts/extract_terms_from_pdf.py --input ../data/raw/economic_terms_800_2026.pdf --output ../data/processed/economic_terms.json
```

추출 결과 점검 리포트는 `data/processed/extraction_report.json`에 생성됩니다.
