from google import genai
from core import config
from typing import Any, Optional
from pathlib import Path
import time

client = genai.Client(api_key=config.settings.GEMINI_API_KEY)


def analyze_incident(
    event_type: str,
    severity: str,
    location: str,
    camera_id: str,
    details: dict = {},
) -> str:
    details_str = ""
    if details:
        details_str = "\n".join(f"- {k}: {v}" for k, v in details.items())

    prompt = (
        "You are a transit safety AI generating emergency alerts for subway station staff. "
        "Write exactly 2 sentences. Be specific, calm, and actionable. "
        "Do not use bullet points or formatting.\n\n"
        f"Detection details:\n"
        f"- Event type: {event_type}\n"
        f"- Severity: {severity}\n"
        f"- Location: {location}\n"
        f"- Camera: {camera_id}\n"
        f"{details_str}\n\n"
        "Generate the dispatch alert now:"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return response.text.strip()


def analyze_video(video_path: str | Path) -> Any:
    """
    Uploads a real video file path to Gemini and returns a safety analysis report.
    """
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"[gemini] Uploading video: {video_path}")

    myfile = client.files.upload(file=str(video_path))

    while not myfile.state or myfile.state.name != "ACTIVE":
        state_name = getattr(myfile.state, "name", str(myfile.state))
        print(f"[gemini] Video processing state: {state_name}")

        if state_name == "FAILED":
            raise RuntimeError(f"Video processing failed for {myfile.name}")

        time.sleep(5)
        myfile = client.files.get(name=myfile.name)

    print("[gemini] Video ready, generating safety analysis...")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            myfile,
            (
                "You are a transit safety AI. Analyze this subway station footage. "
                "Identify any safety concerns such as people lying on the ground, "
                "aggressive behaviour, people in distress, or unusual movements. "
                "For each concern found, state what you see, where in the video it occurs "
                "(timestamp if possible), and the recommended staff response. "
                "If no concerns are found, state that the footage appears normal."
            )
        ]
    )

    print("[gemini] Analysis complete")
    return response.text


def generate_gemini_response() -> Optional[str]:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Respond with exactly: SubGuard Gemini API connected successfully."
    )
    return response.text