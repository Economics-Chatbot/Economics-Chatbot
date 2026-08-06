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

  return (
    <div className="chunk-term-card">
      <div className="chunk-term-header">
        <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
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
