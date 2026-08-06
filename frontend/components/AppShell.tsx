"use client";

import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { ArrowLeft, ChartNoAxesColumnIncreasing, CircleHelp, PieChart } from "lucide-react";
import type { Answer, AnswerDoneData, AnswerSection, AnswerStartData, DeltaData, Suggestion } from "@/types/answers";
import type { CharacterState, ScreenState } from "@/types/ui";
import { ChatInput } from "@/components/ChatInput";
import { SuggestedQuestions, type SuggestedQuestion } from "@/components/SuggestedQuestions";
import { UserMessage } from "@/components/UserMessage";
import { ErrorCard } from "@/components/ErrorCard";
import { RelatedKeywordChip } from "@/components/RelatedKeywordChip";
import { MessageList } from "@/components/MessageList";
import { AnswerMessage, type AnswerMessageData } from "@/components/AnswerMessage";
import { LoadingCard } from "@/components/LoadingCard";
import { AnswerNetworkError, streamAnswers, streamTermAnswer } from "@/lib/answers";

type ChatMessage =
  | { id: string; type: "user"; text: string }
  | { id: string; type: "answer"; data: AnswerMessageData };

const EMPTY_SECTIONS: Record<AnswerSection, string> = {
  one_line_definition: "",
  easy_explanation: "",
  example: "",
};

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
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [failureMsg, setFailureMsg] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  
  const [isOrangeJelly, setIsOrangeJelly] = useState(false);
  const requestTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const characterLayout = screen === "home-idle" || screen === "home-typing" ? "home" : "result";

  const clearRequestTimers = () => {
    requestTimersRef.current.forEach(clearTimeout);
    requestTimersRef.current = [];
  };

  useEffect(() => {
    if (screen !== "home-idle" && screen !== "home-typing") return;

    let blinkTimer: ReturnType<typeof setTimeout>;
    let openTimer: ReturnType<typeof setTimeout>;
    const scheduleMotion = () => {
      blinkTimer = setTimeout(() => {
        // 20% 확률로 서서히 주황색 젤리로 변신!
        if (Math.random() < 0.20) {
          setIsOrangeJelly(true);
          setTimeout(() => setIsOrangeJelly(false), 3800);
        }

        const isThinking = Math.random() < 0.35;
        const nextState: CharacterState = isThinking ? "thinking" : "blink";
        const duration = isThinking ? 1200 : 300;

        setCharacter(nextState);
        openTimer = setTimeout(() => {
          setCharacter("default");
          scheduleMotion();
        }, duration);
      }, 2500 + Math.random() * 1800);
    };

    setCharacter("default");
    scheduleMotion();
    return () => {
      clearTimeout(blinkTimer);
      clearTimeout(openTimer);
    };
  }, [screen]);

  useEffect(() => () => {
    clearRequestTimers();
    abortControllerRef.current?.abort();
  }, []);

  const handleSuggestionClick = (suggestionText: string) => {
    void submitQuestion(suggestionText, "query");
  };

  const submitQuestion = async (rawQuery: string, mode: "query" | "term" = "query") => {
    const trimmedQuery = rawQuery.trim();
    if (!trimmedQuery) return;
    if (["query-transition", "searching", "answer-streaming"].includes(screen)) return;

    clearRequestTimers();
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

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

    setScreen("searching");
    setCharacter("thinking");

    const updateAnswer = (index: number, update: (data: AnswerMessageData) => AnswerMessageData) => {
      const cardId = `${answerId}-${index}`;
      setChatMessages((current) => current.map((message) => (
        message.type === "answer" && message.id === cardId
          ? { ...message, data: update(message.data) }
          : message
      )));
    };

    try {
      const stream = mode === "term" ? streamTermAnswer : streamAnswers;
      await stream(trimmedQuery, {
        onAnswerStart: (data: AnswerStartData) => {
          setChatMessages((current) => [
            ...current,
            {
              id: `${answerId}-${data.index}`,
              type: "answer",
              data: {
                id: `${answerId}-${data.index}`,
                index: data.index,
                term: data.term,
                relatedKeywords: data.related_keywords,
                sections: { ...EMPTY_SECTIONS },
              },
            },
          ]);
          setScreen("answer-streaming");
        },
        onDelta: (data: DeltaData) => {
          updateAnswer(data.index, (current) => ({
            ...current,
            sections: {
              ...current.sections,
              [data.section]: current.sections[data.section] + data.text,
            },
          }));
        },
        onAnswerDone: (data: AnswerDoneData) => {
          updateAnswer(data.index, (current) => ({
            ...current,
            term: data.answer.term,
            relatedKeywords: data.answer.related_keywords,
            answer: data.answer,
            sections: {
              one_line_definition: data.answer.one_line_definition,
              easy_explanation: data.answer.easy_explanation,
              example: data.answer.example,
            },
          }));
        },
        onSuggestions: (data) => {
          setSuggestions(data.suggestions.map((suggestion, index) => ({
            term_id: index,
            term: suggestion.term,
            query: data.query,
            reason: suggestion.reason,
          })));
          setScreen("suggestions");
        },
        onFailure: (data) => {
          setFailureMsg(data.message);
          setScreen("failure");
        },
        onError: (data) => {
          setErrorMsg(data.message);
          setScreen("error");
          setCharacter("error");
        },
        onDone: (data) => {
          setScreen(data.status === "error" ? "error" : data.status === "failed" ? "failure" : data.status === "suggestions" ? "suggestions" : "answer-done");
          setCharacter(data.status === "error" ? "error" : "default");
        },
      }, controller.signal);
    } catch (error) {
      if (controller.signal.aborted) return;
      setErrorMsg(error instanceof AnswerNetworkError ? error.message : "답변 요청을 처리하지 못했어요.");
      setScreen("error");
      setCharacter("error");
    } finally {
      if (abortControllerRef.current === controller) abortControllerRef.current = null;
    }
  };

  const handleBack = () => {
    clearRequestTimers();
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setScreen("home-idle");
    setCharacter("default");
    setUserQueryBubble("");
    setChatMessages([]);
    setSuggestions([]);
  };

  const handleCancel = () => {
    clearRequestTimers();
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setScreen("answer-done");
    setCharacter("default");
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
        <div className="ui-header-jelly-button" title="옐로 메이트">
          <Image
            src="/assets/character-default.png"
            alt="노란 젤리 메이트"
            width={32}
            height={32}
            className="ui-header-jelly-img"
            unoptimized
          />
        </div>
      </header>

      {/* 캐릭터 스테이지 & 3D 장식들 */}
      <div className="chunk-character-stage">
        <div className={`ui-character-wrapper ${isOrangeJelly ? "theme-orange-jelly" : ""}`}>
          {/* 이미지 1: 기본 미소 (눈 뜬 상태) */}
          <Image
            src="/assets/character-default.png"
            alt="옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image ${character === "default" || character === "blink" || character === "thinking" ? "active" : ""}`}
            priority
            unoptimized
          />
          {/* 이미지 2: 위 쳐다보는 생각 표정 */}
          <Image
            src="/assets/character-thinking.png"
            alt="생각하는 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image thinking-frame ${character === "thinking" ? "active" : ""}`}
            unoptimized
          />
          {/* 눈 감기 깜빡임 프레임 */}
          <Image
            src="/assets/character-complete.png"
            alt="눈 감은 옐로 메이트"
            width={184}
            height={184}
            className={`ui-character-image blink-frame ${character === "blink" ? "active" : ""}`}
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
        <div className="home-content-wrapper">
          <div className="chunk-home-intro">
            <h1 className="type-home-title">
              {"궁금한 경제용어,\n편하게 물어보세요"}
            </h1>
          </div>

          <div className="chunk-home-guide">어려운 경제를 쉽고 친근하게 설명해드릴게요.</div>

          <SuggestedQuestions items={HOME_SUGGESTIONS} onSelect={handleSuggestionClick} />
        </div>
      </div>

      {/* 모든 질문 결과 화면 (성공, 후보, 실패, 에러 포함) */}
      <div className="result-only">
        <MessageList
          scrollKey={`${screen}:${chatMessages.map((message) => message.id + (message.type === "answer" ? JSON.stringify(message.data.sections) : message.text)).join("|")}:${suggestions.length}`}
        >
          {chatMessages.map((message) => message.type === "user" ? (
            <UserMessage key={message.id}>{message.text}</UserMessage>
          ) : (
            <AnswerMessage
              key={message.id}
              message={message.data}
              onKeywordClick={(keyword) => void submitQuestion(keyword, "term")}
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
                    onClick={() => void submitQuestion(item.term, "term")}
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
              description={failureMsg || "용어 이름이나 약어를 조금 더 정확하게 입력해 주세요."}
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
        disabled={["query-transition", "searching", "answer-streaming"].includes(screen)}
        onCancel={handleCancel}
        onChange={setQuery}
        onFocus={() => {
          if (screen === "home-idle") setScreen("home-typing");
        }}
        onSubmit={() => void submitQuestion(query)}
      />
    </div>
  );
}
