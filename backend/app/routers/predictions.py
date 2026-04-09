from fastapi import APIRouter, HTTPException, Query
from app.db import get_connection
from app.schemas import PredictionRunIn
import psycopg2
import math

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("")
def get_predictions(limit: int = Query(100, ge=1, le=500)):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                prediction_id,
                user_id,
                vehicle_position_id,
                target_route_id,
                transfer_station_id,
                success_probability,
                is_warning,
                warning_reason,
                predicted_at
            FROM transfer_predictions
            ORDER BY predicted_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

        return [
            {
                "prediction_id": row[0],
                "user_id": row[1],
                "vehicle_position_id": row[2],
                "target_route_id": row[3],
                "transfer_station_id": row[4],
                "success_probability": float(row[5]) if row[5] is not None else None,
                "is_warning": row[6],
                "warning_reason": row[7],
                "predicted_at": row[8].isoformat() if row[8] else None,
            }
            for row in rows
        ]

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")

    finally:
        cur.close()
        conn.close()


def get_walking_speed(profile: str) -> float:
    profile = profile.lower()

    if profile == "fast":
        return 1.5
    elif profile == "slow":
        return 0.9
    else:
        return 1.2


def haversine_meters(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]:
        return 150.0  # 좌표 없으면 기본값

    r = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


def calculate_walking_time_sec(distance_m: float, mobility_profile: str) -> int:
    speed = get_walking_speed(mobility_profile)
    return int(distance_m / speed)


def score_success_probability(slack_time_sec: int) -> float:
    if slack_time_sec >= 120:
        return 0.9
    elif slack_time_sec >= 60:
        return 0.7
    elif slack_time_sec >= 20:
        return 0.5
    elif slack_time_sec >= 0:
        return 0.3
    else:
        return 0.1


def get_risk_level(prob: float) -> str:
    if prob >= 0.7:
        return "safe"
    elif prob >= 0.4:
        return "uncertain"
    else:
        return "risky"


def build_alternatives(slack_time_sec: int):
    alternatives = []

    if slack_time_sec < 0:
        alternatives.append("동일 노선의 다음 차량 이용")
        alternatives.append("다음 정류장에서 환승 재시도")
        alternatives.append("다른 노선 기반 환승 경로 재탐색")
    elif slack_time_sec < 30:
        alternatives.append("환승 정류장 도착 후 즉시 이동")
        alternatives.append("후속 차량 대기")
        alternatives.append("다음 정류장 환승 검토")
    else:
        alternatives.append("현재 환승 전략 유지")

    return alternatives


def estimate_first_vehicle_eta_sec(cur, vehicle_position_id: int, transfer_station_id: str):
    cur.execute("""
        SELECT
            vp.vehicle_position_id,
            vp.vehicle_no,
            vp.route_id,
            vp.latitude,
            vp.longitude,
            vp.operation_speed
        FROM vehicle_positions vp
        WHERE vp.vehicle_position_id = %s
    """, (vehicle_position_id,))
    vehicle = cur.fetchone()

    if not vehicle:
        raise HTTPException(status_code=404, detail="vehicle_position_id가 존재하지 않습니다.")

    current_route_id = vehicle[2]
    vehicle_lat = vehicle[3]
    vehicle_lon = vehicle[4]
    speed_kmh = float(vehicle[5]) if vehicle[5] is not None else 20.0

    cur.execute("""
        SELECT latitude, longitude
        FROM stations
        WHERE station_id = %s
    """, (transfer_station_id,))
    station = cur.fetchone()

    if not station:
        raise HTTPException(status_code=404, detail="transfer_station_id가 존재하지 않습니다.")

    station_lat = station[0]
    station_lon = station[1]

    distance_m = haversine_meters(vehicle_lat, vehicle_lon, station_lat, station_lon)

    speed_mps = max(speed_kmh * 1000 / 3600, 3.0)
    eta_sec = int(distance_m / speed_mps)

    return {
        "current_route_id": current_route_id,
        "vehicle_lat": vehicle_lat,
        "vehicle_lon": vehicle_lon,
        "station_lat": station_lat,
        "station_lon": station_lon,
        "first_vehicle_eta_sec": eta_sec,
    }


