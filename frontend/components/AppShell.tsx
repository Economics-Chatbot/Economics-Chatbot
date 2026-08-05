"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";

// design.md 타입 정의
export type ScreenState =
  | "home-idle"
  | "home-typing"
  | "query-transition"
  | "searching"
  | "answer-streaming"
  | "answer-done"
  | "suggestions"
  | "failure"
  | "error";

export type CharacterState = "default" | "curious" | "eyes-closed" | "thinking";

export interface RetrievedTerm {
  term_id: number;
  term_name: string;
  official_definition: string;
  related_terms: string[];
}

export interface TermSuggestion {
  term_id: number;
  term_name: string;
  similarity: number;
  related_terms: string[];
}

const MOTION = {
  closeEyesMs: 90,
  shrinkDelayMs: 120,
  shrinkMs: 400,
  thinkingStartMs: 520,
  contentReleaseMs: 680,
  completeFadeMs: 180,
} as const;

const HOME_SUGGESTIONS = [
  "기준금리가 뭐야?",
  "환율이 오르면 왜 물가도 올라?",
  "인플레이션이 뭐야?",
];

export function AppShell() {
  const [screen, setScreen] = useState<ScreenState>("home-idle");
  const [character, setCharacter] = useState<CharacterState>("default");
  const [query, setQuery] = useState("");
  const [userQueryBubble, setUserQueryBubble] = useState("");
  
  // 스트리밍 / 결과 데이터 상태
  const [termData, setTermData] = useState<RetrievedTerm | null>(null);
  const [suggestions, setSuggestions] = useState<TermSuggestion[]>([]);
  const [failureMsg, setFailureMsg] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [answerContent, setAnswerContent] = useState("");
  
  const viewportRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const characterLayout = screen === "home-idle" || screen === "home-typing" ? "home" : "result";

  // 자동 스크롤
  useEffect(() => {
    if (viewportRef.current && (screen === "answer-streaming" || screen === "answer-done")) {
      const el = viewportRef.current;
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (isNearBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [answerContent, screen]);

  // 추천 질문 버튼 클릭 (자동 전송 대신 포커스 및 입력창 설정)
  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setScreen("home-typing");
    setCharacter("curious");
  };

  // 백엔드 API 질문 제출 핸들러 (design.md 19 타임라인 적용)
  const submitQuestion = async (rawQuery: string) => {
    const trimmedQuery = rawQuery.trim();
    if (!trimmedQuery) return;
    if (["query-transition", "searching", "answer-streaming"].includes(screen)) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    // 초기화 및 타임라인 시작
    setUserQueryBubble(trimmedQuery);
    setQuery("");
    setTermData(null);
    setSuggestions([]);
    setFailureMsg("");
    setErrorMsg("");
    setAnswerContent("");

    // 0ms: query-transition & eyes-closed
    setScreen("query-transition");
    setCharacter("eyes-closed");

    // 120ms: shrink delay handled by CSS data-character-layout

    // 520ms: searching & thinking
    const timer1 = setTimeout(() => {
      setScreen("searching");
      setCharacter("thinking");
    }, MOTION.thinkingStartMs);

    try {
      // BE2 벡터 검색 API 파이프라인 호출 (/be2/vector-retrieve)
      const res = await fetch("http://127.0.0.1:8000/be2/vector-retrieve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmedQuery }),
        signal: abortControllerRef.current.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} error`);
      }

      const data = await res.json();
      
      // 680ms 지점 이후 화면 결과 업데이트
      const timer2 = setTimeout(() => {
        if (data.status === "answerable" && data.term) {
          setTermData(data.term);
          setAnswerContent(data.term.official_definition);
          setScreen("answer-done");
          setCharacter("default");
        } else if (data.status === "suggestions" && data.suggestions) {
          setSuggestions(data.suggestions);
          setScreen("suggestions");
          setCharacter("curious");
        } else {
          setFailureMsg("관련 용어를 찾지 못했어요.");
          setScreen("failure");
          setCharacter("curious");
        }
      }, MOTION.contentReleaseMs);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      setTimeout(() => {
        setErrorMsg("답변을 불러오지 못했어요.");
        setScreen("error");
        setCharacter("curious");
      }, MOTION.contentReleaseMs);
    }
  };

  const handleBack = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setScreen("home-idle");
    setCharacter("default");
    setUserQueryBubble("");
    setTermData(null);
    setSuggestions([]);
  };

  return (
    <div className="app frame-app-mobile" data-screen={screen} data-character-layout={characterLayout}>
      {/* 7.1 & 8.1 CHUNK_HEADER */}
      <header className="chunk-header">
        {screen !== "home-idle" && screen !== "home-typing" && (
          <button className="ui-header-back-button" onClick={handleBack} aria-label="뒤로가기">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2647D8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>
        )}
        <div className="ui-header-brand">EconomyMate</div>
        {screen !== "home-idle" && screen !== "home-typing" && (
          <button className="ui-header-info-button" aria-label="정보">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#405DE6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
          </button>
        )}
      </header>

      {/* 6. CHUNK_CHARACTER_STAGE (루트 단 하나만 존재) */}
      <div className="chunk-character-stage">
        <div className="ui-character-wrapper">
          <Image
            src="/assets/character-default.png"
            alt="옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "default" ? "active" : ""}`}
            priority
          />
          <Image
            src="/assets/character-curious.png"
            alt="궁금한 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "curious" ? "active" : ""}`}
          />
          <Image
            src="/assets/character-complete.png"
            alt="눈 감은 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "eyes-closed" ? "active" : ""}`}
          />
          <Image
            src="/assets/character-thinking.png"
            alt="생각하는 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "thinking" ? "active" : ""}`}
          />
        </div>
        <div className="ui-character-shadow"></div>
      </div>

      {/* 7. 시작 화면 레이아웃 (home-only) */}
      <div className="home-only">
        <div className="chunk-home-intro">
          <h1 className="type-home-title">
            {"어려운 경제용어,\n이코노미메이트와 함께라면 어렵지 않아요!"}
          </h1>
        </div>

        <div className="chunk-home-guide">쉽고 친근하게 설명드릴게요.</div>

        <div className="chunk-home-suggestions">
          <div className="ui-section-title">자주 묻는 질문</div>
          {HOME_SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              className="ui-suggestion-button"
              onClick={() => handleSuggestionClick(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* 8. 결과 화면 레이아웃 (result-only) */}
      <div className="result-only">
        {userQueryBubble && (
          <div className="chunk-query-bubble">{userQueryBubble}</div>
        )}

        <div className="chunk-answer-viewport" ref={viewportRef}>
          {screen === "searching" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">관련 용어를 검색하고 있어요...</div>
              <div className="feedback-desc">한국은행 경제금융용어 800선 DB를 분석 중입니다.</div>
            </div>
          )}

          {termData && (
            <>
              {/* 8.5 CHUNK_TERM_HEADER */}
              <div className="chunk-term-header">
                <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
                <div className="ui-term-name">{termData.term_name}</div>
              </div>

              {/* 8.6 CHUNK_ANSWER_CONTENT */}
              <div className="chunk-answer-content">
                <div className="answer-section">
                  <div className="answer-section-title">📌 한 줄 정의</div>
                  <div className="answer-section-body">{answerContent}</div>
                </div>

                {termData.related_terms && termData.related_terms.length > 0 && (
                  <>
                    <div className="answer-divider"></div>
                    <div className="answer-section">
                      <div className="answer-section-title">💡 관련 키워드</div>
                      <div className="answer-section-body">
                        {termData.related_terms.join(", ")}
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* 8.8 CHUNK_SOURCE */}
              <div className="chunk-source">
                <span className="ui-source-label">출처</span>
                <span className="ui-source-value">한국은행 경제금융용어 800선</span>
              </div>

              {/* 8.9 CHUNK_RELATED_TERMS */}
              {termData.related_terms && termData.related_terms.length > 0 && (
                <div className="chunk-related-terms">
                  <div className="ui-section-title">함께 보면 좋은 용어</div>
                  <div className="related-term-buttons">
                    {termData.related_terms.map((term, idx) => (
                      <button
                        key={idx}
                        className="ui-related-term-button"
                        onClick={() => void submitQuestion(term)}
                      >
                        {term}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* 11.2 후보 안내 화면 */}
          {screen === "suggestions" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">혹시 이 용어를 찾으셨나요?</div>
              <div className="feedback-desc">질문과 가까운 용어를 골라주세요.</div>
              <div className="related-term-buttons">
                {suggestions.map((item) => (
                  <button
                    key={item.term_id}
                    className="ui-related-term-button"
                    onClick={() => void submitQuestion(item.term_name)}
                  >
                    {item.term_name} (유사도 {(item.similarity * 100).toFixed(0)}%)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 11.3 검색 실패 화면 */}
          {screen === "failure" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">관련 용어를 찾지 못했어요.</div>
              <div className="feedback-desc">용어 이름이나 약어를 조금 더 정확하게 입력해 주세요.</div>
              <button
                className="feedback-action-button"
                onClick={() => {
                  setScreen("home-typing");
                  setCharacter("curious");
                }}
              >
                다시 질문하기
              </button>
            </div>
          )}

          {/* 11.4 기술 오류 화면 */}
          {screen === "error" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">답변을 불러오지 못했어요.</div>
              <div className="feedback-desc">{errorMsg || "잠시 후 다시 시도해 주세요."}</div>
              <button
                className="feedback-action-button"
                onClick={() => void submitQuestion(userQueryBubble)}
              >
                다시 시도
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 7.6 CHUNK_INPUT_DOCK */}
      <form
        className="chunk-input-dock"
        onSubmit={(e) => {
          e.preventDefault();
          void submitQuestion(query);
        }}
      >
        <textarea
          className="ui-textarea"
          placeholder="경제용어를 물어보세요"
          value={query}
          onFocus={() => {
            if (screen === "home-idle") {
              setScreen("home-typing");
              setCharacter("curious");
            }
          }}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submitQuestion(query);
            }
          }}
        />
        <button
          className="ui-send-button"
          type="submit"
          disabled={!query.trim() || ["query-transition", "searching"].includes(screen)}
          aria-label="질문 보내기"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </button>
      </form>
    </div>
  );
}
