import os
import time
import requests
import psycopg2
from urllib.parse import unquote
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("PUBLIC_DATA_API_KEY")
SYNC_TARGET = os.getenv("SYNC_TARGET", "all")

ULSAN_CODE = "3100000000"
ULSAN_NAME = "울산광역시"

NUM_OF_ROWS = 50   # 안정성 위해 100 → 50으로 감소

MST_INFO_URL = "https://apis.data.go.kr/B551982/rte/mst_info"
PS_INFO_URL = "https://apis.data.go.kr/B551982/rte/ps_info"
RTM_LOC_INFO_URL = "https://apis.data.go.kr/B551982/rte/rtm_loc_info"


###############################
# 유틸 함수
###############################

def norm_key(key):
    if not key:
        raise ValueError("PUBLIC_DATA_API_KEY 없음")

    if "%2F" in key or "%3D" in key:
        return unquote(key)

    return key


def conn_db():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL 없음")

    return psycopg2.connect(DATABASE_URL)


def parse_tot_dt(value):
    if not value:
        return None

    return datetime.strptime(value, "%Y%m%d%H%M%S")


###############################
# API 호출 함수 (rate-limit 대응)
###############################

def call_api(url, page, max_retries=6):

    params = {
        "serviceKey": norm_key(API_KEY),
        "type": "json",
        "pageNo": page,
        "numOfRows": NUM_OF_ROWS,
    }

    for attempt in range(max_retries):

        try:
            r = requests.get(url, params=params, timeout=60)

            print(f"[API] {url} page={page} status={r.status_code}", flush=True)

            if r.status_code == 200:

                time.sleep(3.0)  # rate-limit 보호 핵심
                return r.json()

            if r.status_code == 429:

                wait = 20 * (attempt + 1)
                print(f"[429] page={page} {wait}초 대기 후 재시도", flush=True)

                time.sleep(wait)
                continue

            r.raise_for_status()

        except requests.exceptions.ReadTimeout:

            wait = 10 * (attempt + 1)
            print(f"[TIMEOUT] page={page} {wait}초 대기 후 재시도", flush=True)

            time.sleep(wait)

    raise Exception(f"page={page} API 호출 반복 실패")


###############################
# 데이터 필터링
###############################

def get_items(data):

    items = data["body"]["items"]["item"]

    if isinstance(items, list):
        return items

    return [items]


def is_ulsan(item):

    return (
        str(item.get("stdgCd", "")).strip() == ULSAN_CODE
        or str(item.get("lclgvNm", "")).strip() == ULSAN_NAME
    )


def fetch_ulsan_block(url):

    page = 1
    kept = []

    while True:

        data = call_api(url, page)

        items = get_items(data)

        if not items:
            print(f"[STOP] page={page} 데이터 없음", flush=True)
            break

        page_kept = [item for item in items if is_ulsan(item)]

        if len(page_kept) == 0:
            print(f"[STOP] page={page} 울산 데이터 없음", flush=True)
            break

        kept.extend(page_kept)

        print(
            f"[KEEP] page={page} kept={len(page_kept)} total={len(kept)}",
            flush=True,
        )

        page += 1

    return kept


###############################
# routes 적재
###############################

def sync_routes(conn):

    print("routes syncing...", flush=True)

    items = fetch_ulsan_block(MST_INFO_URL)

    cur = conn.cursor()

    try:

        for item in items:

            cur.execute(
                """
                INSERT INTO routes
                (route_id, route_no, route_type, start_stop, end_stop)

                VALUES (%s, %s, %s, %s, %s)

                ON CONFLICT (route_id)
                DO UPDATE SET

                route_no = EXCLUDED.route_no,
                route_type = EXCLUDED.route_type,
                start_stop = EXCLUDED.start_stop,
                end_stop = EXCLUDED.end_stop
                """,
                (
                    item["rteId"],
                    item["rteNo"],
                    item["rteType"],
                    item["stpnt"],
                    item["edpnt"],
                ),
            )

        conn.commit()

        print(f"routes 완료 count={len(items)}", flush=True)

    except Exception as e:

        conn.rollback()
        print("routes 실패:", e, flush=True)
        raise

    finally:
        cur.close()


###############################
# stations + route_stations
###############################

def sync_stations_and_route_stations(conn):

    print("stations syncing...", flush=True)

    items = fetch_ulsan_block(PS_INFO_URL)

    cur = conn.cursor()

    try:

        for item in items:

            station_id = item["bstaId"]

            latitude = float(item["bstaLat"]) if item.get("bstaLat") else None
            longitude = float(item["bstaLot"]) if item.get("bstaLot") else None

            cur.execute(
                """
                INSERT INTO stations
                (station_id, station_name, latitude, longitude)

                VALUES (%s, %s, %s, %s)

                ON CONFLICT (station_id)
                DO UPDATE SET

                station_name = EXCLUDED.station_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude
                """,
                (
                    station_id,
                    item["bstaNm"],
                    latitude,
                    longitude,
                ),
            )

            cur.execute(
                """
                INSERT INTO route_stations
                (route_id, station_id, station_sequence)

                SELECT %s, %s, %s

                WHERE NOT EXISTS
                (
                    SELECT 1
                    FROM route_stations

                    WHERE route_id=%s
                    AND station_id=%s
                    AND station_sequence=%s
                )
                """,
                (
                    item["rteId"],
                    station_id,
                    int(item["bstaSn"]),
                    item["rteId"],
                    station_id,
                    int(item["bstaSn"]),
                ),
            )

        conn.commit()

        print("stations 완료", flush=True)

    except Exception as e:

        conn.rollback()
        print("stations 실패:", e, flush=True)
        raise

    finally:
        cur.close()


###############################
# 차량 위치 적재
###############################

def sync_vehicle_positions(conn):

    print("vehicle_positions syncing...", flush=True)

    items = fetch_ulsan_block(RTM_LOC_INFO_URL)

    cur = conn.cursor()

    inserted = 0

    try:

        for item in items:

            vehicle_no = item.get("vhclNo")

            if not vehicle_no:
                continue

            cur.execute(
                """
                INSERT INTO vehicle_positions

                (
                    vehicle_no,
                    route_id,
                    latitude,
                    longitude,
                    operation_speed,
                    operation_direction,
                    collected_at
                )

                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    vehicle_no,
                    item.get("rteId"),
                    float(item["lat"]),
                    float(item["lot"]),
                    float(item["oprSpd"]),
                    int(item["oprDrct"]),
                    parse_tot_dt(item.get("totDt")),
                ),
            )

            inserted += 1

        conn.commit()

        print(f"vehicle_positions 완료 inserted={inserted}", flush=True)

    except Exception as e:

        conn.rollback()
        print("vehicle_positions 실패:", e, flush=True)
        raise

    finally:
        cur.close()


###############################
# 실행 흐름 제어
###############################

def main():
    conn = conn_db()
    try:
        if SYNC_TARGET == "routes":
            sync_routes(conn)

        elif SYNC_TARGET == "stations":
            sync_stations_and_route_stations(conn)

        elif SYNC_TARGET == "vehicles":
            sync_vehicle_positions(conn)

        else:
            sync_routes(conn)
            print("routes 완료 → 180초 대기", flush=True)
            time.sleep(180)

            sync_stations_and_route_stations(conn)
            print("stations 완료 → 180초 대기", flush=True)
            time.sleep(180)

            sync_vehicle_positions(conn)

        print("import 완료", flush=True)
    finally:
        conn.close()

if __name__ == "__main__":
    main()