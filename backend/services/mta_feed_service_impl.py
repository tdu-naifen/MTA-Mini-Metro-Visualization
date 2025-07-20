"""
MTA Real-time Feed Service Implementation
Implements the Thrift-generated MTAFeedService interface with real MTA data
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import uuid

from google.transit import gtfs_realtime_pb2
from ..generated.mta_data.ttypes import (
    SubwayLine, Train, Station, RealTimeFeed, 
    Coordinate, Direction, LineColor, LineSegment,
    MTAServiceException, InvalidLineException, FeedUnavailableException
)
from ..generated.mta_data.MTAFeedService import Iface as MTAFeedServiceIface
from .mta_data_loader import mta_data_loader

logger = logging.getLogger(__name__)

class MTAFeedServiceImpl(MTAFeedServiceIface):
    """Implementation of MTAFeedService that fetches real MTA data"""
    
    # MTA real-time feed URLs
    FEED_URLS = {
        'NQRW': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
        'BDFM': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
        'ACE': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
        'G': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
        'JZ': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
        'L': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
        '123456S': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
        '7': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-7'
    }
    
    # Line to feed mapping
    LINE_TO_FEED = {
        'N': 'NQRW', 'Q': 'NQRW', 'R': 'NQRW', 'W': 'NQRW',
        'B': 'BDFM', 'D': 'BDFM', 'F': 'BDFM', 'M': 'BDFM',
        'A': 'ACE', 'C': 'ACE', 'E': 'ACE',
        'G': 'G',
        'J': 'JZ', 'Z': 'JZ',
        'L': 'L',
        '1': '123456S', '2': '123456S', '3': '123456S', 
        '4': '123456S', '5': '123456S', '6': '123456S', 'S': '123456S',
        '7': '7'
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.cached_feeds: Dict[str, Dict] = {}
        self.last_update: Dict[str, datetime] = {}
        self.cache_duration = timedelta(seconds=30)  # Cache for 30 seconds
        self._initialized = False
        
    async def initialize(self):
        """Initialize the service"""
        if not self._initialized:
            self.session = aiohttp.ClientSession()
            # Load static data
            success = await mta_data_loader.load_static_data()
            if not success:
                logger.warning("Failed to load static data, using fallback data")
            self._initialized = True
            logger.info("MTA Feed Service initialized")
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    def _validate_lines(self, line_ids: List[str]) -> None:
        """Validate that all requested lines are supported"""
        supported_lines = set(self.LINE_TO_FEED.keys())
        invalid_lines = [line for line in line_ids if line not in supported_lines]
        
        if invalid_lines:
            raise InvalidLineException(
                message=f"Unsupported line(s): {', '.join(invalid_lines)}. Supported lines: {', '.join(sorted(supported_lines))}",
                line_id=invalid_lines[0]
            )
    
    async def _fetch_feed_data(self, feed_key: str) -> gtfs_realtime_pb2.FeedMessage:
        """Fetch real-time data from MTA feed"""
        url = self.FEED_URLS[feed_key]
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.read()
                    feed = gtfs_realtime_pb2.FeedMessage()
                    feed.ParseFromString(data)
                    return feed
                else:
                    raise FeedUnavailableException(
                        message=f"MTA feed returned status {response.status}",
                        retry_after_seconds=60
                    )
        except asyncio.TimeoutError:
            raise FeedUnavailableException(
                message="MTA feed request timed out",
                retry_after_seconds=30
            )
        except Exception as e:
            logger.error(f"Error fetching feed {feed_key}: {e}")
            raise MTAServiceException(
                message=f"Failed to fetch feed data: {str(e)}",
                error_code=500
            )
    
    def _parse_direction(self, gtfs_direction: int) -> Direction:
        """Parse GTFS direction to our Direction enum"""
        if gtfs_direction == 0:
            return Direction.NORTH  # or could be SOUTH depending on line
        elif gtfs_direction == 1:
            return Direction.SOUTH  # or could be NORTH depending on line
        else:
            return Direction.UNKNOWN
    
    def _estimate_position(self, station_id: str, next_station_id: Optional[str] = None) -> Coordinate:
        """Estimate train position based on current/next station"""
        if station_id in mta_data_loader.stations:
            station = mta_data_loader.stations[station_id]
            return station.location
        
        # Fallback coordinates (Times Square area)
        return Coordinate(latitude=40.754932, longitude=-73.987140)
    
    async def _process_feed_entities(self, feed: gtfs_realtime_pb2.FeedMessage, line_ids: List[str]) -> List[Train]:
        """Process feed entities and extract train information"""
        trains = []
        
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip_update = entity.trip_update
                trip = trip_update.trip
                
                # Check if this trip belongs to one of our requested lines
                route_id = trip.route_id
                if route_id not in line_ids:
                    continue
                
                # Get the train ID
                train_id = f"{route_id}_{trip.trip_id}"
                
                # Get stop time updates to determine current and next station
                current_station_id = None
                next_station_id = None
                delay_seconds = 0
                
                if trip_update.stop_time_update:
                    # Find the most recent or current stop
                    now = int(time.time())
                    for i, update in enumerate(trip_update.stop_time_update):
                        if update.HasField('arrival') and update.arrival.time:
                            arrival_time = update.arrival.time
                            if arrival_time <= now:
                                current_station_id = update.stop_id
                                # Get delay if available
                                if update.arrival.HasField('delay'):
                                    delay_seconds = update.arrival.delay
                            else:
                                # This is a future stop
                                if current_station_id and not next_station_id:
                                    next_station_id = update.stop_id
                                break
                
                if not current_station_id and trip_update.stop_time_update:
                    # If we can't determine current station, use the first upcoming stop
                    current_station_id = trip_update.stop_time_update[0].stop_id
                    if len(trip_update.stop_time_update) > 1:
                        next_station_id = trip_update.stop_time_update[1].stop_id
                
                if current_station_id:
                    # Create train object
                    train = Train(
                        train_id=train_id,
                        line_id=route_id,
                        current_position=self._estimate_position(current_station_id, next_station_id),
                        direction=self._parse_direction(trip.direction_id if trip.HasField('direction_id') else 0),
                        current_station_id=current_station_id,
                        next_station_id=next_station_id,
                        timestamp=int(time.time()),
                        speed_mph=0.0,  # Not available in MTA feed
                        trip_id=trip.trip_id,
                        delay_seconds=delay_seconds,
                        line_color=mta_data_loader.get_line_color(route_id)
                    )
                    trains.append(train)
        
        return trains
    
    async def getRealTimeFeed(self, line_ids: List[str]) -> RealTimeFeed:
        """Get real-time feed data for specific subway lines"""
        if not self._initialized:
            await self.initialize()
            
        self._validate_lines(line_ids)
        
        # Determine which feeds we need
        feeds_needed = set()
        for line_id in line_ids:
            feeds_needed.add(self.LINE_TO_FEED[line_id])
        
        # Fetch data for each required feed
        all_trains = []
        all_lines = []
        
        for feed_key in feeds_needed:
            try:
                # Check cache
                if (feed_key in self.cached_feeds and 
                    feed_key in self.last_update and 
                    datetime.now() - self.last_update[feed_key] < self.cache_duration):
                    
                    feed_data = self.cached_feeds[feed_key]
                else:
                    # Fetch fresh data
                    feed = await self._fetch_feed_data(feed_key)
                    feed_data = feed
                    self.cached_feeds[feed_key] = feed_data
                    self.last_update[feed_key] = datetime.now()
                
                # Extract trains for requested lines only
                lines_in_feed = [line for line in line_ids if self.LINE_TO_FEED[line] == feed_key]
                trains = await self._process_feed_entities(feed_data, lines_in_feed)
                all_trains.extend(trains)
                
            except Exception as e:
                logger.error(f"Error processing feed {feed_key}: {e}")
                raise
        
        # Build subway lines with stations and trains
        for line_id in line_ids:
            stations = mta_data_loader.get_stations_for_lines([line_id])
            line_trains = [t for t in all_trains if t.line_id == line_id]
            
            subway_line = SubwayLine(
                line_id=line_id,
                name=f"{line_id} Line",
                color=mta_data_loader.get_line_color(line_id),
                stations=stations,
                segments=[],  # Line segments would require more complex processing
                active_trains=line_trains
            )
            all_lines.append(subway_line)
        
        return RealTimeFeed(
            timestamp=int(time.time()),
            lines=all_lines,
            total_active_trains=len(all_trains),
            feed_version="1.0"
        )
    
    async def getAvailableLines(self) -> List[SubwayLine]:
        """Get all available subway lines with their static information"""
        if not self._initialized:
            await self.initialize()
            
        lines = []
        all_line_ids = mta_data_loader.get_all_supported_lines()
        
        # Filter to only include lines we have real-time feeds for
        supported_lines = [line for line in all_line_ids if line in self.LINE_TO_FEED]
        
        for line_id in supported_lines:
            stations = mta_data_loader.get_stations_for_lines([line_id])
            
            subway_line = SubwayLine(
                line_id=line_id,
                name=f"{line_id} Line",
                color=mta_data_loader.get_line_color(line_id),
                stations=stations,
                segments=[],
                active_trains=[]
            )
            lines.append(subway_line)
        
        return lines
    
    async def getStationsForLine(self, line_id: str) -> List[Station]:
        """Get station information for a specific line"""
        if not self._initialized:
            await self.initialize()
            
        self._validate_lines([line_id])
        return mta_data_loader.get_stations_for_lines([line_id])
    
    async def getActiveTrains(self, line_id: str) -> List[Train]:
        """Get active trains for a specific line"""
        if not self._initialized:
            await self.initialize()
            
        feed_data = await self.getRealTimeFeed([line_id])
        
        for line in feed_data.lines:
            if line.line_id == line_id:
                return line.active_trains
        
        return []
    
    async def healthCheck(self) -> bool:
        """Health check for the service"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Try to fetch a small amount of data
            await self.getRealTimeFeed(['N'])
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def getServiceStatus(self) -> str:
        """Get service status information"""
        if not self._initialized:
            await self.initialize()
            
        status = {
            "service": "MTA Real-time Feed Service",
            "version": "1.0",
            "initialized": self._initialized,
            "supported_lines": list(self.LINE_TO_FEED.keys()),
            "feeds_available": list(self.FEED_URLS.keys()),
            "cache_duration_seconds": self.cache_duration.total_seconds(),
            "cached_feeds": list(self.cached_feeds.keys()),
            "timestamp": int(time.time())
        }
        
        import json
        return json.dumps(status, indent=2)

# Global service instance
mta_feed_service = MTAFeedServiceImpl()
