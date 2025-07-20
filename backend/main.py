from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging
from typing import List, Dict, Optional
import json

from .services.mta_feed_service_impl import mta_feed_service
from .services.websocket_service_impl import websocket_service
from .generated.mta_data.ttypes import (
    SubwayLine, Train, RealTimeFeed, MTAServiceException, 
    InvalidLineException, FeedUnavailableException
)
from .models.api_models import (
    SubwayLineModel, TrainModel, RealTimeFeedModel,
    thrift_to_pydantic_line, thrift_to_pydantic_train, thrift_to_pydantic_feed
)
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MTA Mini Metro API",
    description="Real-time MTA subway visualization API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
# Services are imported as singletons and will be initialized when first used

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting MTA Mini Metro API...")
    await mta_feed_service.initialize()
    logger.info("MTA Mini Metro API started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down MTA Mini Metro API...")
    await mta_feed_service.cleanup()
    await websocket_service.cleanup()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MTA Mini Metro API", 
        "status": "running",
        "version": "1.0.0",
        "supported_lines": ["N", "Q", "R", "W", "B", "D", "F", "M", "A", "C", "E", "G", "J", "Z", "L", "1", "2", "3", "4", "5", "6", "7"]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        is_healthy = await mta_feed_service.healthCheck()
        status = await mta_feed_service.getServiceStatus()
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service_info": json.loads(status)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/api/lines", response_model=List[SubwayLineModel])
async def get_available_lines():
    """Get all available subway lines"""
    try:
        lines = await mta_feed_service.getAvailableLines()
        return [thrift_to_pydantic_line(line) for line in lines]
    except MTAServiceException as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting available lines: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/lines/{line_id}/stations")
async def get_stations_for_line(line_id: str):
    """Get stations for a specific line"""
    try:
        stations = await mta_feed_service.getStationsForLine(line_id.upper())
        return [station.__dict__ for station in stations]
    except InvalidLineException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except MTAServiceException as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting stations for line {line_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/lines/{line_id}/trains", response_model=List[TrainModel])
async def get_active_trains(line_id: str):
    """Get active trains for a specific line"""
    try:
        trains = await mta_feed_service.getActiveTrains(line_id.upper())
        return [thrift_to_pydantic_train(train) for train in trains]
    except InvalidLineException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except FeedUnavailableException as e:
        raise HTTPException(status_code=503, detail=e.message)
    except MTAServiceException as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting trains for line {line_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/realtime", response_model=RealTimeFeedModel)
async def get_realtime_feed(lines: str = Query(..., description="Comma-separated list of line IDs (e.g., 'N,Q,R,W')")):
    """Get real-time feed data for specified lines"""
    try:
        line_ids = [line.strip().upper() for line in lines.split(',')]
        feed_data = await mta_feed_service.getRealTimeFeed(line_ids)
        return thrift_to_pydantic_feed(feed_data)
    except InvalidLineException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except FeedUnavailableException as e:
        raise HTTPException(status_code=503, detail=e.message)
    except MTAServiceException as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting real-time feed for lines {lines}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Legacy endpoints for backward compatibility
@app.get("/api/lines/{line_id}", response_model=SubwayLineModel)
async def get_line(line_id: str):
    """Get specific subway line data (legacy endpoint)"""
    try:
        feed_data = await mta_feed_service.getRealTimeFeed([line_id.upper()])
        for line in feed_data.lines:
            if line.line_id == line_id.upper():
                return thrift_to_pydantic_line(line)
        raise HTTPException(status_code=404, detail="Line not found")
    except InvalidLineException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting line {line_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/trains/{line_id}", response_model=List[TrainModel])
async def get_trains_for_line_legacy(line_id: str):
    """Get all trains for a specific line (legacy endpoint)"""
    return await get_active_trains(line_id)

@app.get("/api/feed", response_model=RealTimeFeedModel)
async def get_real_time_feed():
    """Get complete real-time feed data for NQRW lines (legacy endpoint)"""
    return await get_realtime_feed("N,Q,R,W")

@app.websocket("/ws/trains")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time train updates"""
    await websocket.accept()
    subscription_id = None
    
    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types from client
            if message.get("type") == "subscribe":
                lines = message.get("lines", ["N", "Q", "R", "W"])
                update_interval = message.get("update_interval", 30)
                
                # Create subscription
                subscription_id = await websocket_service.subscribeToLineUpdates(lines, update_interval)
                
                # Start update loop for this subscription
                asyncio.create_task(websocket_service.start_updates_for_subscription(subscription_id, websocket))
                
                # Send confirmation
                await websocket.send_text(json.dumps({
                    "type": "subscription_created",
                    "subscription_id": subscription_id,
                    "lines": lines,
                    "update_interval": update_interval
                }))
                
            elif message.get("type") == "unsubscribe":
                if subscription_id:
                    await websocket_service.unsubscribeFromUpdates(subscription_id)
                    subscription_id = None
                    
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed"
                    }))
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for subscription {subscription_id}")
        if subscription_id:
            await websocket_service.unsubscribeFromUpdates(subscription_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if subscription_id:
            await websocket_service.unsubscribeFromUpdates(subscription_id)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass  # Connection might be closed

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
