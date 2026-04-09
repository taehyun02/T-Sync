-- =========================
-- 1. routes (노선정보)
-- =========================

CREATE TABLE routes (
    route_id VARCHAR(20) PRIMARY KEY,
    route_no VARCHAR(100) NOT NULL,
    route_type VARCHAR(50),
    start_stop VARCHAR(100),
    end_stop VARCHAR(100)
);

COMMENT ON TABLE routes IS '노선정보';

COMMENT ON COLUMN routes.route_id IS '노선ID';
COMMENT ON COLUMN routes.route_no IS '노선번호';
COMMENT ON COLUMN routes.route_type IS '노선유형';
COMMENT ON COLUMN routes.start_stop IS '기점정류장명';
COMMENT ON COLUMN routes.end_stop IS '종점정류장명';


-- =========================
-- 2. stations (정류장정보)
-- =========================

CREATE TABLE stations (
    station_id VARCHAR(20) PRIMARY KEY,
    station_name VARCHAR(150) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

COMMENT ON TABLE stations IS '정류장정보';

COMMENT ON COLUMN stations.station_id IS '정류장ID';
COMMENT ON COLUMN stations.station_name IS '정류장명';
COMMENT ON COLUMN stations.latitude IS '위도';
COMMENT ON COLUMN stations.longitude IS '경도';


-- =========================
-- 3. route_stations (노선-정류장매핑)
-- =========================

CREATE TABLE route_stations (
    route_station_id BIGSERIAL PRIMARY KEY,
    route_id VARCHAR(20) NOT NULL,
    station_id VARCHAR(20) NOT NULL,
    station_sequence INTEGER NOT NULL,

    CONSTRAINT fk_route_stations_route
    FOREIGN KEY (route_id)
    REFERENCES routes(route_id),

    CONSTRAINT fk_route_stations_station
    FOREIGN KEY (station_id)
    REFERENCES stations(station_id)
);

COMMENT ON TABLE route_stations IS '노선-정류장매핑';

COMMENT ON COLUMN route_stations.route_station_id IS '매핑ID';
COMMENT ON COLUMN route_stations.route_id IS '노선ID';
COMMENT ON COLUMN route_stations.station_id IS '정류장ID';
COMMENT ON COLUMN route_stations.station_sequence IS '정류장순서';


-- =========================
-- 4. vehicle_positions (차량실시간위치)
-- =========================

CREATE TABLE vehicle_positions (
    vehicle_position_id BIGSERIAL PRIMARY KEY,
    vehicle_no VARCHAR(30) NOT NULL,
    route_id VARCHAR(20) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    operation_speed NUMERIC(6,2),
    operation_direction INTEGER,
    collected_at TIMESTAMP,

    CONSTRAINT fk_vehicle_positions_route
    FOREIGN KEY (route_id)
    REFERENCES routes(route_id)
);

COMMENT ON TABLE vehicle_positions IS '차량실시간위치';

COMMENT ON COLUMN vehicle_positions.vehicle_position_id IS '차량위치ID';
COMMENT ON COLUMN vehicle_positions.vehicle_no IS '차량번호';
COMMENT ON COLUMN vehicle_positions.route_id IS '노선ID';
COMMENT ON COLUMN vehicle_positions.latitude IS '차량위도';
COMMENT ON COLUMN vehicle_positions.longitude IS '차량경도';
COMMENT ON COLUMN vehicle_positions.operation_speed IS '차량속도';
COMMENT ON COLUMN vehicle_positions.operation_direction IS '차량방향각';
COMMENT ON COLUMN vehicle_positions.collected_at IS '위치수집시각';


-- =========================
-- 5. transfer_predictions (환승예측결과)
-- =========================

CREATE TABLE transfer_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    vehicle_position_id BIGINT NOT NULL,
    target_route_id VARCHAR(20) NOT NULL,
    transfer_station_id VARCHAR(20),
    success_probability NUMERIC(5,2),
    is_warning BOOLEAN DEFAULT FALSE,
    warning_reason VARCHAR(200),
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_predictions_position
    FOREIGN KEY (vehicle_position_id)
    REFERENCES vehicle_positions(vehicle_position_id),

    CONSTRAINT fk_predictions_route
    FOREIGN KEY (target_route_id)
    REFERENCES routes(route_id),

    CONSTRAINT fk_predictions_station
    FOREIGN KEY (transfer_station_id)
    REFERENCES stations(station_id)
);

COMMENT ON TABLE transfer_predictions IS '환승예측결과';

COMMENT ON COLUMN transfer_predictions.prediction_id IS '예측결과ID';
COMMENT ON COLUMN transfer_predictions.user_id IS '사용자식별ID';
COMMENT ON COLUMN transfer_predictions.vehicle_position_id IS '참조차량위치ID';
COMMENT ON COLUMN transfer_predictions.target_route_id IS '환승대상노선ID';
COMMENT ON COLUMN transfer_predictions.transfer_station_id IS '환승예정정류장ID';
COMMENT ON COLUMN transfer_predictions.success_probability IS '환승성공확률(%)';
COMMENT ON COLUMN transfer_predictions.is_warning IS '환승지연/실패경고여부';
COMMENT ON COLUMN transfer_predictions.warning_reason IS '경고발생원인';
COMMENT ON COLUMN transfer_predictions.predicted_at IS '예측실행시각';


-- =========================
-- 인덱스 (성능 최적화)
-- =========================

CREATE INDEX idx_route_stations_route
ON route_stations(route_id, station_sequence);

CREATE INDEX idx_vehicle_positions_route_time
ON vehicle_positions(route_id, collected_at DESC);

CREATE INDEX idx_vehicle_positions_vehicle_time
ON vehicle_positions(vehicle_no, collected_at DESC);

CREATE INDEX idx_predictions_position
ON transfer_predictions(vehicle_position_id);