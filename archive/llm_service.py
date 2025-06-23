# llm_service.py
import httpx, datetime, json, math
from openai import AsyncOpenAI

# New Ollama client using OpenAI compatibility API
CLIENT = AsyncOpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama',  # required but not actually used by Ollama
)

GRAPH_MAX = 30                     # clip long series for readability

# --- NOAA Data Fetching ---
# Fetches temperature data from NOAA API for a given state and date range.
async def _fetch_noaa_temps(state: str, days: int = 30):
    """
    Return (dates:list[str YYYY-MM-DD], temps:list[float]) for the last <days>
    of average daily temps in the given US state using NOAA's Climate Data API.
    """
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    token = "YOUR_NOAA_TOKEN"                  # put this in an env-var in prod
    url   = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
    params = {
        "datasetid": "GHCND",
        "datatypeid": "TAVG",                  # average °F *10
        "locationid": f"FIPS:{state}",
        "units": "standard",
        "startdate": start.isoformat(),
        "enddate":   end.isoformat(),
        "limit": 1000
    }
    hdrs = {"token": token}

    async with httpx.AsyncClient(timeout=15) as s:
        r = await s.get(url, params=params, headers=hdrs)
        r.raise_for_status()
        raw = sorted(r.json()["results"], key=lambda d: d["date"])
        dates = [d["date"][:10] for d in raw]
        temps = [round(d["value"], 1)           # NOAA sends tenths of °F
                 if d["value"] is not None else math.nan
                 for d in raw]
        return dates[-days:], temps[-days:]

# --- analyze_prompt: LLM/Rule-based Graph Generation ---
# Decides if the prompt is a weather request (rule-based) or sends to GPT-4. Always returns a dict with description, title, and series.
async def analyze_prompt(prompt: str) -> dict:
    """
    Parse <prompt>, decide if it's a weather-graph request, otherwise ask GPT-4.
    Always return: description:str, title:str, series:list[dict].
    """
    p = prompt.lower()

    # ---------- very light rule-based recogniser ---------------------------
    if "last" in p and "day" in p and "temp" in p:
        # crude geography heuristics
        loc = "WI" if "wi" in p or "wisconsin" in p else \
              "IL" if "chicago" in p else None
        if loc:
            try:
                x, y = await _fetch_noaa_temps(state=loc, days=30)
                label = f"{'Wisconsin' if loc=='WI' else 'Chicago'} Temperature"
                title = f"Daily High Temperatures – last 30 days ({label})"
                desc  = (f"Here’s the daily average temperature for the past "
                         f"30 days in {label.split()[0]}.")
                return {
                    "description": desc,
                    "title": title,
                    "series": [{"label": label, "x": x, "y": y}]
                }
            except Exception as e:
                return {
                    "description": f"Couldn’t fetch NOAA data: {e}",
                    "title": "",
                    "series": []
                }

    # ---------- fallback: let GPT format its own data ----------------------
    sys = ("You are a Python plotting assistant. "
           "Respond ONLY with JSON of the shape "
           '{"description":str,"title":str,"series":[…]}.')
    res = await CLIENT.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys},
                  {"role":"user",  "content":prompt}],
        temperature=0.3
    )
    # ensure valid JSON
    try:
        return json.loads(res.choices[0].message.content)
    except Exception:
        return {
            "description": res.choices[0].message.content,
            "title": "",
            "series": []
        }
