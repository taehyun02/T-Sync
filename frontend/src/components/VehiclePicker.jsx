import { useEffect, useState } from "react";

import { fetchVehiclesByRoute } from "../api/tsyncApi";
import SectionCard from "./SectionCard";

export default function VehiclePicker({
  route,
  selectedVehicleId,
  onSelectVehicle,
}) {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!route?.route_id) {
      setVehicles([]);
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const data = await fetchVehiclesByRoute(route.route_id);
        if (!cancelled) {
          setVehicles(data.slice(0, 10));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [route]);

  return (
    <SectionCard
      eyebrow="Step 2"
      title="현재 탑승 버스 선택"
      description="실시간 위치가 잡힌 버스 중에서 지금 타고 있는 버스를 골라주세요."
    >
      {!route ? <p className="helper-text">먼저 현재 탑승 노선을 선택해 주세요.</p> : null}
      {loading ? <p className="helper-text">버스 정보를 불러오는 중입니다.</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      <div className="list-grid">
        {vehicles.map((vehicle) => (
          <button
            key={vehicle.vehicle_position_id}
            type="button"
            className={`select-card ${selectedVehicleId === vehicle.vehicle_position_id ? "selected" : ""}`}
            onClick={() => onSelectVehicle(vehicle)}
          >
            <strong>{vehicle.vehicle_no}</strong>
            <span>속도 {vehicle.operation_speed ?? "-"} km/h</span>
            <small>{vehicle.collected_at ?? "수집 시각 정보 없음"}</small>
          </button>
        ))}
      </div>
    </SectionCard>
  );
}
