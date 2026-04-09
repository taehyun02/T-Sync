import { useState } from "react";

import { runPrediction } from "../api/tsyncApi";
import PredictionForm from "../components/PredictionForm";
import PredictionResult from "../components/PredictionResult";
import RouteSearchPanel from "../components/RouteSearchPanel";
import TransferStationPicker from "../components/TransferStationPicker";
import VehiclePicker from "../components/VehiclePicker";

export default function DashboardPage() {
  const [currentRoute, setCurrentRoute] = useState(null);
  const [targetRoute, setTargetRoute] = useState(null);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [userId, setUserId] = useState("demo-user-001");
  const [mobilityProfile, setMobilityProfile] = useState("normal");
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionError, setPredictionError] = useState("");
  const [predicting, setPredicting] = useState(false);

  async function handleRunPrediction() {
    if (!currentRoute || !targetRoute || !selectedVehicle || !selectedStation) {
      setPredictionError("현재 노선, 목표 노선, 차량, 환승 정류장을 모두 선택해야 합니다.");
      return;
    }

    setPredicting(true);
    setPredictionError("");

    try {
      const result = await runPrediction({
        user_id: userId.trim() || "demo-user-001",
        vehicle_position_id: selectedVehicle.vehicle_position_id,
        target_route_id: targetRoute.route_id,
        transfer_station_id: selectedStation.station_id,
        mobility_profile: mobilityProfile,
      });
      setPredictionResult(result);
    } catch (err) {
      setPredictionResult(null);
      setPredictionError(err.message);
    } finally {
      setPredicting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">T-Sync</span>
          <h1>실시간 버스 환승, 지금 갈아탈 수 있을지 미리 보는 서비스</h1>
          <p>
            실시간 버스 위치를 바탕으로 환승 가능성을 계산하고, 놓칠 가능성이 크면 다른 방법도 함께 안내합니다.
          </p>
        </div>
        <div className="hero-summary">
          <div>
            <span>핵심 차별점</span>
            <strong>ETA가 아니라 환승 성공 가능성</strong>
          </div>
          <div>
            <span>공공데이터 활용</span>
            <strong>실시간 위치와 정류장 순서 결합</strong>
          </div>
          <div>
            <span>서비스 흐름</span>
            <strong>입력 → 예측 → 대안 추천</strong>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <RouteSearchPanel
          label="Step 1-A"
          title="현재 탑승 노선 선택"
          selectedRouteId={currentRoute?.route_id}
          onSelectRoute={(route) => {
            setCurrentRoute(route);
            setSelectedVehicle(null);
            setSelectedStation(null);
            setPredictionResult(null);
          }}
        />
        <RouteSearchPanel
          label="Step 1-B"
          title="목표 환승 노선 선택"
          selectedRouteId={targetRoute?.route_id}
          onSelectRoute={(route) => {
            setTargetRoute(route);
            setSelectedStation(null);
            setPredictionResult(null);
          }}
        />
        <VehiclePicker
          route={currentRoute}
          selectedVehicleId={selectedVehicle?.vehicle_position_id}
          onSelectVehicle={(vehicle) => {
            setSelectedVehicle(vehicle);
            setPredictionResult(null);
          }}
        />
        <TransferStationPicker
          currentRoute={currentRoute}
          targetRoute={targetRoute}
          selectedStationId={selectedStation?.station_id}
          onSelectStation={(station) => {
            setSelectedStation(station);
            setPredictionResult(null);
          }}
        />
        <PredictionForm
          userId={userId}
          mobilityProfile={mobilityProfile}
          onChangeUserId={setUserId}
          onChangeProfile={setMobilityProfile}
          onSubmit={handleRunPrediction}
          disabled={!currentRoute || !targetRoute || !selectedVehicle || !selectedStation}
          loading={predicting}
        />
        <PredictionResult result={predictionResult} error={predictionError} />
      </section>
    </main>
  );
}
