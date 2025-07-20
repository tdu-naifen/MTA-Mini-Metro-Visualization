#!/usr/bin/env python3
"""
Run the MTA Mini Metro backend server
"""

import uvicorn
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point for the server"""
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable auto-reload to prevent WebSocket disconnections
        log_level="info"
    )

if __name__ == "__main__":
    main()
