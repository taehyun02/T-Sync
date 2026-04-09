import SectionCard from "./SectionCard";

function riskLabel(riskLevel) {
  if (riskLevel === "stable" || riskLevel === "safe") return "안정";
  if (riskLevel === "uncertain") return "불확실";
  return "위험";
}

export default function PredictionResult({ result, error }) {
  const currentArrivalSeconds =
    result?.source_arrival_seconds ?? result?.first_vehicle_eta_sec ?? null;
  const targetArrivalSeconds =
    result?.target_arrival_seconds ?? result?.second_vehicle_eta_sec ?? null;
  const walkingTimeSeconds =
    result?.walking_time_seconds ?? result?.walking_time_sec ?? null;
  const slackSeconds =
    result?.slack_seconds ?? result?.slack_time_sec ?? null;
  const recommendationCards = result?.recommendations ?? [];
  const recommendationTexts = result?.recommended_alternatives ?? [];

  return (
    <SectionCard
      eyebrow="Step 5"
      title="예측 결과"
      description="심사위원이 바로 이해할 수 있도록 핵심 지표와 대안 전략을 한 화면에서 보여줍니다."
    >
      {!result && !error ? <p className="helper-text">예측을 실행하면 결과가 여기에 표시됩니다.</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      {result ? (
        <div className="result-stack">
          <div className="hero-result">
            <div>
              <span className={`risk-badge ${result.risk_level}`}>{riskLabel(result.risk_level)}</span>
              <h3>{result.transfer_station_name} 환승 예측</h3>
              <p>
                성공 확률 <strong>{Math.round(result.success_probability * 100)}%</strong>
              </p>
            </div>
            <div className="metric-grid">
              <div className="metric-card">
                <span>현재 차량 도착</span>
                <strong>{currentArrivalSeconds ?? "-"}초</strong>
              </div>
              <div className="metric-card">
                <span>목표 차량 도착</span>
                <strong>{targetArrivalSeconds ?? "-"}초</strong>
              </div>
              <div className="metric-card">
                <span>보행 시간</span>
                <strong>{walkingTimeSeconds ?? "-"}초</strong>
              </div>
              <div className="metric-card">
                <span>환승 여유시간</span>
                <strong>{slackSeconds ?? "-"}초</strong>
              </div>
            </div>
          </div>

          {result.warning_reason ? (
            <div className="warning-panel">
              <strong>리스크 해석</strong>
              <p>{result.warning_reason}</p>
            </div>
          ) : null}

          {recommendationCards.length > 0 ? (
            <div className="recommendation-list">
              {recommendationCards.map((item, index) => (
                <article key={`${item.strategy}-${item.transfer_station_id}-${index}`} className="recommendation-card">
                  <div className="recommendation-top">
                    <span>{index === 0 ? "최우선 전략" : `대안 ${index}`}</span>
                    <strong>{item.strategy}</strong>
                  </div>
                  <p>{item.transfer_station_name}</p>
                  <div className="recommendation-stats">
                    <span>성공 확률 {Math.round(item.success_probability * 100)}%</span>
                    <span>여유시간 {item.slack_seconds}초</span>
                  </div>
                  <small>{item.summary}</small>
                </article>
              ))}
            </div>
          ) : null}

          {recommendationTexts.length > 0 ? (
            <div className="recommendation-list">
              {recommendationTexts.map((text, index) => (
                <article key={`${text}-${index}`} className="recommendation-card">
                  <div className="recommendation-top">
                    <span>{index === 0 ? "추천 전략" : `대안 ${index}`}</span>
                    <strong>{text}</strong>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
