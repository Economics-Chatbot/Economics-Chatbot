import React, { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { Answer, AnswerSection } from "@/types/answers";
import { RelatedKeywordChip } from "@/components/RelatedKeywordChip";

export type AnswerMessageData = {
  id: string;
  index: number;
  term: string;
  relatedKeywords: string[];
  sections: Record<AnswerSection, string>;
  answer?: Answer;
};

type AnswerMessageProps = {
  message: AnswerMessageData;
  onKeywordClick: (keyword: string) => void;
};

export function AnswerMessage({ message, onKeywordClick }: AnswerMessageProps) {
  const { term, relatedKeywords, sections, answer } = message;
  const keywords = answer?.related_keywords ?? [];
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = [
      term,
      sections.one_line_definition,
      "💡 쉬운 설명",
      sections.easy_explanation,
      "🏠 생활 속 예시",
      sections.example,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard permission is optional; the answer remains usable without it.
    }
  };

  return (
    <div className="chunk-term-card">
      <div className="chunk-term-header">
        <div className="ui-term-eyebrow-row">
          <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
          <button
            type="button"
            className={`ui-copy-button ${copied ? "copied" : ""}`}
            onClick={handleCopy}
            aria-label="용어 설명 복사하기"
          >
            {copied ? <Check size={15} /> : <Copy size={15} />}
            <span>{copied ? "복사됨" : "복사"}</span>
          </button>
        </div>
        <div className="ui-term-name">{term}</div>
        <div className="answer-term-definition">{sections.one_line_definition}</div>
      </div>

      <div className="chunk-answer-content">
        <div className="answer-section">
          <div className="answer-section-title">💡 쉬운 설명</div>
          <div className="answer-section-body">{sections.easy_explanation}</div>
        </div>

        <div className="answer-divider" />
        <div className="answer-section">
          <div className="answer-section-title">🏠 생활 속 예시</div>
          <div className="answer-section-body">
            {sections.example}
          </div>
        </div>

        {keywords.length > 0 && (
          <div className="answer-keywords">
            <div className="answer-keywords-label">관련 키워드</div>
            <div className="answer-keyword-list">
              {keywords.slice(0, 3).map((keyword, index) => (
                <RelatedKeywordChip
                  key={`${keyword}-${index}`}
                  variant="tag"
                  onClick={() => onKeywordClick(keyword)}
                >
                  {keyword}
                </RelatedKeywordChip>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
