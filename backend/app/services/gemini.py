from google import genai
from core import config
from typing import Any, Optional
from pathlib import Path
import time

client = genai.Client(api_key=config.settings.GEMINI_API_KEY)

def generate_gemini_response() -> Optional[str]:
    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
    )
    return response.text

def analyze_video(video_url: str) -> Any:
    print("analyzing...")
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    myfile = client.files.upload(file=str(BASE_DIR / "videos" / video_url))

    while not myfile.state or myfile.state.name != "ACTIVE":
        state_name = getattr(myfile.state, "name", str(myfile.state))
        print("video processing state:", state_name)

        if state_name == "FAILED":
            raise RuntimeError(f"Video processing failed for file {myfile.name}")

        time.sleep(5)
        myfile = client.files.get(name=myfile.name)
    print("entering response")
    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=[myfile, "Summarize this video. Then create a quiz with an answer key based on the information in this video."]
    )
    print(response.text)