def estimate_second_vehicle_eta_sec(cur, target_route_id: str, transfer_station_id: str):
    cur.execute("""
        SELECT route_id
        FROM routes
        WHERE route_id = %s
    """, (target_route_id,))
    route_row = cur.fetchone()

    if not route_row:
        raise HTTPException(status_code=404, detail="target_route_id가 존재하지 않습니다.")

    cur.execute("""
        SELECT s.latitude, s.longitude
        FROM stations s
        WHERE s.station_id = %s
    """, (transfer_station_id,))
    station = cur.fetchone()

    if not station:
        raise HTTPException(status_code=404, detail="transfer_station_id가 존재하지 않습니다.")

    station_lat = station[0]
    station_lon = station[1]

    cur.execute("""
        SELECT
            vp.vehicle_position_id,
            vp.vehicle_no,
            vp.route_id,
            vp.latitude,
            vp.longitude,
            vp.operation_speed
        FROM vehicle_positions vp
        WHERE vp.route_id = %s
        ORDER BY vp.collected_at DESC
    """, (target_route_id,))
    vehicles = cur.fetchall()

    if not vehicles:
        return 600  # 목표 노선 차량이 없으면 보수적으로 10분

    best_eta = None

    for row in vehicles:
        lat = row[3]
        lon = row[4]
        speed_kmh = float(row[5]) if row[5] is not None else 20.0

        distance_m = haversine_meters(lat, lon, station_lat, station_lon)
        speed_mps = max(speed_kmh * 1000 / 3600, 3.0)
        eta_sec = int(distance_m / speed_mps)

        if best_eta is None or eta_sec < best_eta:
            best_eta = eta_sec

    return best_eta if best_eta is not None else 600


@router.post("/run")
def run_prediction(payload: PredictionRunIn):
    conn = get_connection()
    cur = conn.cursor()

    try:
        first_info = estimate_first_vehicle_eta_sec(
            cur,
            payload.vehicle_position_id,
            payload.transfer_station_id
        )

        second_vehicle_eta_sec = estimate_second_vehicle_eta_sec(
            cur,
            payload.target_route_id,
            payload.transfer_station_id
        )

        # 같은 정류장 환승 기준 MVP: 좌표 동일하면 기본 보행거리 최소값 부여
        transfer_walk_distance_m = 120.0
        walking_time_sec = calculate_walking_time_sec(
            transfer_walk_distance_m,
            payload.mobility_profile
        )

        slack_time_sec = second_vehicle_eta_sec - first_info["first_vehicle_eta_sec"] - walking_time_sec
        success_probability = score_success_probability(slack_time_sec)
        risk_level = get_risk_level(success_probability)
        alternatives = build_alternatives(slack_time_sec)

        is_warning = success_probability < 0.4
        warning_reason = None if not is_warning else "환승 실패 위험이 높은 상태입니다."

        cur.execute("""
            INSERT INTO transfer_predictions (
                user_id,
                vehicle_position_id,
                target_route_id,
                transfer_station_id,
                success_probability,
                is_warning,
                warning_reason,
                predicted_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING
                prediction_id,
                predicted_at
        """, (
            payload.user_id,
            payload.vehicle_position_id,
            payload.target_route_id,
            payload.transfer_station_id,
            success_probability,
            is_warning,
            warning_reason
        ))

        row = cur.fetchone()
        conn.commit()

        return {
            "prediction_id": row[0],
            "user_id": payload.user_id,
            "vehicle_position_id": payload.vehicle_position_id,
            "target_route_id": payload.target_route_id,
            "transfer_station_id": payload.transfer_station_id,
            "mobility_profile": payload.mobility_profile,
            "first_vehicle_eta_sec": first_info["first_vehicle_eta_sec"],
            "second_vehicle_eta_sec": second_vehicle_eta_sec,
            "walking_time_sec": walking_time_sec,
            "slack_time_sec": slack_time_sec,
            "success_probability": success_probability,
            "risk_level": risk_level,
            "is_warning": is_warning,
            "warning_reason": warning_reason,
            "recommended_alternatives": alternatives,
            "predicted_at": row[1].isoformat() if row[1] else None
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"prediction 계산 중 오류: {str(e)}")
    finally:
        cur.close()
        conn.close()