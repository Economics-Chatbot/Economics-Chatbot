"use client";

import { useEffect, useRef, type ReactNode } from "react";

type MessageListProps = {
  children: ReactNode;
  scrollKey: string | number;
};

export function MessageList({ children, scrollKey }: MessageListProps) {
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, [scrollKey]);

  return (
    <div className="chunk-answer-viewport" ref={viewportRef}>
      {children}
    </div>
  );
}
