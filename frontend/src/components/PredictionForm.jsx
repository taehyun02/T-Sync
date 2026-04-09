import SectionCard from "./SectionCard";

const profiles = [
  {
    value: "fast",
    label: "빠르게 걷는 편",
    description: "예: 평소 걸음이 빠른 경우",
  },
  {
    value: "normal",
    label: "보통 걸음",
    description: "예: 평소 보통 속도로 이동하는 경우",
  },
  {
    value: "slow",
    label: "천천히 걷는 편",
    description: "예: 교통약자, 임산부, 짐이 많은 경우",
  },
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
      description="평소 걷는 속도에 맞게 선택한 뒤 환승 가능성을 확인해 보세요."
    >
      <div className="form-grid">
        <label className="field">
          <span>사용자 이름</span>
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
          {loading ? "계산 중..." : "환승 가능성 보기"}
        </button>
      </div>
    </SectionCard>
  );
}
