# workers.py

import json
from PySide6.QtCore import QThread, Signal
from openai import OpenAI

class ChatWorker(QThread):
    """
    Worker thread that sends chat_history to OpenAI, parses JSON,
    and emits (description, title, series_list) once done.
    """
    result_ready = Signal(str, str, list)

    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY environment variable not set in ChatWorker")
            raise ValueError("OPENAI_API_KEY environment variable not set")
        else:
            print("OPENAI_API_KEY found in ChatWorker, initializing OpenAI client")
        self.client = OpenAI(api_key=api_key)

    def run(self):
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=self.chat_history
            )
            raw = completion.choices[0].message.content.strip()
        except Exception:
            raw = '{"description": "Sorry, I could not connect to ChatGPT.", "title": "", "series": []}'

        try:
            import json
            parsed = json.loads(raw)
            desc = parsed.get("description", "")
            title = parsed.get("title", "")
            series = parsed.get("series", [])
            if not isinstance(series, list):
                series = []
        except Exception:
            desc = raw
            title = ""
            series = []

        self.result_ready.emit(desc, title, series)


# --- FastAPI helper ----------------------------------------------------------
# --------------------------------------------------------------------------
def call_openai(chat_history: list[dict]) -> dict:
    """
    Synchronous helper that re-uses ChatWorker’s OpenAI/JSON logic,
    so FastAPI can invoke it in a background thread.
    """
    import os, json
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        raw = client.chat.completions.create(
            model="gpt-4o-mini",
            store=True,
            messages=chat_history
        ).choices[0].message.content.strip()
    except Exception:
        raw = '{"description":"Sorry, I could not connect to ChatGPT.","title":"","series":[]}'

    try:
        parsed = json.loads(raw)
        return {
            "description": parsed.get("description", ""),
            "title": parsed.get("title", ""),
            "series": parsed.get("series", [])
        }
    except Exception:
        return {"description": raw, "title": "", "series": []}
