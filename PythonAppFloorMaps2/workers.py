# workers.py

import json
from PySide6.QtCore import QThread, Signal
from openai import OpenAI
import os

class ChatWorker(QThread):
    """
    Worker thread that sends chat_history to OpenAI, parses JSON,
    and emits (description, title, series_list) once done.
    """
    result_ready = Signal(str, str, list)

    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable")

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
            parsed = json.loads(raw)
            desc = parsed.get("description", "")
            title = parsed.get("title", "")
            series = parsed.get("series", [])
        except Exception:
            desc = raw
            title = ""
            series = []

        self.result_ready.emit(desc, title, series)

# END OF workers.py
