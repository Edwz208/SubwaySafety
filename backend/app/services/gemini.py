from google import genai
from core import config
from typing import Any, Optional
from pathlib import Path

client = genai.Client(api_key=config.settings.GEMINI_API_KEY)

def generate_gemini_response() -> Optional[str]:
    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
    )
    return response.text

def analyze_video(video_url: str) -> Any:
    BASE_DIR = Path(__file__).resolve().parent.parent
    myfile = client.files.upload(file=str(BASE_DIR / video_url))
    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=[myfile, "Summarize this video. Then create a quiz with an answer key based on the information in this video."]
    )

    print(response.text)
