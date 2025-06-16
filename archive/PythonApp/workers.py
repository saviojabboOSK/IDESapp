# workers.py

import json
from PySide6.QtCore import QThread, Signal
from openai import OpenAI
import os

# ChatWorker class: Handles background tasks for sending chat history to OpenAI and processing the response.
class ChatWorker(QThread):
    """
    Worker thread that sends chat_history to OpenAI, parses JSON,
    and emits (description, title, series_list) once done.
    """
    # Signal emitted when processing is complete.
    result_ready = Signal(str, str, list)

    def __init__(self, chat_history, base_image_path="ADIClabpng.png"):
        super().__init__()
        self.chat_history = chat_history
        self.base_image_path = base_image_path
        # Retrieve OpenAI API key from environment variables.
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable")

    def run(self):
        try:
            # Check if the last user message requests floormap image generation.
            last_message = self.chat_history[-1]["content"].lower() if self.chat_history else ""
            if "generate floormap image" in last_message or "floormap with data points" in last_message:
                # Generate floormap image and emit the result.
                image_path = self.generate_floormap_image()
                desc = "Generated floormap image with data points."
                title = "Floormap with Data Points"
                series = {"floormap": image_path}
                self.result_ready.emit(desc, title, series)
                return

            # Send chat history to OpenAI and retrieve the response.
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=self.chat_history
            )
            raw = completion.choices[0].message.content.strip()
        except Exception:
            # Fallback response in case of an error.
            raw = '{"description": "Sorry, I could not connect to ChatGPT.", "title": "", "series": []}'

        try:
            # Parse the JSON response from OpenAI.
            parsed = json.loads(raw)
            desc = parsed.get("description", "")
            title = parsed.get("title", "")
            series = parsed.get("series", [])
        except Exception:
            # Handle parsing errors.
            desc = raw
            title = ""
            series = []

        # Emit the processed result.
        self.result_ready.emit(desc, title, series)

    def generate_floormap_image(self):
        import os
        import base64
        import io
        from PIL import Image, ImageDraw

        # Load base floormap image (use the instance's base_image_path)
        if not os.path.exists(self.base_image_path):
            return ""

        base_image = Image.open(self.base_image_path).convert("RGBA")

        # Example: overlay red circles as data points on the image
        draw = ImageDraw.Draw(base_image)
        data_points = [(50, 50), (150, 100), (200, 180)]  # example coordinates
        for point in data_points:
            x, y = point
            r = 10
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0, 128))

        # Save generated image to a unique file
        import uuid
        output_dir = "floormap_images"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"generated_floormap_{uuid.uuid4().hex}.png")
        base_image.save(output_path)

        return output_path

# END OF workers.py
