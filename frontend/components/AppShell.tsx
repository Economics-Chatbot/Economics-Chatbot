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

// 표정 상태:
// - default/closed (이미지 1: 눈 감고 미소)
// - thinking (이미지 2: 위 올려다보는 미소 - 로딩/검색 전용)
// - error (이미지 3: 동공지진/당황 - 오류/실패 전용)
export type CharacterState = "default" | "thinking" | "error";

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

// 이미지 4 스펙 기반 추천 질문 목록
const HOME_SUGGESTIONS = [
  { icon: "📈", text: "인플레이션이 뭐야?" },
  { icon: "％", text: "금리가 오르면 어떻게 돼?" },
  { icon: "📊", text: "ETF를 쉽게 설명해줘" },
];

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

  const characterLayout = screen === "home-idle" || screen === "home-typing" ? "home" : "result";

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
    setScreen("home-typing");
  };

  const submitQuestion = async (rawQuery: string) => {
    const trimmedQuery = rawQuery.trim();
    if (!trimmedQuery) return;
    if (["query-transition", "searching", "answer-streaming"].includes(screen)) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setUserQueryBubble(trimmedQuery);
    setQuery("");
    setTermData(null);
    setSuggestions([]);
    setFailureMsg("");
    setErrorMsg("");
    setAnswerContent("");

    // [규칙 1]: 정보를 불러올 때는 이미지 1(default/closed) & 이미지 2(thinking) 표정만 사용한다.
    setScreen("query-transition");
    setCharacter("default"); // 이미지 1 (눈 감은 표정)

    const timer1 = setTimeout(() => {
      setScreen("searching");
      setCharacter("thinking"); // 이미지 2 (위 올려다보는 표정)
    }, MOTION.thinkingStartMs);

    try {
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
      
      const timer2 = setTimeout(() => {
        if (data.status === "answerable" && data.term) {
          // 정보 로딩 성공: 이미지 1 미소 표정으로 결과 표시
          setTermData(data.term);
          setAnswerContent(data.term.official_definition);
          setScreen("answer-done");
          setCharacter("default"); // 이미지 1
        } else if (data.status === "suggestions" && data.suggestions) {
          // [규칙 2]: 오류/실패 시에는 이미지 3 (error/당황 표정) 사용
          setSuggestions(data.suggestions);
          setScreen("suggestions");
          setCharacter("error"); // 이미지 3
        } else {
          // [규칙 2]: 검색 실패 시 이미지 3 (error/당황 표정) 사용
          setFailureMsg("관련 용어를 찾지 못했어요.");
          setScreen("failure");
          setCharacter("error"); // 이미지 3
        }
      }, MOTION.contentReleaseMs);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      setTimeout(() => {
        // [규칙 2]: 오류 발생 시 이미지 3 (error/당황 표정) 사용
        setErrorMsg("답변을 불러오지 못했어요.");
        setScreen("error");
        setCharacter("error"); // 이미지 3
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
      {/* 헤더 (이미지 4 스펙) */}
      <header className="chunk-header">
        {screen !== "home-idle" && screen !== "home-typing" && (
          <button className="ui-header-back-button" onClick={handleBack} aria-label="뒤로가기">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2647D8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>
        )}
        <div className="ui-header-brand">EconomyMate</div>
        <button className="ui-header-info-button" aria-label="정보">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2647D8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
        </button>
      </header>

      {/* 캐릭터 스테이지 & 이미지 4 신규 3D 장식 요소 (?, 구체, 별) */}
      <div className="chunk-character-stage">
        <div className="ui-character-wrapper">
          {/* 이미지 1: 눈 감고 웃는 표정 (로딩/성공 전용) */}
          <Image
            src="/assets/character-default.png"
            alt="눈 감은 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "default" ? "active" : ""}`}
            priority
          />
          {/* 이미지 2: 위 쳐다보는 미소 표정 (검색/정보 로딩 전용) */}
          <Image
            src="/assets/character-thinking.png"
            alt="생각하는 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "thinking" ? "active" : ""}`}
          />
          {/* 이미지 3: 동공 지진 / 당황 표정 (오류/실패 전용) */}
          <Image
            src="/assets/character-curious.png"
            alt="당황한 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "error" ? "active" : ""}`}
          />
        </div>
        <div className="ui-character-shadow"></div>

        {/* [규칙 4]: 3D/파스텔 신규 장식 자산 (?, 구체, 별) */}
        <div className="stage-decorations">
          <div className="deco-question-mark">?</div>
          <div className="deco-orb deco-orb-purple"></div>
          <div className="deco-orb deco-orb-cyan"></div>
          <div className="deco-orb deco-orb-orange"></div>
          <div className="deco-star">✦</div>
        </div>
      </div>

      {/* [규칙 3]: 첫 구현 페이지 및 설명 페이지 (이미지 4 스펙) */}
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
              className="ui-suggestion-pill-button"
              onClick={() => handleSuggestionClick(suggestion.text)}
            >
              <span className="icon-chip-circle">{suggestion.icon}</span>
              <span>{suggestion.text}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 결과 및 상태 화면 */}
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
              <div className="chunk-term-header">
                <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
                <div className="ui-term-name">{termData.term_name}</div>
              </div>

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

              <div className="chunk-source">
                <span className="ui-source-label">출처</span>
                <span className="ui-source-value">한국은행 경제금융용어 800선</span>
              </div>

              {termData.related_terms && termData.related_terms.length > 0 && (
                <div className="chunk-related-terms">
                  <div className="ui-section-title-left">함께 보면 좋은 용어</div>
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

          {/* 이미지 3 표정 적용된 후보/실패/오류 화면 */}
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

          {screen === "failure" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">관련 용어를 찾지 못했어요.</div>
              <div className="feedback-desc">용어 이름이나 약어를 조금 더 정확하게 입력해 주세요.</div>
              <button
                className="feedback-action-button"
                onClick={() => setScreen("home-typing")}
              >
                다시 질문하기
              </button>
            </div>
          )}

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

      {/* 하단 DOCK 입력창 (이미지 4 스펙) */}
      <form
        className="chunk-input-dock"
        onSubmit={(e) => {
          e.preventDefault();
          void submitQuestion(query);
        }}
      >
        <textarea
          className="ui-textarea"
          placeholder="경제용어를 입력해 주세요"
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
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </button>
      </form>
    </div>
  );
}
