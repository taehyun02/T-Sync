import math
from typing import Any


EARTH_RADIUS_M = 6371000
DEFAULT_BUS_SPEED_KMH = 18.0
PROFILE_WALKING_BUFFER = {
    "fast": 60,
    "normal": 90,
    "slow": 140,
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def _speed_to_mps(speed_kmh: float | None) -> float:
    speed = speed_kmh if speed_kmh and speed_kmh > 0 else DEFAULT_BUS_SPEED_KMH
    return max(speed * 1000 / 3600, 3.0)


def _estimate_arrival_seconds(
    distance_m: float,
    speed_kmh: float | None,
    remaining_stops: int,
) -> int:
    travel_seconds = distance_m / _speed_to_mps(speed_kmh)
    dwell_seconds = max(remaining_stops, 0) * 25
    signal_seconds = max(remaining_stops - 1, 0) * 15
    return int(travel_seconds + dwell_seconds + signal_seconds)


def _probability_from_slack(slack_seconds: int) -> float:
    probability = 1 / (1 + math.exp(-slack_seconds / 45))
    return round(max(0.01, min(0.99, probability)), 2)


def _risk_level(probability: float) -> str:
    if probability >= 0.7:
        return "stable"
    if probability >= 0.4:
        return "uncertain"
    return "warning"


def _warning_reason(
    probability: float,
    slack_seconds: int,
    target_eta_seconds: int | None,
) -> str | None:
    if probability >= 0.7:
        return None
    if target_eta_seconds is None:
        return "목표 노선의 도착 차량을 확인하지 못해 환승 성공 가능성을 낮게 평가했습니다."
    if slack_seconds < 0:
        return "환승 정류장 도착 후 이동 시간보다 목표 차량 도착이 더 빨라 환승 실패 위험이 큽니다."
    return "환승 여유 시간이 충분하지 않아 변동 상황에 따라 실패할 가능성이 있습니다."


def _fetch_route_stations(cur: Any, route_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            rs.station_id,
            rs.station_sequence,
            s.station_name,
            s.latitude,
            s.longitude
        FROM route_stations rs
        JOIN stations s
          ON rs.station_id = s.station_id
        WHERE rs.route_id = %s
        ORDER BY rs.station_sequence
        """,
        (route_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "station_id": row[0],
            "station_sequence": row[1],
            "station_name": row[2],
            "latitude": row[3],
            "longitude": row[4],
        }
        for row in rows
    ]


def _station_lookup(route_stations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {station["station_id"]: station for station in route_stations}


def _find_nearest_station(
    route_stations: list[dict[str, Any]],
    latitude: float | None,
    longitude: float | None,
) -> dict[str, Any] | None:
    if latitude is None or longitude is None:
        return None

    best_station = None
    best_distance = None

    for station in route_stations:
        if station["latitude"] is None or station["longitude"] is None:
            continue

        distance_m = _haversine_m(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"],
        )
        if best_distance is None or distance_m < best_distance:
            best_station = station
            best_distance = distance_m

    return best_station


def _estimate_vehicle_to_station(
    route_stations: list[dict[str, Any]],
    transfer_station_id: str,
    vehicle: dict[str, Any],
) -> dict[str, Any] | None:
    station_map = _station_lookup(route_stations)
    transfer_station = station_map.get(transfer_station_id)
    nearest_station = _find_nearest_station(
        route_stations,
        vehicle["latitude"],
        vehicle["longitude"],
    )

    if not transfer_station or not nearest_station:
        return None
    if transfer_station["latitude"] is None or transfer_station["longitude"] is None:
        return None

    remaining_stops = transfer_station["station_sequence"] - nearest_station["station_sequence"]
    if remaining_stops < -1:
        return None

    distance_m = _haversine_m(
        vehicle["latitude"],
        vehicle["longitude"],
        transfer_station["latitude"],
        transfer_station["longitude"],
    )
    eta_seconds = _estimate_arrival_seconds(
        distance_m,
        vehicle["operation_speed"],
        max(remaining_stops, 0),
    )

    return {
        "station": transfer_station,
        "nearest_station": nearest_station,
        "remaining_stops": max(remaining_stops, 0),
        "distance_m": round(distance_m, 1),
        "eta_seconds": eta_seconds,
    }


def _fetch_latest_route_vehicles(cur: Any, route_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT DISTINCT ON (vehicle_no)
            vehicle_position_id,
            vehicle_no,
            route_id,
            latitude,
            longitude,
            operation_speed,
            operation_direction,
            collected_at
        FROM vehicle_positions
        WHERE route_id = %s
        ORDER BY vehicle_no, collected_at DESC
        """,
        (route_id,),
    )
    rows = cur.fetchall()
    return [
        {
            "vehicle_position_id": row[0],
            "vehicle_no": row[1],
            "route_id": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "operation_speed": float(row[5]) if row[5] is not None else None,
            "operation_direction": row[6],
            "collected_at": row[7],
        }
        for row in rows
    ]


def _target_arrival_candidates(
    cur: Any,
    route_id: str,
    transfer_station_id: str,
) -> list[dict[str, Any]]:
    route_stations = _fetch_route_stations(cur, route_id)
    vehicles = _fetch_latest_route_vehicles(cur, route_id)
    candidates = []

    for vehicle in vehicles:
        estimate = _estimate_vehicle_to_station(route_stations, transfer_station_id, vehicle)
        if not estimate:
            continue

        candidates.append(
            {
                "vehicle_position_id": vehicle["vehicle_position_id"],
                "vehicle_no": vehicle["vehicle_no"],
                "route_id": route_id,
                "transfer_station_id": transfer_station_id,
                "transfer_station_name": estimate["station"]["station_name"],
                "eta_seconds": estimate["eta_seconds"],
                "remaining_stops": estimate["remaining_stops"],
                "distance_m": estimate["distance_m"],
            }
        )

    return sorted(candidates, key=lambda item: item["eta_seconds"])


def _build_recommendation(
    strategy: str,
    route_id: str,
    station: dict[str, Any],
    source_eta_seconds: int,
    target_eta_seconds: int,
    walking_time_seconds: int,
) -> dict[str, Any]:
    slack_seconds = target_eta_seconds - source_eta_seconds - walking_time_seconds
    probability = _probability_from_slack(slack_seconds)
    return {
        "strategy": strategy,
        "route_id": route_id,
        "transfer_station_id": station["station_id"],
        "transfer_station_name": station["station_name"],
        "source_arrival_seconds": source_eta_seconds,
        "target_arrival_seconds": target_eta_seconds,
        "walking_time_seconds": walking_time_seconds,
        "slack_seconds": slack_seconds,
        "success_probability": probability,
        "risk_level": _risk_level(probability),
        "summary": (
            f"{station['station_name']} 기준 환승 여유시간 {slack_seconds}초, "
            f"성공 확률 {int(probability * 100)}%"
        ),
    }


def _shared_station_recommendation(
    cur: Any,
    source_route_id: str,
    target_route_id: str,
    source_vehicle: dict[str, Any],
    mobility_profile: str,
) -> dict[str, Any] | None:
    source_stations = _fetch_route_stations(cur, source_route_id)
    target_stations = _fetch_route_stations(cur, target_route_id)
    nearest_source_station = _find_nearest_station(
        source_stations,
        source_vehicle["latitude"],
        source_vehicle["longitude"],
    )

    if not nearest_source_station:
        return None

    target_station_map = _station_lookup(target_stations)
    walking_time_seconds = PROFILE_WALKING_BUFFER[mobility_profile]

    future_shared_stations = [
        station
        for station in source_stations
        if station["station_sequence"] >= nearest_source_station["station_sequence"]
        and station["station_id"] in target_station_map
    ]

    best_option = None
    for station in future_shared_stations[:5]:
        source_estimate = _estimate_vehicle_to_station(
            source_stations,
            station["station_id"],
            source_vehicle,
        )
        if not source_estimate:
            continue

        target_candidates = _target_arrival_candidates(cur, target_route_id, station["station_id"])
        if not target_candidates:
            continue

        option = _build_recommendation(
            strategy="다음 공통 정류장 환승",
            route_id=target_route_id,
            station=station,
            source_eta_seconds=source_estimate["eta_seconds"],
            target_eta_seconds=target_candidates[0]["eta_seconds"],
            walking_time_seconds=walking_time_seconds,
        )
        if not best_option or option["success_probability"] > best_option["success_probability"]:
            best_option = option

    return best_option


def generate_prediction(cur: Any, payload: Any) -> dict[str, Any]:
    mobility_profile = payload.mobility_profile if payload.mobility_profile in PROFILE_WALKING_BUFFER else "normal"

    cur.execute(
        """
        SELECT
            vehicle_position_id,
            vehicle_no,
            route_id,
            latitude,
            longitude,
            operation_speed,
            operation_direction,
            collected_at
        FROM vehicle_positions
        WHERE vehicle_position_id = %s
        """,
        (payload.vehicle_position_id,),
    )
    source_row = cur.fetchone()
    if not source_row:
        raise ValueError("vehicle_position_id가 존재하지 않습니다.")

    source_vehicle = {
        "vehicle_position_id": source_row[0],
        "vehicle_no": source_row[1],
        "route_id": source_row[2],
        "latitude": source_row[3],
        "longitude": source_row[4],
        "operation_speed": float(source_row[5]) if source_row[5] is not None else None,
        "operation_direction": source_row[6],
        "collected_at": source_row[7],
    }

    source_route_stations = _fetch_route_stations(cur, source_vehicle["route_id"])
    target_route_stations = _fetch_route_stations(cur, payload.target_route_id)
    if not source_route_stations or not target_route_stations:
        raise ValueError("노선 정류장 정보가 부족합니다.")

    source_station_map = _station_lookup(source_route_stations)
    target_station_map = _station_lookup(target_route_stations)

    if payload.transfer_station_id not in source_station_map:
        raise ValueError("선택한 환승 정류장이 현재 차량 노선에 존재하지 않습니다.")
    if payload.transfer_station_id not in target_station_map:
        raise ValueError("선택한 환승 정류장이 목표 노선에 존재하지 않습니다.")

    source_estimate = _estimate_vehicle_to_station(
        source_route_stations,
        payload.transfer_station_id,
        source_vehicle,
    )
    if not source_estimate:
        raise ValueError("현재 차량이 해당 환승 정류장을 이미 지나갔거나 도착 예측이 어렵습니다.")

    target_candidates = _target_arrival_candidates(
        cur,
        payload.target_route_id,
        payload.transfer_station_id,
    )
    if not target_candidates:
        raise ValueError("목표 노선의 도착 예정 차량을 찾지 못했습니다.")

    target_candidate = target_candidates[0]
    walking_time_seconds = PROFILE_WALKING_BUFFER[mobility_profile]
    slack_seconds = (
        target_candidate["eta_seconds"]
        - source_estimate["eta_seconds"]
        - walking_time_seconds
    )
    success_probability = _probability_from_slack(slack_seconds)
    warning_reason = _warning_reason(
        success_probability,
        slack_seconds,
        target_candidate["eta_seconds"],
    )

    recommendations = [
        _build_recommendation(
            strategy="기본 환승 유지",
            route_id=payload.target_route_id,
            station=source_station_map[payload.transfer_station_id],
            source_eta_seconds=source_estimate["eta_seconds"],
            target_eta_seconds=target_candidate["eta_seconds"],
            walking_time_seconds=walking_time_seconds,
        )
    ]

    if len(target_candidates) > 1:
        recommendations.append(
            _build_recommendation(
                strategy="같은 노선 다음 차량 대기",
                route_id=payload.target_route_id,
                station=source_station_map[payload.transfer_station_id],
                source_eta_seconds=source_estimate["eta_seconds"],
                target_eta_seconds=target_candidates[1]["eta_seconds"],
                walking_time_seconds=walking_time_seconds,
            )
        )

    shared_station_option = _shared_station_recommendation(
        cur,
        source_route_id=source_vehicle["route_id"],
        target_route_id=payload.target_route_id,
        source_vehicle=source_vehicle,
        mobility_profile=mobility_profile,
    )
    if shared_station_option:
        recommendations.append(shared_station_option)

    unique_recommendations = []
    seen = set()
    for item in sorted(recommendations, key=lambda rec: rec["success_probability"], reverse=True):
        key = (item["strategy"], item["route_id"], item["transfer_station_id"])
        if key in seen:
            continue
        seen.add(key)
        unique_recommendations.append(item)

    return {
        "source_vehicle": source_vehicle,
        "source_route_id": source_vehicle["route_id"],
        "transfer_station": source_station_map[payload.transfer_station_id],
        "walking_time_seconds": walking_time_seconds,
        "source_arrival_seconds": source_estimate["eta_seconds"],
        "target_arrival_seconds": target_candidate["eta_seconds"],
        "slack_seconds": slack_seconds,
        "success_probability": success_probability,
        "risk_level": _risk_level(success_probability),
        "is_warning": success_probability < 0.4,
        "warning_reason": warning_reason,
        "recommended_option": unique_recommendations[0],
        "recommendations": unique_recommendations[:3],
    }
