"""
Test to verify the WebSocket default subscription interval is set to 10 seconds.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.main import app


@pytest.mark.asyncio
async def test_websocket_default_subscription_interval():
    """Test that WebSocket subscription uses 10s default interval when not specified"""
    
    with TestClient(app) as client:
        # Mock the websocket service methods
        with patch('backend.main.websocket_service.subscribeToLineUpdates', new_callable=AsyncMock) as mock_subscribe:
            with patch('backend.main.websocket_service.start_updates_for_subscription', new_callable=AsyncMock) as mock_start_updates:
                
                # Configure mock to return a subscription ID
                mock_subscribe.return_value = "test-subscription-123"
                
                # Test WebSocket connection with subscription without specifying interval
                with client.websocket_connect("/ws/trains") as websocket:
                    # Send subscription message without update_interval
                    websocket.send_text(json.dumps({
                        "type": "subscribe",
                        "lines": ["N", "Q", "R", "W"]
                    }))
                    
                    # Verify the service was called with default interval of 10
                    mock_subscribe.assert_called_once_with(["N", "Q", "R", "W"], 10)
                    
                    # Verify start_updates_for_subscription was called
                    mock_start_updates.assert_called_once_with("test-subscription-123", websocket.websocket)
                    
                    # Receive the subscription confirmation
                    response = websocket.receive_text()
                    response_data = json.loads(response)
                    
                    assert response_data["type"] == "subscription_created"
                    assert response_data["subscription_id"] == "test-subscription-123"
                    assert response_data["lines"] == ["N", "Q", "R", "W"]
                    assert response_data["update_interval"] == 10  # Should be 10, not 30


@pytest.mark.asyncio 
async def test_websocket_custom_subscription_interval():
    """Test that WebSocket subscription respects custom interval when specified"""
    
    with TestClient(app) as client:
        # Mock the websocket service methods
        with patch('backend.main.websocket_service.subscribeToLineUpdates', new_callable=AsyncMock) as mock_subscribe:
            with patch('backend.main.websocket_service.start_updates_for_subscription', new_callable=AsyncMock) as mock_start_updates:
                
                # Configure mock to return a subscription ID
                mock_subscribe.return_value = "test-subscription-456"
                
                # Test WebSocket connection with custom interval
                with client.websocket_connect("/ws/trains") as websocket:
                    # Send subscription message with custom update_interval
                    websocket.send_text(json.dumps({
                        "type": "subscribe",
                        "lines": ["N"],
                        "update_interval": 5
                    }))
                    
                    # Verify the service was called with custom interval of 5
                    mock_subscribe.assert_called_once_with(["N"], 5)
                    
                    # Receive the subscription confirmation
                    response = websocket.receive_text()
                    response_data = json.loads(response)
                    
                    assert response_data["type"] == "subscription_created"
                    assert response_data["update_interval"] == 5  # Should respect custom value


if __name__ == "__main__":
    pytest.main([__file__])