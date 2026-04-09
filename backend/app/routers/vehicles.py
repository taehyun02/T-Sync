from fastapi import APIRouter, Query, HTTPException
from app.db import get_connection
import psycopg2

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("")
def get_vehicle_positions(limit: int = Query(300, ge=1, le=1000)):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
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
            ORDER BY collected_at DESC
            LIMIT %s
        """, (limit,))
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
                "collected_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/by-route/{route_id}")
def get_vehicle_positions_by_route(route_id: str):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
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
            WHERE route_id = %s
            ORDER BY collected_at DESC
        """, (route_id,))
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
                "collected_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/{vehicle_position_id}")
def get_vehicle_position_detail(vehicle_position_id: int):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
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
        """, (vehicle_position_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="해당 차량 위치 정보를 찾을 수 없습니다.")

        return {
            "vehicle_position_id": row[0],
            "vehicle_no": row[1],
            "route_id": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "operation_speed": float(row[5]) if row[5] is not None else None,
            "operation_direction": row[6],
            "collected_at": row[7].isoformat() if row[7] else None,
        }
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {str(e)}")
    finally:
        cur.close()
        conn.close()