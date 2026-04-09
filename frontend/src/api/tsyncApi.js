const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = "요청 처리 중 오류가 발생했습니다.";

    try {
      const data = await response.json();
      if (data?.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Ignore JSON parsing error and use default message.
    }

    throw new Error(message);
  }

  return response.json();
}

export function fetchRoutes() {
  return request("/routes");
}

export function searchRoutes(keyword) {
  return request(`/routes/search?keyword=${encodeURIComponent(keyword)}`);
}

export function fetchRouteStations(routeId) {
  return request(`/routes/${routeId}/stations`);
}

export function searchStations(keyword, limit = 20) {
  return request(`/stations/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`);
}

export function fetchVehiclesByRoute(routeId) {
  return request(`/vehicles/by-route/${routeId}`);
}

export function runPrediction(payload) {
  return request("/predictions/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
