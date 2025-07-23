#!/usr/bin/env python3
"""
Demo script to show the WebSocket interval change in action
"""
import json

def demo_websocket_logic():
    """Demonstrate the WebSocket message handling logic"""
    
    print("🚇 MTA Mini Metro WebSocket Subscription Interval Demo")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "name": "Default behavior (no interval specified)",
            "message": {
                "type": "subscribe",
                "lines": ["N", "Q", "R", "W"]
            }
        },
        {
            "name": "Custom interval specified",
            "message": {
                "type": "subscribe", 
                "lines": ["N"],
                "update_interval": 5
            }
        },
        {
            "name": "Empty lines with no interval",
            "message": {
                "type": "subscribe",
                "lines": []
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        message = test_case["message"]
        print(f"📨 Client Message: {json.dumps(message, indent=2)}")
        
        # This is the exact logic from backend/main.py after our change
        lines = message.get("lines", ["N", "Q", "R", "W"])  
        update_interval = message.get("update_interval", 10)  # Changed from 30 to 10
        
        print(f"🔧 Server Processing:")
        print(f"   - Extracted lines: {lines}")
        print(f"   - Resolved interval: {update_interval} seconds")
        
        # Show what would be sent back to client
        response = {
            "type": "subscription_created",
            "subscription_id": f"demo-{i}",
            "lines": lines,
            "update_interval": update_interval
        }
        print(f"📤 Server Response: {json.dumps(response, indent=2)}")
        
        # Show the difference from old behavior
        old_interval = message.get("update_interval", 30)
        if old_interval != update_interval:
            print(f"⚡ Change Impact: Old would be {old_interval}s, now {update_interval}s")
            print(f"   ➡️  Data refreshes {old_interval/update_interval:.1f}x more frequently!")
    
    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("The WebSocket now polls every 10 seconds by default instead of 30 seconds,")
    print("providing 3x more frequent updates for better real-time visualization!")
    print("=" * 60)

if __name__ == "__main__":
    demo_websocket_logic()