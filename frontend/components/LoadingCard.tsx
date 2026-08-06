export function LoadingCard() {
  return (
    <div className="chunk-status-feedback" role="status" aria-live="polite">
      <div className="feedback-title">관련 용어를 검색하고 있어요...</div>
      <div className="feedback-desc">한국은행 경제금융용어 800선 DB를 분석 중입니다.</div>
    </div>
  );
}
