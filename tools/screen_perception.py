import os
import io
import time
import base64
from typing import Dict, Any, Optional
from PIL import Image, ImageGrab

class ScreenPerceptionEngine:
    """Captures and processes desktop screen content for the agent."""

    def __init__(self, save_dir: str = ".data/screenshots"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def capture_screen(self) -> Dict[str, Any]:
        """Takes a full desktop screenshot and saves a temporary image file."""
        try:
            timestamp = int(time.time())
            filename = f"screen_{timestamp}.png"
            filepath = os.path.join(self.save_dir, filename)

            # Capture desktop screen
            screenshot = ImageGrab.grab()
            screenshot.save(filepath, format="PNG")

            # Convert to base64 for vision LLM capabilities
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # Extract window/screen metrics
            width, height = screenshot.size

            return {
                "status": "success",
                "filepath": filepath,
                "width": width,
                "height": height,
                "image_b64": img_b64,
                "summary": f"Captured desktop screen screenshot ({width}x{height} pixels). File saved to: {filepath}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to capture screen: {str(e)}"
            }

    def get_screen_context_prompt(self) -> str:
        """Helper to format screen observation for the agent LLM prompt."""
        res = self.capture_screen()
        if res["status"] == "success":
            return (
                f"[SCREEN PERCEPTION ATTACHED]\n"
                f"Resolution: {res['width']}x{res['height']}\n"
                f"Screenshot Path: {res['filepath']}\n"
                f"Note to Agent: You have captured the user's active desktop screen. Analyze the user's query in context of what is visible."
            )
        return f"[SCREEN PERCEPTION ERROR]: {res.get('message', 'Could not capture screen')}"
