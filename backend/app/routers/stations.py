from fastapi import APIRouter, Query
from app.db import get_connection

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("")
def get_stations(limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT station_id, station_name, latitude, longitude
            FROM stations
            ORDER BY station_name
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

        return [
            {
                "station_id": row[0],
                "station_name": row[1],
                "latitude": row[2],
                "longitude": row[3],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


@router.get("/search")
def search_stations(keyword: str = Query(...), limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT station_id, station_name, latitude, longitude
            FROM stations
            WHERE station_name ILIKE %s
            ORDER BY station_name
            LIMIT %s
        """, (f"%{keyword}%", limit))
        rows = cur.fetchall()

        return [
            {
                "station_id": row[0],
                "station_name": row[1],
                "latitude": row[2],
                "longitude": row[3],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()