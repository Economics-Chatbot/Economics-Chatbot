import type { ReactNode } from "react";

type RelatedKeywordChipProps = {
  children: ReactNode;
  variant?: "related" | "candidate" | "tag";
  onClick: () => void;
};

export function RelatedKeywordChip({ children, variant = "related", onClick }: RelatedKeywordChipProps) {
  return (
    <button
      type="button"
      className={`ui-related-term-button ui-related-term-button--${variant}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
