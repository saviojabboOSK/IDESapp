# IDES – Indoor Digital Environment System

*Real-time insights into air quality and working conditions at single-sensor granularity, powered by natural-language visualisations and predictive analytics.*

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Codebase Tour](#codebase-tour)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Overview
IDES delivers detailed monitoring of indoor environments—temperature, humidity, CO₂, VOCs, occupancy and lighting—down to each sensor.  
A local LLM interprets plain-language prompts to generate graphs, analyses, or both in chat-style bubbles.

## Features
- **Natural-Language Visualisations** – ask “Plot today’s temperature vs. humidity” and get an interactive chart.  
- **Sensor-Level Telemetry** – live data pulled from InfluxDB; mock data substitutes if the DB is offline.  
- **Predictive Forecasting** – simple statistical baseline today; ready for ML model plug-in.  
- **REST API** – FastAPI back-end with zero hard-coded metrics or URLs; all configurable by env vars.

## Architecture
```text
┌───────────────┐
│ Sensors (BLE) │
└──────┬────────┘
       ▼
┌─────────────────────┐           ┌──────────────────────────────┐
│   InfluxDB (time-DB)│◄───pull───┤  workers.py (orchestration)  │
└─────────────────────┘           └─────────┬────────────────────┘
                                            ▼
                                   ┌──────────────────────────────┐
                                   │ llm_service.py (local LLM)   │
                                   └─────────┬────────────────────┘
                                             ▼
                                   ┌──────────────────────────────┐
                                   │ main.py (FastAPI HTTP layer) │
                                   └─────────┬────────────────────┘
                                             ▼
                                   ┌──────────────────────────────┐
                                   │   static/ (HTML/CSS/JS)      │
                                   └──────────────────────────────┘
```
## Codebase Tour
| Path | What it contains / does |
|------|-------------------------|
| **backend/main.py** | **FastAPI entry point**.<br>• Mounts `/static/`, serves `index.html`.<br>• CRUD routes for `graphs.json`.<br>• `/api/analyze` – receives chat history and delegates to `workers.analyze_prompt`. |
| **backend/workers.py** | **Orchestrator**.<br>• Parses the latest user prompt to decide metrics & time-window.<br>• Calls `influx_service.fetch_timeseries` with a safe fallback to mock data.<br>• Summarises DB results and passes everything to `llm_service.smart_response`. |
| **backend/llm_service.py** | **All LLM logic**.<br>• Loads templates from `llm_prompts.py`.<br>• Talks to your local Ollama/OpenAI-compatible endpoint.<br>• Normalises raw LLM output into the front-end schema (`Graph`, `Analysis`, or plain `Chat`). |
| **backend/influx_service.py** | Thin async wrapper around `influxdb-client`. Env vars set URL, token, org, bucket. |
| **backend/llm_prompts.py** | Prompt templates, system messages, and JSON-schema instructions—no code. |
| **backend/graphs.json** | Simple on-disk store of saved graph objects (`title`, `series`, `is_fav`, …). |
| **static/index.html** | Single-page UI shell. Hooks to `app.js` and `style.css`. |
| **static/app.js** | Front-end logic: sends prompts to `/api/analyze`, renders chat bubbles/graphs, and manages favourites. |
| **static/style.css** | Tailwind-style custom rules that define the look & feel. |
| **static/assets/** | *(Optional)* Place all logos and images here; update paths like `src="assets/logo.png"` in HTML/CSS. |

> **Tip**: nothing outside `static/` is served to the browser, so moving images into `static/assets/` is safe—just adjust references.

---

## Getting Started

### Prerequisites
- Python ≥ 3.10  
- Node.js (optional, only if you plan to rebuild front-end assets)  
- InfluxDB 2.x (local or remote)  
- Ollama or another OpenAI-compatible LLM endpoint on `http://localhost:11434/`

### Quick Start
```bash
git clone https://github.com/your-org/IDES.git
cd IDES/backend
python -m venv .venv && . .venv/Scripts/activate  # Windows PowerShell variant
pip install -r requirements.txt                   # FastAPI, influxdb-client, openai, uvicorn
set INFLUXDB_URL=http://localhost:8086
set INFLUXDB_BUCKET=sensors
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 in your browser.

## Usage

* Open the web/mobile UI.
* Type requests like “Show me today’s CO₂ heatmap for Facility A” or “Forecast humidity in Zone 3 for the next 24 hours.”
* Download generated diagrams or embed them in reports.

## Contributing

1. Fork the repo.
2. Create a branch (git checkout -b feature/YourFeature).
3. Commit changes and push.
4. Open a Pull Request.

## License

Under the OshKosh Restricted License.

## Contact

**Project Lead:** Savio Jabbo, ADIC DT Intern – [sjabbo@oshkoshcorp.com](mailto:sjabbo@oshkoshcorp.com)
**GitHub:** [https://github.com/saviojabboOSK/IDESapp](https://github.com/saviojabboOSK/IDESapp)
