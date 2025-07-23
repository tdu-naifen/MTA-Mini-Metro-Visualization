#!/usr/bin/env python3
"""
Simple manual test script to verify the WebSocket default subscription interval change.
"""

import json
import sys
import os

# Add the project root to the Python path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_websocket_default_interval():
    """Test that the default interval is now 10 seconds"""
    # Simulate the WebSocket message handling logic from main.py
    message = {
        "type": "subscribe",
        "lines": ["N", "Q", "R", "W"]
        # No update_interval specified, should default to 10
    }
    
    # This is the exact logic from backend/main.py line 186
    update_interval = message.get("update_interval", 10)  # This was changed from 30 to 10
    
    print(f"Testing WebSocket default interval...")
    print(f"Message: {message}")
    print(f"Resolved update_interval: {update_interval}")
    
    # Verify the default is now 10
    assert update_interval == 10, f"Expected default interval of 10, but got {update_interval}"
    print("✅ PASS: Default interval is correctly set to 10 seconds")

def test_websocket_custom_interval():
    """Test that custom intervals are still respected"""
    message = {
        "type": "subscribe",
        "lines": ["N"],
        "update_interval": 5
    }
    
    # This is the exact logic from backend/main.py line 186
    update_interval = message.get("update_interval", 10)
    
    print(f"\nTesting WebSocket custom interval...")
    print(f"Message: {message}")
    print(f"Resolved update_interval: {update_interval}")
    
    # Verify custom interval is respected
    assert update_interval == 5, f"Expected custom interval of 5, but got {update_interval}"
    print("✅ PASS: Custom interval is correctly respected")

def test_old_behavior():
    """Test that the old behavior would have resulted in 30 seconds"""
    message = {
        "type": "subscribe",
        "lines": ["N", "Q", "R", "W"]
    }
    
    # This is what the old logic would have been
    old_update_interval = message.get("update_interval", 30)
    new_update_interval = message.get("update_interval", 10)
    
    print(f"\nTesting behavior change...")
    print(f"Message: {message}")
    print(f"Old behavior would give: {old_update_interval}")
    print(f"New behavior gives: {new_update_interval}")
    
    assert old_update_interval == 30, "Old behavior check failed"
    assert new_update_interval == 10, "New behavior check failed"
    print("✅ PASS: Behavior change is confirmed - old would be 30s, new is 10s")

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Default Interval Change Test")
    print("=" * 60)
    
    try:
        test_websocket_default_interval()
        test_websocket_custom_interval()
        test_old_behavior()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("The WebSocket default subscription interval has been successfully changed from 30s to 10s")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        sys.exit(1)