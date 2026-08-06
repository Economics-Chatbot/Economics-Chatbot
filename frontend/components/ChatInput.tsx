"use client";

import type { ChangeEvent, FormEvent, KeyboardEvent } from "react";
import { Send } from "lucide-react";

type ChatInputProps = {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onFocus?: () => void;
  onSubmit: () => void;
};

export function ChatInput({
  value,
  disabled = false,
  onChange,
  onFocus,
  onSubmit,
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
      <button
        className="ui-send-button"
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="질문 보내기"
      >
        <Send size={20} strokeWidth={2.5} aria-hidden="true" />
      </button>
    </form>
  );
}
