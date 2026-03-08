# Mission Control Setup Guide

## Quick Start

Mission Control is a metadata and coordination layer for OpenClaw agents. Follow this guide to get up and running in minutes.

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Docker (optional, for production setup)
- OpenClaw gateway running on port 18789

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mission-control.git
cd mission-control
```

### 2. Frontend Setup (V1 Dashboard)

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### 3. Backend Setup (V2 API)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python main.py  # or uvicorn main:app --reload
```

The API will be available at:
- http://localhost:8000 (or 8001 if 8000 is in use)
- API Documentation: http://localhost:8000/docs

### 4. Test the Setup

```bash
# Test backend API
cd backend
python test_api.py

# Test frontend
curl http://localhost:3000
```

## Docker Setup (Production)

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose run migrate

# View logs
docker-compose logs -f
```

### Services

- **PostgreSQL**: Port 5432 - Metadata storage
- **Redis**: Port 6379 - Event pub/sub and caching
- **Backend API**: Port 8000 - FastAPI server
- **Frontend**: Port 3000 - Next.js dashboard

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://mission_control:mission_control@localhost:5432/mission_control
REDIS_URL=redis://localhost:6379/0

# OpenClaw Integration
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
OPENCLAW_API_URL=http://127.0.0.1:18789
OPENCLAW_TOKEN=your-token-here

# Server
PORT=8000
ENVIRONMENT=development
```

### Frontend Configuration

Update `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SSE_URL=http://localhost:8000/api/v1/stream
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Mission Control                      │
├───────────────────┬─────────────────────────────────────┤
│    Frontend       │           Backend                    │
│    (Next.js)      │          (FastAPI)                  │
│                   │                                      │
│  ┌─────────────┐  │  ┌──────────────┐  ┌────────────┐ │
│  │  Dashboard  │──┼──│   REST API   │  │ PostgreSQL │ │
│  │   Views     │  │  │              │──│  Metadata  │ │
│  └─────────────┘  │  └──────────────┘  └────────────┘ │
│                   │           │                         │
│  ┌─────────────┐  │  ┌──────────────┐  ┌────────────┐ │
│  │     SSE     │◄─┼──│     SSE      │◄─│   Redis    │ │
│  │   Client    │  │  │   Publisher  │  │   PubSub   │ │
│  └─────────────┘  │  └──────────────┘  └────────────┘ │
│                   │           │                         │
│                   │  ┌──────────────┐                  │
│                   │  │   OpenClaw   │                  │
│                   │  │   Adapter    │                  │
│                   │  └──────┬───────┘                  │
└───────────────────┴─────────┼──────────────────────────┘
                              │
                    ┌─────────▼───────────┐
                    │  OpenClaw Gateway   │
                    │     Port 18789      │
                    └─────────────────────┘
```

## API Endpoints

### Core Endpoints

- `GET /health` - Health check
- `GET /api/v1/agents` - List agents
- `POST /api/v1/agents` - Create agent
- `GET /api/v1/tasks` - List tasks
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/jobs` - List jobs
- `POST /api/v1/jobs` - Create job
- `GET /api/v1/stream` - SSE event stream

### Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI with all endpoints.

## Development Workflow

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
npm test
```

### Code Formatting

```bash
# Python (backend)
black backend/
ruff check backend/

# TypeScript (frontend)
npm run lint
npm run format
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8001
```

### Frontend Not Loading

```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql postgresql://mission_control:mission_control@localhost:5432/mission_control
```

### OpenClaw Connection Failed

Ensure OpenClaw gateway is running:

```bash
# Check if gateway is accessible
curl http://127.0.0.1:18789/health
```

## Production Deployment

### Google Cloud Platform

1. **Cloud Run** for API and Frontend
2. **Cloud SQL** for PostgreSQL
3. **Memorystore** for Redis
4. **Secret Manager** for credentials

### Deploy to Cloud Run

```bash
# Build and push images
gcloud builds submit --tag gcr.io/PROJECT_ID/mission-control-backend
gcloud builds submit --tag gcr.io/PROJECT_ID/mission-control-frontend

# Deploy backend
gcloud run deploy mission-control-backend \
  --image gcr.io/PROJECT_ID/mission-control-backend \
  --platform managed \
  --allow-unauthenticated

# Deploy frontend
gcloud run deploy mission-control-frontend \
  --image gcr.io/PROJECT_ID/mission-control-frontend \
  --platform managed \
  --allow-unauthenticated
```

## Support

- GitHub Issues: https://github.com/yourusername/mission-control/issues
- Documentation: /docs
- OpenClaw Integration: See OPENCLAW_BRIDGE.md

## License

MIT License - See LICENSE file for details.