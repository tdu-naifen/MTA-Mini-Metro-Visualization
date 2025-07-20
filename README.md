# MTA Mini Metro Visualization

A real-time subway visualization app inspired by Mini Metro game style, showing N, Q, R, W train lines with live MTA data.

## Quick Start

This project uses [UV](https://docs.astral.sh/uv/) for fast and modern Python package management.

### Prerequisites
- Python 3.9+
- UV package manager (install with `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup and Run

```bash
# Clone the repository
git clone <your-repo-url>
cd mta-mini-metro

# Install dependencies using UV
uv sync

# Run the server
uv run python run_server.py

# Alternative: use the start script
./start_server.sh
```

The server will start at `http://localhost:8000`

### Development

```bash
# Install development dependencies
uv sync --extra dev

# Run with auto-reload (already enabled in run_server.py)
uv run python run_server.py

# Add new dependencies
uv add package-name

# Add development dependencies
uv add --group dev package-name
```

## Setup

1. Install Python dependencies: `pip install -r requirements.txt`
2. Install Node.js dependencies: `cd frontend && npm install`
3. Generate Thrift schemas: `./scripts/generate_thrift.sh`
4. Start backend: `python -m backend.main`
5. Start frontend: `cd frontend && ng serve`

## Architecture

- **Backend**: Python FastAPI with real-time MTA GTFS feeds
- **Frontend**: Angular with minimalist Metro-style UI
- **Schema**: Apache Thrift for data definitions
- **Maps**: Apple Maps integration
- **Real-time**: WebSocket connections for live updates

## Features

- Real-time train positions for N, Q, R, W lines
- Mini Metro visual style with colored lines and train squares
- Direction indicators with arrows
- Minimalist map overlay
- Live feed updates from MTA API

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /api/lines` - Get all subway lines information
- `GET /api/trains` - Get real-time train positions
- `WebSocket /ws` - Real-time updates for train positions

## Configuration

Create a `.env` file in the project root with your MTA API key:

```
MTA_API_KEY=your_mta_api_key_here
```

Get your API key from [MTA Developer Portal](https://api.mta.info/)
