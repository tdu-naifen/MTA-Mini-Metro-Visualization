import os
from typing import Dict, List, ClassVar
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # MTA API configuration
    MTA_API_KEY: str = ""
    MTA_FEED_URL: str = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw"
    
    # Database configuration (for future use)
    DATABASE_URL: str = "sqlite:///./mta_metro.db"
    
    # Redis configuration (for caching)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Update intervals
    FEED_UPDATE_INTERVAL: int = 30  # seconds
    WEBSOCKET_HEARTBEAT: int = 10   # seconds
    
    # Geographic bounds for NYC subway system
    NYC_BOUNDS: ClassVar[Dict[str, float]] = {
        "north": 40.917577,
        "south": 40.477399,
        "east": -73.700272,
        "west": -74.259090
    }
    
    # Line configuration
    ACTIVE_LINES: ClassVar[List[str]] = ["N", "Q", "R", "W"]
    
    class Config:
        env_file = ".env"

settings = Settings()
