type ErrorCardProps = {
  title: string;
  description: string;
};

export function ErrorCard({ title, description }: ErrorCardProps) {
  return (
    <div className="chunk-status-feedback" role="alert">
      <div className="feedback-title">{title}</div>
      <div className="feedback-desc">{description}</div>
    </div>
  );
}
