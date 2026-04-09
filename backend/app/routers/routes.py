from fastapi import APIRouter, Query
from app.db import get_connection

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("")
def get_routes():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT route_id, route_no, route_type, start_stop, end_stop
            FROM routes
            ORDER BY route_no
        """)
        rows = cur.fetchall()

        return [
            {
                "route_id": row[0],
                "route_no": row[1],
                "route_type": row[2],
                "start_stop": row[3],
                "end_stop": row[4],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


@router.get("/search")
def search_routes(keyword: str = Query(...)):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT route_id, route_no, route_type, start_stop, end_stop
            FROM routes
            WHERE route_no ILIKE %s
               OR start_stop ILIKE %s
               OR end_stop ILIKE %s
            ORDER BY route_no
        """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
        rows = cur.fetchall()

        return [
            {
                "route_id": row[0],
                "route_no": row[1],
                "route_type": row[2],
                "start_stop": row[3],
                "end_stop": row[4],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


@router.get("/{route_id}/stations")
def get_route_stations(route_id: str):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                rs.route_id,
                rs.station_id,
                s.station_name,
                rs.station_sequence,
                s.latitude,
                s.longitude
            FROM route_stations rs
            JOIN stations s
              ON rs.station_id = s.station_id
            WHERE rs.route_id = %s
            ORDER BY rs.station_sequence
        """, (route_id,))
        rows = cur.fetchall()

        return [
            {
                "route_id": row[0],
                "station_id": row[1],
                "station_name": row[2],
                "station_sequence": row[3],
                "latitude": row[4],
                "longitude": row[5],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()