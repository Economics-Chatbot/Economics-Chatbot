type ErrorCardProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function ErrorCard({ title, description, actionLabel, onAction }: ErrorCardProps) {
  return (
    <div className="chunk-status-feedback" role="alert">
      <div className="feedback-title">{title}</div>
      <div className="feedback-desc">{description}</div>
      {actionLabel && onAction && (
        <button type="button" className="feedback-action-button" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
