import { useEffect, useState } from "react";

import { fetchRoutes, searchRoutes } from "../api/tsyncApi";
import SectionCard from "./SectionCard";

export default function RouteSearchPanel({
  label,
  title,
  selectedRouteId,
  onSelectRoute,
}) {
  const [keyword, setKeyword] = useState("");
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const data = keyword.trim() ? await searchRoutes(keyword.trim()) : await fetchRoutes();
        if (!cancelled) {
          setRoutes(data.slice(0, 12));
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
  }, [keyword]);

  return (
    <SectionCard
      eyebrow={label}
      title={title}
      description="노선 번호나 기점, 종점을 검색해서 환승 경로를 골라보세요."
    >
      <div className="control-stack">
        <input
          className="text-input"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="예: 401, 울산역, 시청"
        />
        {loading ? <p className="helper-text">노선 정보를 불러오는 중입니다.</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <div className="list-grid">
          {routes.map((route) => (
            <button
              key={route.route_id}
              type="button"
              className={`select-card ${selectedRouteId === route.route_id ? "selected" : ""}`}
              onClick={() => onSelectRoute(route)}
            >
              <strong>{route.route_no}</strong>
              <span>
                {route.start_stop} → {route.end_stop}
              </span>
              <small>{route.route_type || "노선 유형 정보 없음"}</small>
            </button>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
