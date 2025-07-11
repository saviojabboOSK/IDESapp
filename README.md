# IDES 2.0

**Indoor Digital Environment System**

IDES 2.0 turns the raw numbers coming from the sensors in your building into live, easy-to-read charts and plain-English insights.
You open the dashboard, ask questions like “Show me today’s temperature and humidity” or “Forecast CO₂ for the next two weeks”, and the system draws the graphs for you – then keeps them up-to-date as new readings arrive.

---

## What you get

|                          | In plain language                                                                                                   | Under the hood                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Live charts**          | Every graph moves in real time – no page refresh needed.                                                            | FastAPI WebSocket streams new rows; React & Chart.js redraw instantly.                                 |
| **Ask it anything**      | Type a question; a small AI model (or the OpenAI API – you choose) answers and, if helpful, draws a chart.          | Pluggable LLM service reads the latest sensor snapshots and returns JSON the front end can plot.       |
| **Forecast & verify**    | The AI can look at past data, predict the next days, and later overlay the real numbers so you see how well it did. | Forecast data are dashed; new “actual” points paint over them and an automatic MAE/RMSE score appears. |
| **Customise every card** | Click the ⚙️ on a graph, flip it over, pick different metrics, time ranges or chart types.                          | The back face of each React card patches its settings through `/api/graphs/{id}`.                      |
| **Drag & resize layout** | Arrange your favourite charts on the grid – make some big, some small.                                              | dnd-kit & interact.js store layout in localStorage (and optionally the back-end).                      |
| **Automatic clean-up**   | Decide how many weeks of history to keep; old files vanish on their own.                                            | APScheduler runs a purge job using the number of weeks you chose in Settings.                          |

---

## How it works (one-minute tour)

```
Sensors  →  InfluxDB  →  Python worker  →  JSON snapshots  →  FastAPI
                                |                               |
                                |  WebSocket                    |  REST
                                ▼                               ▼
                           React front end  ←–––––– LLM service (local or OpenAI)
```

* The **worker** pulls sensor data every 30 seconds, appending them to a single JSON file per week.
* After every pull it tells the browser “new data!” through a WebSocket.
* The **front end** receives that ping and updates the correct charts.
* When you type a prompt, FastAPI hands the latest snapshots to the **LLM**; the reply may include a ready-to-draw chart plus a short explanation.

---

## What’s in the folders?

```
idesAPP_7_7_2025/
│
├── backend/                 # Python
│   ├── app/                 # FastAPI application
│   │   ├── api/             # HTTP routes & WebSocket
│   │   ├── workers/         # Influx pull, purge, weather, forecast
│   │   └── llm/             # openai_service.py  |  local_service.py
│   └── data/                # *.json snapshots (auto-rotated)
│
└── frontend/                # React 19 + Vite + TS
    ├── public/assets/       # logos
    └── src/                 # components, hooks, pages, Tailwind CSS
```

Everything is standard FastAPI + React; extend or replace pieces without touching the whole stack.

---


## Project Automation: Makefile Commands

This project uses a Makefile to automate setup, development, testing, and deployment. Here are the main commands you can run:

| Command                | Description |
|------------------------|-------------|
| `make install`         | Install all backend (Python) and frontend (Node.js) dependencies. |
| `make install-backend` | Install only backend Python dependencies in a virtual environment. |
| `make install-frontend`| Install only frontend Node.js dependencies using pnpm. |
| `make setup`           | Run full setup, including copying example config and creating data folders. |
| `make activate`        | Show the command to activate the Python virtual environment. |
| `make shell`           | Open a shell with the Python virtual environment activated. |
| `make dev`             | Start both backend (FastAPI) and frontend (React) dev servers. |
| `make dev-backend`     | Start only the backend dev server. |
| `make dev-frontend`    | Start only the frontend dev server. |
| `make backend`         | Alias for `make dev-backend`. |
| `make frontend`        | Alias for `make dev-frontend`. |
| `make build`           | Build the frontend for production. |
| `make test`            | Run all backend and frontend tests. |
| `make test-backend`    | Run backend (Python) tests. |
| `make test-frontend`   | Run frontend (React) tests. |
| `make lint`            | Lint all code (backend and frontend). |
| `make lint-backend`    | Lint backend Python code. |
| `make lint-frontend`   | Lint frontend TypeScript/React code. |
| `make format`          | Format all code (backend and frontend). |
| `make format-backend`  | Format backend Python code. |
| `make format-frontend` | Format frontend TypeScript/React code. |
| `make docker`          | Run the full stack with Docker Compose. |
| `make docker-dev`      | Run the dev stack with Docker Compose. |
| `make docker-prod`     | Run the production stack with Docker Compose. |
| `make docker-llm`      | Run with local LLM service (Ollama). |
| `make logs`            | Show Docker logs. |
| `make clean`           | Remove all build artifacts and dependencies. |
| `make clean-docker`    | Remove Docker containers and volumes. |
| `make status`          | Show status of backend, frontend, and InfluxDB services. |
| `make check`           | Check if dependencies are installed. |
| `make stop`            | Stop all dev servers. |
| `make restart`         | Restart all dev servers. |
| `make install-mac`     | Install dependencies on macOS (requires Homebrew). |
| `make install-linux`   | Install dependencies on Linux. |
| `make install-windows` | Install dependencies on Windows (WSL or Git Bash). |
| `make db-setup`        | Start InfluxDB with Docker and set up sample data. |
| `make db-reset`        | Reset InfluxDB data. |
| `make info`            | Show project info and URLs. |
| `make requirements`    | Show system requirements. |

You can run any of these commands from the project root. For more details, run `make help`.

## Want to tinker?

* Change colours or logos – edit `frontend/src/index.css` and `frontend/public/assets/`.
* Add a new metric – point the worker’s Influx query at it; the front-end settings list reads whatever the back end advertises.
* Swap AI engines – open **Settings → LLM backend**; choose *Local* (eg Ollama) or *OpenAI API*.

Pull requests are welcome – just keep the code formatted (`ruff`, `prettier`) and add a quick test when you add a feature.

---

**Maintainer:** Savio Jabbo · [sjabbo@oshkoshcorp.com](mailto:sjabbo@oshkoshcorp.com)
*Licensed under the OshKosh Restricted License.*

---

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
