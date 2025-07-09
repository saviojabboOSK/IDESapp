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

## Running it yourself (laptop demo)

1. **Install prerequisites**

   * Python ≥ 3.10   `pip install -r backend/requirements.txt`
   * Node + PNPM   `pnpm install --prefix frontend`
   * InfluxDB 2.x running locally (or set the URL in `.env`)

2. **Copy the example settings**

   ```bash
   cd backend
   cp .env.example .env      # fill INFLUX_URL, OPENAI_API_KEY if you like
   ```

3. **Start the services**

   ```bash
   # terminal 1 – Python API + background jobs
   uvicorn app.main:app --reload

   # terminal 2 – React dev server
   pnpm --prefix ../frontend dev
   ```

   Visit **[http://localhost:5173](http://localhost:5173)** in your browser. Data will begin to appear as soon as the first pull finishes.

> **Production** – run `docker compose -f docker-compose.yml --profile prod up -d`.
> Nginx will serve the built React site and proxy API + WebSocket traffic to Uvicorn.

---

## Want to tinker?

* Change colours or logos – edit `frontend/src/index.css` and `frontend/public/assets/`.
* Add a new metric – point the worker’s Influx query at it; the front-end settings list reads whatever the back end advertises.
* Swap AI engines – open **Settings → LLM backend**; choose *Local* (eg Ollama) or *OpenAI API*.

Pull requests are welcome – just keep the code formatted (`ruff`, `prettier`) and add a quick test when you add a feature.

---

**Maintainer:** Savio Jabbo · [sjabbo@oshkoshcorp.com](mailto:sjabbo@oshkoshcorp.com)
*Licensed under the OshKosh Restricted License.*
