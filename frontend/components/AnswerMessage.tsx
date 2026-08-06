import type { RetrievedTerm } from "@/types/answers";
import { RelatedKeywordChip } from "@/components/RelatedKeywordChip";

export type AnswerMessageData = {
  id: string;
  term: RetrievedTerm;
  content: string;
};

type AnswerMessageProps = {
  message: AnswerMessageData;
  onKeywordClick: (keyword: string) => void;
};

function firstSentence(text: string): string {
  const normalized = text.trim();
  const match = normalized.match(/^.*?[.!?。](?:\s|$)/);
  return (match?.[0] ?? normalized).trim();
}

export function AnswerMessage({ message, onKeywordClick }: AnswerMessageProps) {
  const { term, content } = message;

  return (
    <div className="chunk-term-card">
      <div className="chunk-term-header">
        <div className="ui-term-eyebrow">한국은행 경제금융용어</div>
        <div className="ui-term-name">{term.term_name}</div>
        <div className="answer-term-definition">{firstSentence(content)}</div>
      </div>

      <div className="chunk-answer-content">
        <div className="answer-section">
          <div className="answer-section-title">💡 쉬운 설명</div>
          <div className="answer-section-body">{content}</div>
        </div>

        <div className="answer-divider" />
        <div className="answer-section">
          <div className="answer-section-title">🏠 생활 속 예시</div>
          <div className="answer-section-body">
            {term.term_name}이(가) 변하면 대출 금리와 물가 등 생활 전반에 영향을 미쳐요.
          </div>
        </div>

        {term.related_terms.length > 0 && (
          <div className="answer-keywords">
            <div className="answer-keywords-label">관련 키워드</div>
            <div className="answer-keyword-list">
              {term.related_terms.slice(0, 3).map((keyword, index) => (
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
