import SectionCard from "./SectionCard";

const profiles = [
  { value: "fast", label: "빠른 이동형", description: "보행 여유시간 60초 기준" },
  { value: "normal", label: "일반 이동형", description: "보행 여유시간 90초 기준" },
  { value: "slow", label: "느린 이동형", description: "보행 여유시간 140초 기준" },
];

export default function PredictionForm({
  userId,
  mobilityProfile,
  onChangeUserId,
  onChangeProfile,
  onSubmit,
  disabled,
  loading,
}) {
  return (
    <SectionCard
      eyebrow="Step 4"
      title="환승 예측 실행"
      description="사용자 프로필을 선택한 뒤 환승 성공 확률과 대안 전략을 계산합니다."
    >
      <div className="form-grid">
        <label className="field">
          <span>사용자 식별값</span>
          <input
            className="text-input"
            value={userId}
            onChange={(event) => onChangeUserId(event.target.value)}
            placeholder="demo-user-001"
          />
        </label>
        <div className="profile-row">
          {profiles.map((profile) => (
            <button
              key={profile.value}
              type="button"
              className={`profile-chip ${mobilityProfile === profile.value ? "selected" : ""}`}
              onClick={() => onChangeProfile(profile.value)}
            >
              <strong>{profile.label}</strong>
              <span>{profile.description}</span>
            </button>
          ))}
        </div>
        <button type="button" className="primary-button" onClick={onSubmit} disabled={disabled || loading}>
          {loading ? "예측 계산 중..." : "환승 성공 확률 계산"}
        </button>
      </div>
    </SectionCard>
  );
}
