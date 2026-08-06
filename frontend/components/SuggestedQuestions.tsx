import type { ReactNode } from "react";

export type SuggestedQuestion = {
  text: string;
  icon: ReactNode;
};

type SuggestedQuestionsProps = {
  items: SuggestedQuestion[];
  onSelect: (question: string) => void;
};

export function SuggestedQuestions({ items, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="chunk-home-suggestions">
      <div className="ui-section-title-left">이런 질문은 어때요?</div>
      {items.map((item) => (
        <button
          key={item.text}
          type="button"
          className="ui-suggestion-pill-button"
          onClick={() => onSelect(item.text)}
        >
          <span className="icon-chip-circle">{item.icon}</span>
          <span>{item.text}</span>
        </button>
      ))}
    </div>
  );
}
