"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { ArrowLeft, ChartNoAxesColumnIncreasing, CircleHelp, PieChart } from "lucide-react";
import type { TermSuggestion } from "@/types/answers";
import type { CharacterState, ScreenState } from "@/types/ui";
import { ChatInput } from "@/components/ChatInput";
import { SuggestedQuestions, type SuggestedQuestion } from "@/components/SuggestedQuestions";
import { UserMessage } from "@/components/UserMessage";
import { ErrorCard } from "@/components/ErrorCard";
import { RelatedKeywordChip } from "@/components/RelatedKeywordChip";
import { MessageList } from "@/components/MessageList";
import { AnswerMessage, type AnswerMessageData } from "@/components/AnswerMessage";
import { LoadingCard } from "@/components/LoadingCard";
import { MOCK_ANSWER, MOCK_ANSWER_CHUNKS } from "@/lib/mock-answer";

type ChatMessage =
  | { id: string; type: "user"; text: string }
  | { id: string; type: "answer"; data: AnswerMessageData };

const MOTION = {
  closeEyesMs: 90,
  shrinkDelayMs: 120,
  shrinkMs: 400,
  thinkingStartMs: 520,
  contentReleaseMs: 680,
} as const;

// 레퍼런스 추천 질문
const HOME_SUGGESTIONS: SuggestedQuestion[] = [
  {
    icon: <ChartNoAxesColumnIncreasing size={18} strokeWidth={2.5} aria-hidden="true" />,
    text: "인플레이션이 뭐야?",
  },
  {
    icon: <CircleHelp size={18} strokeWidth={2.5} aria-hidden="true" />,
    text: "금리가 오르면 어떻게 돼?",
  },
  {
    icon: <PieChart size={18} strokeWidth={2.5} aria-hidden="true" />,
    text: "ETF를 쉽게 설명해줘",
  },
];

export function AppShell() {
  const [screen, setScreen] = useState<ScreenState>("home-idle");
  const [character, setCharacter] = useState<CharacterState>("default");
  const [query, setQuery] = useState("");
  const [userQueryBubble, setUserQueryBubble] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<TermSuggestion[]>([]);
  const [failureMsg, setFailureMsg] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  
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
  }, []);

  const handleSuggestionClick = (suggestionText: string) => {
    void submitQuestion(suggestionText);
  };

  const submitQuestion = async (rawQuery: string) => {
    const trimmedQuery = rawQuery.trim();
    if (!trimmedQuery) return;
    if (["query-transition", "searching", "answer-streaming"].includes(screen)) return;

    clearRequestTimers();

    setUserQueryBubble(trimmedQuery);
    setQuery("");
    const answerId = `${Date.now()}-${trimmedQuery}`;
    setChatMessages((current) => [
      ...current,
      { id: `${answerId}-user`, type: "user", text: trimmedQuery },
    ]);
    setSuggestions([]);
    setFailureMsg("");
    setErrorMsg("");

    setScreen("query-transition");
    setCharacter("default");

    requestTimersRef.current.push(
      setTimeout(() => {
        setScreen("searching");
        setCharacter("thinking"); // 이미지 2 (위 쳐다보는 생각 표정)
      }, MOTION.thinkingStartMs)
    );

    const answerStartDelay = MOTION.thinkingStartMs + 520;
    requestTimersRef.current.push(
      setTimeout(() => {
        if (trimmedQuery.includes("오류")) {
          setErrorMsg("답변을 생성하는 중 문제가 발생했어요.");
          setScreen("error");
          setCharacter("error");
          return;
        }

        setChatMessages((current) => [
          ...current,
          { id: answerId, type: "answer", data: { id: answerId, term: MOCK_ANSWER, content: "" } },
        ]);
        setScreen("answer-streaming");
        setCharacter("thinking");

        MOCK_ANSWER_CHUNKS.forEach((chunk, index) => {
          requestTimersRef.current.push(
            setTimeout(() => {
              setChatMessages((current) => current.map((message) => {
                if (message.type !== "answer" || message.id !== answerId) return message;
                return {
                  ...message,
                  data: { ...message.data, content: message.data.content + chunk },
                };
              }));
              if (index === MOCK_ANSWER_CHUNKS.length - 1) {
                setScreen("answer-done");
                setCharacter("default");
              }
            }, index * 620),
          );
        });
      }, answerStartDelay),
    );

  };

  const handleBack = () => {
    clearRequestTimers();
    setScreen("home-idle");
    setCharacter("default");
    setUserQueryBubble("");
    setChatMessages([]);
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
            <ArrowLeft size={24} strokeWidth={2.5} aria-hidden="true" />
          </button>
        )}
        <div className="ui-header-brand">EconomyMate</div>
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

        <SuggestedQuestions items={HOME_SUGGESTIONS} onSelect={handleSuggestionClick} />
      </div>

      {/* 모든 질문 결과 화면 (성공, 후보, 실패, 에러 포함) */}
      <div className="result-only">
        <MessageList
          scrollKey={`${screen}:${chatMessages.map((message) => message.id + (message.type === "answer" ? message.data.content : message.text)).join("|")}:${suggestions.length}`}
        >
          {chatMessages.map((message) => message.type === "user" ? (
            <UserMessage key={message.id}>{message.text}</UserMessage>
          ) : (
            <AnswerMessage
              key={message.id}
              message={message.data}
              onKeywordClick={(keyword) => void submitQuestion(keyword)}
            />
          ))}

          {screen === "searching" && (
            <LoadingCard />
          )}

          {/* 후보 추천 상태 (유사 용어) */}
          {screen === "suggestions" && (
            <div className="chunk-status-feedback">
              <div className="feedback-title">혹시 이 용어를 찾으셨나요?</div>
              <div className="feedback-desc">질문과 가까운 용어를 아래에서 선택해 주세요.</div>
              <div className="related-term-buttons">
                {suggestions.map((item) => (
                  <RelatedKeywordChip
                    key={item.term_id}
                    variant="candidate"
                    onClick={() => void submitQuestion(item.query)}
                  >
                    {item.term}
                  </RelatedKeywordChip>
                ))}
              </div>
            </div>
          )}

          {/* 관련 용어 미발견 (실패) 상태 */}
          {screen === "failure" && (
            <ErrorCard
              title="관련 용어를 찾지 못했어요."
              description="용어 이름이나 약어를 조금 더 정확하게 입력해 주세요."
              actionLabel="다시 질문하기"
              onAction={() => setScreen("home-typing")}
            />
          )}

          {/* 에러 상태 */}
          {screen === "error" && (
            <ErrorCard
              title="답변을 불러오지 못했어요."
              description={errorMsg || "잠시 후 다시 시도해 주세요."}
            />
          )}
        </MessageList>
      </div>

      {/* 하단 DOCK 입력창 */}
      <ChatInput
        value={query}
        disabled={["query-transition", "searching"].includes(screen)}
        onChange={setQuery}
        onFocus={() => {
          if (screen === "home-idle") setScreen("home-typing");
        }}
        onSubmit={() => void submitQuestion(query)}
      />
    </div>
  );
}
