from typing import Literal, Optional

from pydantic import BaseModel


class RouteOut(BaseModel):
    route_id: str
    route_no: str
    route_type: Optional[str] = None
    start_stop: Optional[str] = None
    end_stop: Optional[str] = None


class StationOut(BaseModel):
    station_id: str
    station_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RouteStationOut(BaseModel):
    route_id: str
    station_id: str
    station_name: str
    station_sequence: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VehiclePositionOut(BaseModel):
    vehicle_position_id: int
    vehicle_no: str
    route_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operation_speed: Optional[float] = None
    operation_direction: Optional[int] = None
    collected_at: Optional[str] = None

class PredictionRunIn(BaseModel):
    user_id: str
    vehicle_position_id: int
    target_route_id: str
    transfer_station_id: str
    mobility_profile: Literal["fast", "normal", "slow"] = "normal"
