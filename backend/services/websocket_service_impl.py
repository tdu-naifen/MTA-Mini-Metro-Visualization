"""
WebSocket Service Implementation
Implements real-time updates via WebSocket for subway lines
"""
import asyncio
import logging
import json
import uuid
from typing import Dict, List, Set, Optional
from datetime import datetime

from ..generated.mta_data.ttypes import (
    WebSocketMessage, MessageType, MTAServiceException, InvalidLineException
)
from ..generated.mta_data.WebSocketService import Iface as WebSocketServiceIface
from .mta_feed_service_impl import mta_feed_service

logger = logging.getLogger(__name__)

class Subscription:
    """Represents an active WebSocket subscription"""
    
    def __init__(self, subscription_id: str, line_ids: List[str], update_interval: int):
        self.subscription_id = subscription_id
        self.line_ids = line_ids
        self.update_interval = update_interval
        self.created_at = datetime.now()
        self.last_update = None
        self.is_active = True
        self.task: Optional[asyncio.Task] = None

class WebSocketServiceImpl(WebSocketServiceIface):
    """Implementation of WebSocketService for real-time updates"""
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.websocket_connections: Dict[str, any] = {}  # WebSocket connections by subscription_id
        self._update_tasks: Dict[str, asyncio.Task] = {}
        
    async def subscribeToLineUpdates(self, line_ids: List[str], update_interval_seconds: int) -> str:
        """Start real-time updates for specific lines"""
        try:
            # Validate lines
            await mta_feed_service.initialize()
            mta_feed_service._validate_lines(line_ids)
            
            # Create subscription
            subscription_id = str(uuid.uuid4())
            subscription = Subscription(subscription_id, line_ids, update_interval_seconds)
            
            self.subscriptions[subscription_id] = subscription
            
            logger.info(f"Created subscription {subscription_id} for lines {line_ids} with {update_interval_seconds}s interval")
            return subscription_id
            
        except InvalidLineException as e:
            raise e
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise MTAServiceException(
                message=f"Failed to create subscription: {str(e)}",
                error_code=500
            )
    
    async def unsubscribeFromUpdates(self, subscription_id: str) -> None:
        """Stop real-time updates for a subscription"""
        try:
            if subscription_id in self.subscriptions:
                subscription = self.subscriptions[subscription_id]
                subscription.is_active = False
                
                # Cancel update task if running
                if subscription.task and not subscription.task.done():
                    subscription.task.cancel()
                
                # Remove from tracking
                if subscription_id in self._update_tasks:
                    del self._update_tasks[subscription_id]
                
                if subscription_id in self.websocket_connections:
                    del self.websocket_connections[subscription_id]
                
                del self.subscriptions[subscription_id]
                
                logger.info(f"Unsubscribed {subscription_id}")
            else:
                logger.warning(f"Subscription {subscription_id} not found")
                
        except Exception as e:
            logger.error(f"Error unsubscribing {subscription_id}: {e}")
            raise MTAServiceException(
                message=f"Failed to unsubscribe: {str(e)}",
                error_code=500
            )
    
    async def getActiveSubscriptions(self) -> List[str]:
        """Get active subscription information"""
        return list(self.subscriptions.keys())
    
    async def start_updates_for_subscription(self, subscription_id: str, websocket):
        """Start the update loop for a specific subscription"""
        if subscription_id not in self.subscriptions:
            logger.error(f"Subscription {subscription_id} not found")
            return
        
        subscription = self.subscriptions[subscription_id]
        self.websocket_connections[subscription_id] = websocket
        
        try:
            while subscription.is_active:
                try:
                    # Check if subscription still exists and websocket is still connected
                    if subscription_id not in self.subscriptions:
                        logger.info(f"Subscription {subscription_id} was removed, stopping updates")
                        break
                    
                    # Get the current websocket connection for this subscription
                    current_websocket = self.websocket_connections.get(subscription_id)
                    if not current_websocket:
                        logger.warning(f"No websocket connection found for subscription {subscription_id}")
                        break
                    
                    # Get real-time data
                    feed_data = await mta_feed_service.getRealTimeFeed(subscription.line_ids)
                    
                    # Create WebSocket message
                    message = WebSocketMessage(
                        type=MessageType.FULL_REFRESH,
                        timestamp=feed_data.timestamp,
                        full_data=feed_data
                    )
                    
                    # Send to the specific WebSocket connection for this subscription
                    success = await self.send_message_to_subscription(subscription_id, message)
                    if not success:
                        logger.warning(f"Failed to send message to subscription {subscription_id}, stopping updates")
                        break
                    
                    subscription.last_update = datetime.now()
                    
                    # Wait for next update
                    await asyncio.sleep(subscription.update_interval)
                    
                except asyncio.CancelledError:
                    logger.info(f"Update task for subscription {subscription_id} was cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in update loop for {subscription_id}: {e}")
                    
                    # Send error message
                    error_message = WebSocketMessage(
                        type=MessageType.ERROR,
                        timestamp=int(datetime.now().timestamp()),
                        error_message=str(e)
                    )
                    
                    try:
                        await self.send_message_to_subscription(subscription_id, error_message)
                    except:
                        logger.error(f"Failed to send error message to subscription {subscription_id}")
                    
                    # Wait before retry
                    await asyncio.sleep(min(subscription.update_interval, 30))
                    
        except Exception as e:
            logger.error(f"Critical error in subscription {subscription_id}: {e}")
        finally:
            # Cleanup
            subscription.is_active = False
            if subscription_id in self.websocket_connections:
                del self.websocket_connections[subscription_id]
    
    def _thrift_to_dict(self, thrift_obj) -> dict:
        """Convert Thrift object to dictionary for JSON serialization"""
        if hasattr(thrift_obj, '__dict__'):
            result = {}
            for key, value in thrift_obj.__dict__.items():
                if value is not None:
                    if hasattr(value, '__dict__'):
                        result[key] = self._thrift_to_dict(value)
                    elif isinstance(value, list):
                        result[key] = [self._thrift_to_dict(item) if hasattr(item, '__dict__') else item for item in value]
                    else:
                        result[key] = value
            return result
        else:
            return thrift_obj
    
    async def cleanup(self):
        """Cleanup all subscriptions and tasks"""
        logger.info("Cleaning up WebSocket service...")
        
        # Cancel all active subscriptions
        for subscription_id in list(self.subscriptions.keys()):
            await self.unsubscribeFromUpdates(subscription_id)
        
        logger.info("WebSocket service cleanup complete")
    
    async def send_message_to_subscription(self, subscription_id: str, message: WebSocketMessage) -> bool:
        """Send a message to a specific subscription's WebSocket connection"""
        try:
            if subscription_id not in self.subscriptions:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
            
            websocket = self.websocket_connections.get(subscription_id)
            if not websocket:
                logger.warning(f"No WebSocket connection found for subscription {subscription_id}")
                return False
            
            message_dict = self._thrift_to_dict(message)
            await websocket.send_text(json.dumps(message_dict))
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to subscription {subscription_id}: {e}")
            return False

    async def broadcast_to_all_subscriptions(self, message: WebSocketMessage):
        """Broadcast a message to all active subscriptions"""
        for subscription_id in list(self.subscriptions.keys()):
            await self.send_message_to_subscription(subscription_id, message)
    
    async def get_subscription_info(self, subscription_id: str) -> Optional[Dict]:
        """Get information about a specific subscription"""
        if subscription_id not in self.subscriptions:
            return None
        
        subscription = self.subscriptions[subscription_id]
        return {
            "subscription_id": subscription.subscription_id,
            "line_ids": subscription.line_ids,
            "update_interval": subscription.update_interval,
            "created_at": subscription.created_at.isoformat(),
            "last_update": subscription.last_update.isoformat() if subscription.last_update else None,
            "is_active": subscription.is_active,
            "has_websocket": subscription_id in self.websocket_connections
        }

# Global service instance
websocket_service = WebSocketServiceImpl()
