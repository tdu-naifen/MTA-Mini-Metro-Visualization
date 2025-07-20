"""
MTA Static Data Loader
Loads station and route information from MTA GTFS static feeds
"""
import asyncio
import aiohttp
import csv
import zipfile
import io
import logging
from typing import Dict, List, Set, Optional
from ..generated.mta_data.ttypes import Station, Coordinate, LineSegment, LineColor

logger = logging.getLogger(__name__)

class MTADataLoader:
    """Loads and manages MTA static GTFS data"""
    
    def __init__(self):
        self.stations: Dict[str, Station] = {}
        self.routes: Dict[str, dict] = {}
        self.line_colors = {
            'N': LineColor.YELLOW,
            'Q': LineColor.YELLOW, 
            'R': LineColor.YELLOW,
            'W': LineColor.YELLOW,
            '4': LineColor.GREEN,
            '5': LineColor.GREEN,
            '6': LineColor.GREEN,
            'L': LineColor.BLUE,
            'A': LineColor.BLUE,
            'C': LineColor.BLUE,
            'E': LineColor.BLUE,
            'B': LineColor.ORANGE,
            'D': LineColor.ORANGE,
            'F': LineColor.ORANGE,
            'M': LineColor.ORANGE,
            'G': LineColor.RED,
            'J': LineColor.RED,
            'Z': LineColor.RED,
            '1': LineColor.RED,
            '2': LineColor.RED,
            '3': LineColor.RED,
            '7': LineColor.PURPLE,
        }
        
    async def load_static_data(self) -> bool:
        """Load static GTFS data from MTA"""
        try:
            # Load subway static data
            subway_url = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
            
            async with aiohttp.ClientSession() as session:
                logger.info("Downloading MTA static GTFS data...")
                async with session.get(subway_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        await self._process_gtfs_data(content)
                        logger.info(f"Loaded {len(self.stations)} stations and {len(self.routes)} routes")
                        return True
                    else:
                        logger.error(f"Failed to download GTFS data: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error loading static data: {e}")
            return False
    
    async def _process_gtfs_data(self, zip_content: bytes):
        """Process GTFS ZIP file content"""
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Load stops (stations)
            if 'stops.txt' in zf.namelist():
                await self._load_stops(zf.read('stops.txt').decode('utf-8'))
            
            # Load routes
            if 'routes.txt' in zf.namelist():
                await self._load_routes(zf.read('routes.txt').decode('utf-8'))
                
            # Load stop_times to understand which routes serve which stations
            if 'trips.txt' in zf.namelist() and 'stop_times.txt' in zf.namelist():
                trips_data = zf.read('trips.txt').decode('utf-8')
                stop_times_data = zf.read('stop_times.txt').decode('utf-8')
                await self._link_routes_to_stations(trips_data, stop_times_data)
    
    async def _load_stops(self, stops_content: str):
        """Load station data from stops.txt"""
        reader = csv.DictReader(io.StringIO(stops_content))
        
        for row in reader:
            # Only include subway stations (not bus stops)
            if row.get('location_type') == '1':  # Parent station
                continue
                
            stop_id = row['stop_id']
            
            # Filter for subway stations only (usually have specific ID patterns)
            if not any(char.isalpha() for char in stop_id):
                continue
                
            station = Station(
                station_id=stop_id,
                name=row['stop_name'],
                location=Coordinate(
                    latitude=float(row['stop_lat']),
                    longitude=float(row['stop_lon'])
                ),
                line_ids=[],  # Will be populated later
                is_terminus=False,  # Will be determined later
                accessibility_info="accessible" if row.get('wheelchair_accessible', '0') == '1' else "not_accessible"
            )
            
            self.stations[stop_id] = station
    
    async def _load_routes(self, routes_content: str):
        """Load route data from routes.txt"""
        reader = csv.DictReader(io.StringIO(routes_content))
        
        for row in reader:
            # Only subway routes
            if row.get('route_type') == '1':  # Subway
                route_id = row['route_id']
                self.routes[route_id] = {
                    'short_name': row.get('route_short_name', route_id),
                    'long_name': row.get('route_long_name', ''),
                    'color': row.get('route_color', ''),
                    'text_color': row.get('route_text_color', '')
                }
    
    async def _link_routes_to_stations(self, trips_content: str, stop_times_content: str):
        """Link routes to stations using trips and stop_times"""
        # Build trip_id to route_id mapping
        trip_to_route = {}
        reader = csv.DictReader(io.StringIO(trips_content))
        for row in reader:
            trip_to_route[row['trip_id']] = row['route_id']
        
        # Build route to stations mapping
        route_stations = {}
        reader = csv.DictReader(io.StringIO(stop_times_content))
        
        for row in reader:
            trip_id = row['trip_id']
            stop_id = row['stop_id']
            
            if trip_id in trip_to_route and stop_id in self.stations:
                route_id = trip_to_route[trip_id]
                
                if route_id not in route_stations:
                    route_stations[route_id] = set()
                route_stations[route_id].add(stop_id)
        
        # Update station line_ids
        for route_id, station_ids in route_stations.items():
            route_short_name = self.routes.get(route_id, {}).get('short_name', route_id)
            
            for station_id in station_ids:
                if station_id in self.stations:
                    if route_short_name not in self.stations[station_id].line_ids:
                        self.stations[station_id].line_ids.append(route_short_name)
    
    def get_stations_for_lines(self, line_ids: List[str]) -> List[Station]:
        """Get all stations that serve the specified lines"""
        result_stations = []
        
        for station in self.stations.values():
            # Check if station serves any of the requested lines
            if any(line_id in station.line_ids for line_id in line_ids):
                result_stations.append(station)
        
        return result_stations
    
    def get_line_color(self, line_id: str) -> LineColor:
        """Get the line color for a given line ID"""
        return self.line_colors.get(line_id, LineColor.YELLOW)
    
    def get_all_supported_lines(self) -> List[str]:
        """Get all subway lines that have stations"""
        all_lines = set()
        for station in self.stations.values():
            all_lines.update(station.line_ids)
        return sorted(list(all_lines))

# Global instance
mta_data_loader = MTADataLoader()
