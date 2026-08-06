"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";

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

export type CharacterState = "default" | "blink" | "thinking" | "error";

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
} as const;

// 레퍼런스 추천 질문
const HOME_SUGGESTIONS = [
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
        <polyline points="17 6 23 6 23 12"></polyline>
      </svg>
    ),
    text: "인플레이션이 뭐야?",
  },
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <line x1="19" y1="5" x2="5" y2="19"></line>
        <circle cx="6.5" cy="6.5" r="2.5" fill="#0284c7"></circle>
        <circle cx="17.5" cy="17.5" r="2.5" fill="#0284c7"></circle>
      </svg>
    ),
    text: "금리가 오르면 어떻게 돼?",
  },
  {
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
        <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
      </svg>
    ),
    text: "ETF를 쉽게 설명해줘",
  },
];

function normalizeRelatedTerms(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String).map((term) => term.trim()).filter(Boolean);
  }
  if (typeof value !== "string" || !value.trim()) return [];

  const trimmed = value.trim();
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      return parsed.map(String).map((term) => term.trim()).filter(Boolean);
    }
  } catch {
    // JSON 파싱 실패 시 처리
  }

  return trimmed
    .replace(/^\{(.*)\}$/, "$1")
    .split(",")
    .map((term) => term.trim().replace(/^['"]|['"]$/g, ""))
    .filter(Boolean);
}

function firstSentence(text: string): string {
  const normalized = text.trim();
  const match = normalized.match(/^.*?[.!?。](?:\s|$)/);
  return (match?.[0] ?? normalized).trim();
}

export function AppShell() {
  const [screen, setScreen] = useState<ScreenState>("home-idle");
  const [character, setCharacter] = useState<CharacterState>("default");
  const [query, setQuery] = useState("");
  const [userQueryBubble, setUserQueryBubble] = useState("");
  
  const [termData, setTermData] = useState<RetrievedTerm | null>(null);
  const [suggestions, setSuggestions] = useState<TermSuggestion[]>([]);
  const [failureMsg, setFailureMsg] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [answerContent, setAnswerContent] = useState("");
  
  const viewportRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const characterLayout = screen === "home-idle" || screen === "home-typing" ? "home" : "result";

  const clearRequestTimers = () => {
    requestTimersRef.current.forEach(clearTimeout);
    requestTimersRef.current = [];
  };

  useEffect(() => {
    if (screen !== "home-idle" && screen !== "home-typing") return;

    let blinkTimer: ReturnType<typeof setTimeout>;
    let openTimer: ReturnType<typeof setTimeout>;
    const scheduleBlink = () => {
      blinkTimer = setTimeout(() => {
        setCharacter("blink");
        openTimer = setTimeout(() => {
          setCharacter("default");
          scheduleBlink();
        }, 150);
      }, 2800 + Math.random() * 1800);
    };

    setCharacter("default");
    scheduleBlink();
    return () => {
      clearTimeout(blinkTimer);
      clearTimeout(openTimer);
    };
  }, [screen]);

  useEffect(() => () => {
    clearRequestTimers();
    abortControllerRef.current?.abort();
  }, []);

  useEffect(() => {
    if (viewportRef.current && (screen === "answer-streaming" || screen === "answer-done")) {
      const el = viewportRef.current;
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (isNearBottom) {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [answerContent, screen]);

  const handleSuggestionClick = (suggestionText: string) => {
    setQuery(suggestionText);
    void submitQuestion(suggestionText);
  };

  const submitQuestion = async (rawQuery: string) => {
    const trimmedQuery = rawQuery.trim();
    if (!trimmedQuery) return;
    if (["query-transition", "searching", "answer-streaming"].includes(screen)) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    clearRequestTimers();
    abortControllerRef.current = new AbortController();

    setUserQueryBubble(trimmedQuery);
    setQuery("");
    setTermData(null);
    setSuggestions([]);
    setFailureMsg("");
    setErrorMsg("");
    setAnswerContent("");

    setScreen("query-transition");
    setCharacter("default");

    requestTimersRef.current.push(
      setTimeout(() => {
        setScreen("searching");
        setCharacter("thinking"); // 이미지 2 (위 쳐다보는 생각 표정)
      }, MOTION.thinkingStartMs)
    );

    try {
      const timeoutId = setTimeout(() => {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
      }, 8000);

      const res = await fetch("http://127.0.0.1:8000/be2/vector-retrieve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmedQuery }),
        signal: abortControllerRef.current.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status} error`);
      }

      const data = await res.json();

      if (data.term) {
        data.term.related_terms = normalizeRelatedTerms(data.term.related_terms);
      }
      if (Array.isArray(data.suggestions)) {
        data.suggestions = data.suggestions.map((item: TermSuggestion) => ({
          ...item,
          related_terms: normalizeRelatedTerms(item.related_terms),
        }));
      }
      
      requestTimersRef.current.push(
        setTimeout(() => {
          if (data.status === "answerable" && data.term) {
            setTermData(data.term);
            setAnswerContent(data.term.official_definition);
            setScreen("answer-done");
            setCharacter("default"); // 이미지 1
          } else if (data.status === "suggestions" && data.suggestions && data.suggestions.length > 0) {
            setSuggestions(data.suggestions);
            setScreen("suggestions");
            setCharacter("error"); // 이미지 3 (당황 표정)
          } else {
            setFailureMsg("관련 용어를 찾지 못했어요.");
            setScreen("failure");
            setCharacter("error"); // 이미지 3 (당황 표정)
          }
        }, MOTION.contentReleaseMs)
      );
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      requestTimersRef.current.push(
        setTimeout(() => {
          setCharacter("blink");
          setErrorMsg("답변을 불러오지 못했어요.");
          setScreen("error");
          requestTimersRef.current.push(setTimeout(() => setCharacter("error"), 140));
        }, MOTION.contentReleaseMs)
      );
    }
  };

  const handleBack = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    clearRequestTimers();
    setScreen("home-idle");
    setCharacter("default");
    setUserQueryBubble("");
    setTermData(null);
    setSuggestions([]);
  };

  return (
    <div
      className="app frame-app-mobile"
      data-screen={screen}
      data-character-layout={characterLayout}
      data-character-state={character}
    >
      {/* 헤더 */}
      <header className="chunk-header">
        {screen !== "home-idle" && screen !== "home-typing" && (
          <button className="ui-header-back-button" onClick={handleBack} aria-label="뒤로가기">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>
        )}
        <div className="ui-header-brand">EconomyMate</div>
        <button className="ui-header-info-button" aria-label="정보">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" stroke="#2563eb" strokeWidth="2.2" fill="none"></circle>
            <line x1="12" y1="16" x2="12" y2="12" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round"></line>
            <circle cx="12" cy="8" r="1.2" fill="#2563eb"></circle>
          </svg>
        </button>
      </header>

      {/* 캐릭터 스테이지 & 3D 장식들 */}
      <div className="chunk-character-stage">
        <div className="ui-character-wrapper">
          {/* 이미지 1: 기본 미소 (눈 뜬 상태) */}
          <Image
            src="/assets/character-default.png"
            alt="옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "default" ? "active" : ""}`}
            priority
            unoptimized
          />
          {/* 이미지 2: 위 쳐다보는 생각 표정 */}
          <Image
            src="/assets/character-thinking.png"
            alt="생각하는 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "thinking" ? "active" : ""}`}
            unoptimized
          />
          {/* 눈 감기 깜빡임 프레임 */}
          <Image
            src="/assets/character-complete.png"
            alt="눈 감은 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "blink" ? "active" : ""}`}
            unoptimized
          />
          {/* 이미지 3: 당황 표정 */}
          <Image
            src="/assets/character-curious.png"
            alt="당황한 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "error" ? "active" : ""}`}
            unoptimized
          />
        </div>
        <div className="ui-character-shadow"></div>

        {/* 3D 장식 요소들 */}
        <div className="stage-decorations">
          <div className="deco-question-mark-1">?</div>
          <div className="deco-question-mark-2">?</div>
          <div className="deco-orb-purple-large"></div>
          <div className="deco-orb-cyan-top"></div>
          <div className="deco-orb-orange-small"></div>
          <div className="deco-star-sparkle">✦</div>
        </div>
      </div>

      {/* 시작 화면 전용 */}
      <div className="home-only">
        <div className="chunk-home-intro">
          <h1 className="type-home-title">
            {"궁금한 경제용어,\n편하게 물어보세요"}
          </h1>
        </div>

        <div className="chunk-home-guide">어려운 경제를 쉽고 친근하게 설명해드릴게요.</div>

        <div className="chunk-home-suggestions">
          <div className="ui-section-title-left">이런 질문은 어때요?</div>
          {HOME_SUGGESTIONS.map((suggestion, idx) => (
            <button
              key={idx}
              type="button"
              className="ui-suggestion-pill-button"
              onClick={() => handleSuggestionClick(suggestion.text)}
            >
              <span className="icon-chip-circle">{suggestion.icon}</span>
              <span>{suggestion.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 모든 질문 결과 화면 (성공, 후보, 실패, 에러 포함) */}
      <div className="result-only">
        {/* 모든 질문 상태에서 유저 질문 말풍선은 캐릭터 우측 아래 (top: 135px, right: 20px) 렌더링 */}
        {userQueryBubble && (
          <div className="chunk-query-bubble">{userQueryBubble}</div>
        )}

        <div className="chunk-answer-viewport" ref={viewportRef}>
          {screen === "searching" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">관련 용어를 검색하고 있어요...</div>
              <div className="feedback-desc">한국은행 경제금융용어 700선 DB를 분석 중입니다.</div>
            </div>
          )}

          {/* 성공 답변 카드 */}
          {termData && (
            <>
              <div className="chunk-term-card">
                <div className="chunk-term-header">
                  <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
                  <div className="ui-term-name">{termData.term_name}</div>
                </div>

                <div className="chunk-answer-content">
                  <div className="answer-section">
                    <div className="answer-section-title">📌 한 줄 정의</div>
                    <div className="answer-section-body">{firstSentence(answerContent)}</div>
                  </div>

                  <div className="answer-divider"></div>
                  <div className="answer-section">
                    <div className="answer-section-title">💡 쉬운 설명</div>
                    <div className="answer-section-body">{answerContent}</div>
                  </div>

                  <div className="answer-divider"></div>
                  <div className="answer-section">
                    <div className="answer-section-title">🏠 생활 속 예시</div>
                    <div className="answer-section-body">
                      {termData.term_name}이(가) 변하면 대출 금리와 물가 등 생활 전반에 영향을 미쳐요.
                    </div>
                  </div>
                </div>
              </div>

              <div className="chunk-source">
                <span className="ui-source-label">출처</span>
                <span className="ui-source-value">한국은행 경제금융용어 700선 · p.32</span>
              </div>

              {termData.related_terms.length > 0 && (
                <div className="chunk-related-terms">
                  <div className="ui-section-title-left">함께 보면 좋은 용어</div>
                  <div className="related-term-buttons">
                    {termData.related_terms.slice(0, 3).map((term, idx) => (
                      <button
                        key={`${term}-${idx}`}
                        type="button"
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

          {/* 후보 추천 상태 (유사 용어) */}
          {screen === "suggestions" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">혹시 이 용어를 찾으셨나요?</div>
              <div className="feedback-desc">질문과 가까운 용어를 아래에서 선택해 주세요.</div>
              <div className="related-term-buttons">
                {suggestions.map((item) => (
                  <button
                    key={item.term_id}
                    type="button"
                    className="ui-related-term-button"
                    onClick={() => void submitQuestion(item.term_name)}
                  >
                    {item.term_name} (유사도 {(item.similarity * 100).toFixed(0)}%)
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 관련 용어 미발견 (실패) 상태 */}
          {screen === "failure" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">관련 용어를 찾지 못했어요.</div>
              <div className="feedback-desc">
                용어 이름이나 약어를 조금 더 정확하게 입력해 주세요.
              </div>
              <button
                type="button"
                className="feedback-action-button"
                onClick={() => setScreen("home-typing")}
              >
                다시 질문하기
              </button>
            </div>
          )}

          {/* 에러 상태 */}
          {screen === "error" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">답변을 불러오지 못했어요.</div>
              <div className="feedback-desc">{errorMsg || "잠시 후 다시 시도해 주세요."}</div>
              <button
                type="button"
                className="feedback-action-button"
                onClick={() => void submitQuestion(userQueryBubble)}
              >
                다시 시도
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 하단 DOCK 입력창 */}
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
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </div>
  );
}
