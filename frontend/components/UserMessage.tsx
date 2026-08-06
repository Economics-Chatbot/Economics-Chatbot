type UserMessageProps = {
  children: string;
};

export function UserMessage({ children }: UserMessageProps) {
  return <div className="chunk-query-bubble">{children}</div>;
}
