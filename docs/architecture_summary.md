# Architecture Summary

## 목표

경제금융용어 PDF를 기반으로 사용자의 질문에 쉬운 설명을 제공하는 RAG 기반 Q&A 챗봇을 만든다.

지원 질문 유형:

- 직접 용어 질문: "기준금리가 뭐야?"
- 자연어 질문: "물가가 계속 오르는 현상을 뭐라고 해?"

## 기술 스택

- Frontend: Next.js
- Backend: Python FastAPI
- Database: Supabase PostgreSQL
- Vector Search: pgvector
- AI: OpenAI API
- Source: 한국은행 경제금융용어 PDF

## 처리 흐름

1. PDF를 일회성 스크립트로 텍스트 추출 및 정제한다.
2. 용어명, 공식 정의, 관련 키워드, 임베딩을 DB 테이블에 저장한다.
3. 질문 임베딩을 생성하고 pgvector 유사도 검색을 수행한다.
4. 검색 결과가 기준 점수보다 낮으면 임의 답변을 생성하지 않는다.
5. 검색된 공식 자료만 OpenAI 모델에 전달해 구조화된 답변을 생성한다.
6. Next.js 단일 채팅 화면에 답변과 출처를 표시한다.

## 제외 범위

- 로그인
- 장기 대화 저장
- 관리자용 PDF 업로드 화면
- 모델 파인튜닝
- 별도 벡터 DB
- LangChain, LangGraph
- WebSocket
