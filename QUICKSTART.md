# Quick Start Guide

## 🚀 One-Command Setup

### Local Development (Recommended)
```bash
# Install dependencies and start everything
make setup && make dev
```

This will:
1. Create Python virtual environment
2. Install all Python dependencies
3. Install Node.js dependencies with pnpm
4. Create .env configuration
5. Start both backend and frontend servers

**URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Docker Deployment

#### Development with Docker
```bash
make docker-dev
```

#### Production with Docker
```bash
make docker-prod
```

#### With Local LLM (Ollama)
```bash
make docker-llm
```

## 📋 Prerequisites

- **Python 3.10+** and pip
- **Node.js 18+** and npm
- **pnpm** (install with `npm install -g pnpm`)
- **Docker & Docker Compose** (for Docker deployment)

## 🔧 Available Commands

```bash
make help              # Show all available commands
make setup             # Complete project setup
make dev               # Start development servers
make status            # Check service status
make stop              # Stop all services
make clean             # Clean all build artifacts
```

## 🐳 Docker Quick Reference

```bash
# Start full development stack
docker-compose up --build

# Start only specific services
docker-compose up backend influxdb

# View logs
docker-compose logs -f

# Stop and clean
docker-compose down -v
```

## 🛠 Development Workflow

1. **Start development**: `make dev`
2. **Check status**: `make status`
3. **View logs**: `make logs` (for Docker) or check terminal output
4. **Stop services**: `make stop`

## 📊 Default Access

- **InfluxDB**: admin / password123
- **Sample data**: Generated automatically
- **AI Service**: Local LLM (configurable in Settings)
