"use client";

import { FormEvent, useRef, useState } from "react";

import { streamAnswers, type AnswerCard } from "../lib/answers";
import type {
  AnswerDoneData,
  AnswerStartData,
  DeltaData,
  DoneData,
  ErrorData,
  FailureData,
  SuggestionsData,
} from "../types/answers";

export default function Home() {
  const [query, setQuery] = useState("");
  const [cards, setCards] = useState<AnswerCard[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestionsData[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const controller = useRef<AbortController | null>(null);

  const updateCard = (index: number, update: Partial<AnswerCard>) =>
    setCards((current) => current.map((card) => (card.index === index ? { ...card, ...update } : card)));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim() || loading) return;
    controller.current = new AbortController();
    setCards([]);
    setSuggestions([]);
    setMessage("");
    setLoading(true);
    try {
      await streamAnswers(query.trim(), {
        onAnswerStart: ({ index, term }: AnswerStartData) =>
          setCards((current) => [...current, { index, term, text: "", status: "streaming" }]),
        onDelta: ({ index, text }: DeltaData) =>
          setCards((current) => current.map((card) => card.index === index ? { ...card, text: card.text + text } : card)),
        onAnswerDone: ({ index, answer }: AnswerDoneData) => updateCard(index, { answer, status: "completed" }),
        onSuggestions: (data: SuggestionsData) => setSuggestions((current) => [...current, data]),
        onFailure: ({ index, term, message: failureMessage }: FailureData) => setCards((current) => {
          const card = current.find((item) => item.index === index);
          return card
            ? current.map((item) => item.index === index ? { ...item, status: "failure", message: failureMessage } : item)
            : [...current, { index, term, text: "", status: "failure", message: failureMessage }];
        }),
        onError: ({ index, message: errorMessage }: ErrorData) => {
          if (index === null) setMessage(errorMessage);
          else updateCard(index, { status: "error", message: errorMessage });
        },
        onDone: ({ status }: DoneData) => {
          if (status !== "completed") setMessage(status === "partial" ? "일부 용어만 답변했습니다." : "답변을 완료하지 못했습니다.");
        },
      }, controller.current.signal);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) setMessage("답변 요청 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
      controller.current = null;
    }
  };

  return (
    <main className="chatScreen">
      <h1>EconomyMate</h1>
      <p>경제금융용어를 쉽게 설명해 드립니다.</p>
      <form onSubmit={submit} className="questionForm">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="궁금한 경제용어를 입력하세요" />
        {loading ? <button type="button" onClick={() => controller.current?.abort()}>취소</button> : <button type="submit">질문하기</button>}
      </form>
      {message && <p role="status">{message}</p>}
      {cards.map((card) => (
        <article className="answerCard" key={card.index}>
          <h2>{card.term}</h2>
          <p>{card.text}</p>
          {card.answer && <><p>{card.answer.example}</p><small>관련 검색어: {card.answer.related_keywords.join(", ")}</small></>}
          {card.message && <p role="alert">{card.message}</p>}
        </article>
      ))}
      {suggestions.map((item) => <section key={item.index}><h2>후보 용어</h2><p>{item.suggestions.map((suggestion) => suggestion.term).join(", ")}</p></section>)}
    </main>
  );
}
