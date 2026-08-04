# 초기 생성 파일 설명

이 문서는 개발 시작 전에 필요한 파일과 각 파일의 목적을 정리합니다.

## 공통

- `README.md`: 프로젝트 목표, 기술 스택, 개발 순서를 팀원이 빠르게 이해하기 위한 시작 문서입니다.
- `.gitignore`: API 키, 설치 패키지, 빌드 결과물, 캐시 파일이 Git에 올라가지 않도록 막습니다.
- `.env.example`: 필요한 환경변수 목록을 공유하기 위한 예시 파일입니다. 실제 비밀키는 `.env`에만 저장합니다.
- `docs/architecture_summary.md`: 제공된 아키텍처 PDF의 핵심 결정을 개발용으로 요약한 문서입니다.
- `docs/functional_requirements_summary.md`: 기능 명세서 PDF의 PoC 기능 범위와 인수 기준을 요약한 문서입니다.

## 데이터와 DB

- `data/raw/.gitkeep`: 원본 PDF 또는 원본 텍스트를 넣을 폴더를 Git에 유지하기 위한 파일입니다.
- `data/raw/README.md`: 기준 원본 PDF의 출처, 프로젝트 내 파일명, 관리 방식을 설명합니다.
- `data/raw/economic_terms_800_2026.pdf`: 실제 데이터 기준이 되는 한국은행 경제금융용어 800선 PDF 복사본입니다. 원본 대용량 파일이므로 Git에는 올리지 않습니다.
- `data/processed/.gitkeep`: 정제된 JSON/CSV 데이터를 저장할 폴더를 Git에 유지하기 위한 파일입니다.
- `data/processed/economic_terms.json`: 기준 PDF에서 추출한 789개 경제금융용어 정제 데이터입니다. 임베딩 생성 전 단계의 원천 레코드로 사용합니다.
- `data/processed/extraction_report.json`: PDF 목차 항목 수, 실제 추출 성공 수, 누락 항목을 점검하기 위한 추출 리포트입니다.
- `data/source_manifest.json`: 원본 PDF의 출처, 발행 정보, 본문 시작/종료 위치를 기록합니다.
- `supabase/migrations/001_create_economic_terms.sql`: 경제용어, 공식 정의, 관련 키워드, 임베딩을 저장하는 PostgreSQL 테이블과 pgvector 검색 함수를 만듭니다.

## 백엔드

- `backend/pyproject.toml`: FastAPI 백엔드의 Python 의존성과 실행 명령을 정의합니다.
- `backend/app/main.py`: FastAPI 앱 진입점입니다. 상태 확인 API와 질문 API의 시작점입니다.
- `backend/app/core/config.py`: OpenAI, Supabase, 검색 기준 같은 환경변수를 한 곳에서 읽습니다.
- `backend/app/models/schemas.py`: 질문 요청, 검색 결과, 답변 응답의 데이터 구조를 정의합니다.
- `backend/app/services/retrieval.py`: 정확한 용어 검색과 벡터 검색을 담당할 서비스 파일입니다.
- `backend/app/services/answer_generator.py`: 검색된 공식 정의를 바탕으로 쉬운 설명을 생성할 서비스 파일입니다.
- `backend/scripts/ingest_terms.py`: PDF에서 정제한 경제용어 데이터를 DB에 넣고 임베딩을 생성하는 일회성 적재 스크립트의 시작점입니다.
- `backend/scripts/extract_terms_from_pdf.py`: 기준 PDF에서 목차와 본문을 읽어 `data/processed/economic_terms.json` 정제 데이터를 만드는 스크립트입니다.
- `backend/tests/test_health.py`: 백엔드 서버가 정상적으로 뜨는지 확인하는 최소 테스트입니다.

## 프론트엔드

- `frontend/package.json`: Next.js 프론트엔드 의존성과 실행 스크립트를 정의합니다.
- `frontend/next.config.mjs`: Next.js 설정 파일입니다.
- `frontend/tsconfig.json`: TypeScript 설정 파일입니다.
- `frontend/app/page.tsx`: 단일 챗봇 화면의 페이지 진입점입니다.
- `frontend/app/globals.css`: 전체 화면 스타일과 챗봇 UI 스타일을 정의합니다.
- `frontend/components/Chat.tsx`: 질문 입력, 로딩, 답변 표시를 담당하는 핵심 UI 컴포넌트입니다.
- `frontend/lib/api.ts`: FastAPI 질문 API 호출을 분리해 관리합니다.
