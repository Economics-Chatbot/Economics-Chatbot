"use client";

import type { ChangeEvent, FormEvent, KeyboardEvent } from "react";
import { Send, X } from "lucide-react";

type ChatInputProps = {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onFocus?: () => void;
  onSubmit: () => void;
  onCancel?: () => void;
};

export function ChatInput({
  value,
  disabled = false,
  onChange,
  onFocus,
  onSubmit,
  onCancel,
}: ChatInputProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!disabled && value.trim()) onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim()) onSubmit();
    }
  };

  return (
    <form className="chunk-input-dock" onSubmit={handleSubmit}>
      <textarea
        className="ui-textarea"
        placeholder="경제용어를 물어보세요"
        value={value}
        disabled={disabled}
        aria-label="경제용어 질문"
        onFocus={onFocus}
        onChange={(event: ChangeEvent<HTMLTextAreaElement>) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      {disabled && onCancel ? (
        <button className="ui-send-button" type="button" onClick={onCancel} aria-label="답변 생성 취소">
          <X size={20} strokeWidth={2.5} aria-hidden="true" />
        </button>
      ) : (
        <button className="ui-send-button" type="submit" disabled={!value.trim()} aria-label="질문 보내기">
          <Send size={20} strokeWidth={2.5} aria-hidden="true" />
        </button>
      )}
    </form>
  );
}
