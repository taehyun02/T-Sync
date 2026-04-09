import { useEffect, useMemo, useState } from "react";

import { fetchRouteStations, searchStations } from "../api/tsyncApi";
import SectionCard from "./SectionCard";

export default function TransferStationPicker({
  currentRoute,
  targetRoute,
  selectedStationId,
  onSelectStation,
}) {
  const [currentStations, setCurrentStations] = useState([]);
  const [keyword, setKeyword] = useState("");
  const [stationResults, setStationResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!currentRoute?.route_id) {
      setCurrentStations([]);
      return;
    }

    let cancelled = false;

    async function loadStations() {
      setLoading(true);
      setError("");

      try {
        const data = await fetchRouteStations(currentRoute.route_id);
        if (!cancelled) {
          setCurrentStations(data);
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

    loadStations();

    return () => {
      cancelled = true;
    };
  }, [currentRoute]);

  useEffect(() => {
    let cancelled = false;

    async function loadSearch() {
      if (!keyword.trim()) {
        setStationResults([]);
        return;
      }

      try {
        const data = await searchStations(keyword.trim(), 12);
        if (!cancelled) {
          setStationResults(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    loadSearch();

    return () => {
      cancelled = true;
    };
  }, [keyword]);

  const visibleStations = useMemo(() => {
    if (keyword.trim()) {
      const allowedIds = new Set(currentStations.map((station) => station.station_id));
      return stationResults.filter((station) => allowedIds.has(station.station_id));
    }

    return currentStations.slice(0, 20);
  }, [currentStations, keyword, stationResults]);

  return (
    <SectionCard
      eyebrow="Step 3"
      title="환승 정류장 선택"
      description="현재 노선에서 어디서 갈아탈지 정류장을 골라주세요."
    >
      {!currentRoute || !targetRoute ? (
        <p className="helper-text">현재 탑승 노선과 환승할 노선을 먼저 선택해 주세요.</p>
      ) : null}
      <input
        className="text-input"
        value={keyword}
        onChange={(event) => setKeyword(event.target.value)}
        placeholder="정류장 이름 검색"
      />
      {loading ? <p className="helper-text">정류장 정보를 불러오는 중입니다.</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      <div className="list-grid compact">
        {visibleStations.map((station) => (
          <button
            key={station.station_id}
            type="button"
            className={`select-card ${selectedStationId === station.station_id ? "selected" : ""}`}
            onClick={() => onSelectStation(station)}
          >
            <strong>{station.station_name}</strong>
            <span>정류장 ID {station.station_id}</span>
            <small>순서 {station.station_sequence ?? "-"}</small>
          </button>
        ))}
      </div>
    </SectionCard>
  );
}
