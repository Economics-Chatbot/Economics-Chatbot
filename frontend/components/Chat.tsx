"use client";

import { FormEvent, useState } from "react";
import { Search, Send } from "lucide-react";

import { ChatResponse, askQuestion, getTerm } from "@/lib/api";

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; response: ChatResponse };

const SUGGESTED_QUESTIONS = [
  "인플레이션이 뭐야?",
  "물가가 계속 오르는 현상이 뭐야?",
  "기준금리가 오르면 왜 대출 이자가 올라?",
];

export function Chat() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitQuestion(question: string) {
    const trimmedQuery = question.trim();

    if (!trimmedQuery) {
      setError("질문을 입력해주세요.");
      return;
    }

    setError("");
    setIsLoading(true);
    setMessages((current) => [...current, { role: "user", content: trimmedQuery }]);
    setQuery("");

    try {
      const response = await askQuestion(trimmedQuery);
      setMessages((current) => [...current, { role: "assistant", response }]);
    } catch {
      setError("서버 응답에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsLoading(false);
    }
  }

  async function openTerm(term: string) {
    setError("");
    setIsLoading(true);
    setMessages((current) => [...current, { role: "user", content: term }]);

    try {
      const response = await getTerm(term);
      setMessages((current) => [...current, { role: "assistant", response }]);
    } catch {
      setError("용어를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(query);
  }

  return (
    <main className="shell">
      <section className="intro">
        <p className="eyebrow">EconomyMate</p>
        <h1>경제용어를 쉬운 말로 풀어주는 챗봇</h1>
        <p>한국은행 경제금융용어 800선을 근거로 답변합니다.</p>
      </section>

      <section className="chatPanel" aria-live="polite">
        <div className="messages">
          {messages.length === 0 ? (
            <div className="emptyState">
              <strong>질문을 입력해보세요.</strong>
              <span>경제용어나 경제 현상을 자연스럽게 물어볼 수 있습니다.</span>
              <div className="suggestions" aria-label="추천 질문">
                {SUGGESTED_QUESTIONS.map((suggestion) => (
                  <button
                    disabled={isLoading}
                    key={suggestion}
                    onClick={() => void submitQuestion(suggestion)}
                    type="button"
                  >
                    <Search size={14} />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => {
              if (message.role === "user") {
                return (
                  <div className="message userMessage" key={`${message.role}-${index}`}>
                    {message.content}
                  </div>
                );
              }

              const { answer, failure_message } = message.response;
              return (
                <div className="message assistantMessage" key={`${message.role}-${index}`}>
                  {answer ? (
                    <>
                      <h2>{answer.term}</h2>
                      <dl>
                        <dt>한 줄 정의</dt>
                        <dd>{answer.one_line}</dd>
                        <dt>쉽게 설명하면</dt>
                        <dd>{answer.easy_explanation}</dd>
                        <dt>생활 속 예시</dt>
                        <dd>{answer.example}</dd>
                        <dt>관련 키워드</dt>
                        <dd>
                          {answer.related_terms.length > 0 ? (
                            <div className="termTags">
                              {answer.related_terms.map((term) => (
                                <button
                                  disabled={isLoading}
                                  key={term}
                                  onClick={() => void openTerm(term)}
                                  type="button"
                                >
                                  {term}
                                </button>
                              ))}
                            </div>
                          ) : (
                            "관련 키워드 없음"
                          )}
                        </dd>
                        <dt>출처</dt>
                        <dd>
                          {answer.source_name}
                          {answer.source_page ? `, ${answer.source_page}쪽` : ""}
                        </dd>
                      </dl>
                    </>
                  ) : (
                    <p>{failure_message}</p>
                  )}
                </div>
              );
            })
          )}
          {isLoading && <div className="message assistantMessage">답변을 준비하고 있습니다.</div>}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <input
            maxLength={300}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="경제용어나 경제 현상을 질문해보세요"
            value={query}
          />
          <button aria-label="질문 보내기" disabled={isLoading || !query.trim()} type="submit">
            <Send size={18} />
          </button>
        </form>
        {error && <p className="errorText">{error}</p>}
      </section>
    </main>
  );
}
