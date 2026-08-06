# Retrieval 기반 LLM 스트리밍 답변 API 추가

## 변경 요약

- `POST /api/answers` 엔드포인트를 추가했습니다.
- Retrieval 결과가 고신뢰도 매칭인 경우에만 `official_definition`을 LLM에 전달해 답변을 생성합니다.
- LLM 응답은 SSE(Server-Sent Events)로 스트리밍되며 `answer_start`, `delta`, `answer_done`, `suggestions`, `failure`, `error`, `done` 이벤트를 반환합니다.
- 후보 추천(`suggestions`) 또는 검색 실패(`not_found`) 상태에서는 LLM을 호출하지 않습니다.

## 배경

사용자 질문을 먼저 벡터 검색으로 판별한 뒤, 답변 가능한 경제 용어에 대해서만 공식 정의를 근거로 쉬운 설명을 생성하는 흐름이 필요했습니다. 이를 통해 검색 근거가 없는 질문에는 모델이 임의로 답변하지 않도록 제한했습니다.

## 주요 동작

```text
사용자 질문
→ Retrieval
→ matched: official_definition 기반 LLM 스트리밍 답변
→ candidates: 후보 용어 반환, LLM 호출 없음
→ not_found: 검색 실패 반환, LLM 호출 없음
```

## 검증

- `backend` 테스트 실행 완료
- 결과: `24 passed`

## 참고

- 현재 프론트엔드는 아직 `/api/answers` SSE 응답을 소비하도록 연결되어 있지 않습니다.
- Swagger UI에서는 SSE 스트리밍 확인이 제한적이므로 `curl -N` 또는 프론트 SSE 클라이언트 구현으로 확인하는 것이 적합합니다.
