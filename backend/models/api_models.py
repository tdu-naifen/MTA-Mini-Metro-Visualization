"""
Pydantic models for FastAPI responses that mirror Thrift schema
"""

from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

class DirectionEnum(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"
    UNKNOWN = "UNKNOWN"

class LineColorEnum(str, Enum):
    YELLOW = "YELLOW"
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    ORANGE = "ORANGE"
    PURPLE = "PURPLE"

class CoordinateModel(BaseModel):
    latitude: float
    longitude: float

class StationModel(BaseModel):
    station_id: str
    name: str
    location: CoordinateModel
    line_ids: List[str]
    is_terminus: bool = False
    accessibility_info: Optional[str] = None

class TrainModel(BaseModel):
    train_id: str
    line_id: str
    current_position: CoordinateModel
    direction: DirectionEnum
    current_station_id: str
    next_station_id: Optional[str] = None
    timestamp: int
    speed_mph: float
    trip_id: str
    delay_seconds: Optional[int] = None
    line_color: LineColorEnum

class LineSegmentModel(BaseModel):
    from_station_id: str
    to_station_id: str
    path_coordinates: List[CoordinateModel]
    line_color: LineColorEnum
    distance_miles: float

class SubwayLineModel(BaseModel):
    line_id: str
    name: str
    color: LineColorEnum
    stations: List[StationModel]
    segments: List[LineSegmentModel]
    active_trains: List[TrainModel]

class RealTimeFeedModel(BaseModel):
    timestamp: int
    lines: List[SubwayLineModel]
    total_active_trains: int
    feed_version: str

class ApiResponseModel(BaseModel):
    success: bool
    error_message: Optional[str] = None
    data: Optional[RealTimeFeedModel] = None
    timestamp: int

# Conversion functions from Thrift to Pydantic models

def thrift_to_pydantic_coord(thrift_coord) -> CoordinateModel:
    """Convert Thrift Coordinate to Pydantic model"""
    return CoordinateModel(
        latitude=thrift_coord.latitude,
        longitude=thrift_coord.longitude
    )

def thrift_to_pydantic_station(thrift_station) -> StationModel:
    """Convert Thrift Station to Pydantic model"""
    return StationModel(
        station_id=thrift_station.station_id,
        name=thrift_station.name,
        location=thrift_to_pydantic_coord(thrift_station.location),
        line_ids=thrift_station.line_ids,
        is_terminus=thrift_station.is_terminus,
        accessibility_info=thrift_station.accessibility_info
    )

def thrift_to_pydantic_train(thrift_train) -> TrainModel:
    """Convert Thrift Train to Pydantic model"""
    from ..generated.mta_data.ttypes import Direction, LineColor
    
    # Convert direction enum
    direction_map = {
        Direction.NORTH: DirectionEnum.NORTH,
        Direction.SOUTH: DirectionEnum.SOUTH,
        Direction.EAST: DirectionEnum.EAST,
        Direction.WEST: DirectionEnum.WEST,
        Direction.UNKNOWN: DirectionEnum.UNKNOWN,
    }
    
    # Convert color enum
    color_map = {
        LineColor.YELLOW: LineColorEnum.YELLOW,
        LineColor.RED: LineColorEnum.RED,
        LineColor.BLUE: LineColorEnum.BLUE,
        LineColor.GREEN: LineColorEnum.GREEN,
        LineColor.ORANGE: LineColorEnum.ORANGE,
        LineColor.PURPLE: LineColorEnum.PURPLE,
    }
    
    return TrainModel(
        train_id=thrift_train.train_id,
        line_id=thrift_train.line_id,
        current_position=thrift_to_pydantic_coord(thrift_train.current_position),
        direction=direction_map.get(thrift_train.direction, DirectionEnum.UNKNOWN),
        current_station_id=thrift_train.current_station_id,
        next_station_id=thrift_train.next_station_id,
        timestamp=thrift_train.timestamp,
        speed_mph=thrift_train.speed_mph,
        trip_id=thrift_train.trip_id,
        delay_seconds=thrift_train.delay_seconds,
        line_color=color_map.get(thrift_train.line_color, LineColorEnum.YELLOW)
    )

def thrift_to_pydantic_segment(thrift_segment) -> LineSegmentModel:
    """Convert Thrift LineSegment to Pydantic model"""
    from ..generated.mta_data.ttypes import LineColor
    
    color_map = {
        LineColor.YELLOW: LineColorEnum.YELLOW,
        LineColor.RED: LineColorEnum.RED,
        LineColor.BLUE: LineColorEnum.BLUE,
        LineColor.GREEN: LineColorEnum.GREEN,
        LineColor.ORANGE: LineColorEnum.ORANGE,
        LineColor.PURPLE: LineColorEnum.PURPLE,
    }
    
    return LineSegmentModel(
        from_station_id=thrift_segment.from_station_id,
        to_station_id=thrift_segment.to_station_id,
        path_coordinates=[thrift_to_pydantic_coord(coord) for coord in thrift_segment.path_coordinates],
        line_color=color_map.get(thrift_segment.line_color, LineColorEnum.YELLOW),
        distance_miles=thrift_segment.distance_miles
    )

def thrift_to_pydantic_line(thrift_line) -> SubwayLineModel:
    """Convert Thrift SubwayLine to Pydantic model"""
    from ..generated.mta_data.ttypes import LineColor
    
    color_map = {
        LineColor.YELLOW: LineColorEnum.YELLOW,
        LineColor.RED: LineColorEnum.RED,
        LineColor.BLUE: LineColorEnum.BLUE,
        LineColor.GREEN: LineColorEnum.GREEN,
        LineColor.ORANGE: LineColorEnum.ORANGE,
        LineColor.PURPLE: LineColorEnum.PURPLE,
    }
    
    return SubwayLineModel(
        line_id=thrift_line.line_id,
        name=thrift_line.name,
        color=color_map.get(thrift_line.color, LineColorEnum.YELLOW),
        stations=[thrift_to_pydantic_station(station) for station in thrift_line.stations],
        segments=[thrift_to_pydantic_segment(segment) for segment in thrift_line.segments],
        active_trains=[thrift_to_pydantic_train(train) for train in thrift_line.active_trains]
    )

def thrift_to_pydantic_feed(thrift_feed) -> RealTimeFeedModel:
    """Convert Thrift RealTimeFeed to Pydantic model"""
    return RealTimeFeedModel(
        timestamp=thrift_feed.timestamp,
        lines=[thrift_to_pydantic_line(line) for line in thrift_feed.lines],
        total_active_trains=thrift_feed.total_active_trains,
        feed_version=thrift_feed.feed_version
    )
