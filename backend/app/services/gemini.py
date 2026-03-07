from google import genai
from core import config
from typing import Any, Optional
from pathlib import Path
import time

client = genai.Client(api_key=config.settings.GEMINI_API_KEY)

# ─────────────────────────────────────────────
# FUNCTION 1: analyze_incident
# Takes structured detection data and returns a
# short, plain-text emergency dispatch summary.
#
# This is called by events.py right after a new
# event is saved to the DB.
#
# It does NOT upload a video — it uses text only,
# which is much faster (instant vs 10-30s for video).
# Fast response = alert appears on dashboard quickly.
# ─────────────────────────────────────────────
def analyze_incident(
    event_type: str,
    severity: str,
    location: str,
    camera_id: str,
    details: dict = {},
) -> str:
    """
    Generates a 2-sentence emergency dispatch summary from detection metadata.
    Returns plain text string.
    """

    # Build a structured prompt from the detection data
    # The more specific the context, the better Gemini's response
    details_str = ""
    if details:
        # Convert details dict to readable lines
        # e.g. {"confidence": 0.87, "aspect_ratio": 2.1} → "confidence: 0.87\naspect_ratio: 2.1"
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
        model="gemini-2.0-flash",   # faster + cheaper than gemini-3-flash-preview
        contents=prompt,
    )

    return response.text.strip()


# ─────────────────────────────────────────────
# FUNCTION 2: analyze_video
# Uploads a full video to Gemini and gets a
# detailed safety analysis.
#
# Use this for the SIMULATION MODE demo —
# upload sample_collapse.mp4 and get a full report.
#
# NOT used for real-time alerts (too slow).
# ─────────────────────────────────────────────
def analyze_video(video_url: str) -> Any:
    """
    Uploads a video file from the /videos folder to Gemini
    and returns a safety analysis report.
    Used for simulation/demo mode only.
    """
    print(f"[gemini] Uploading video: {video_url}")

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    video_path = str(BASE_DIR / "videos" / video_url)

    # Upload the file to Gemini's file storage
    myfile = client.files.upload(file=video_path)

    # Wait for Gemini to process the video (can take 10-30 seconds)
    while not myfile.state or myfile.state.name != "ACTIVE":
        state_name = getattr(myfile.state, "name", str(myfile.state))
        print(f"[gemini] Video processing state: {state_name}")

        if state_name == "FAILED":
            raise RuntimeError(f"Video processing failed for {myfile.name}")

        time.sleep(5)
        myfile = client.files.get(name=myfile.name)

    print("[gemini] Video ready, generating safety analysis...")

    # Safety-focused prompt for video analysis
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            myfile,
            (
                "You are a transit safety AI. Analyze this subway station footage. "
                "Identify any safety concerns such as: people lying on the ground, "
                "aggressive behaviour, people in distress, or unusual movements. "
                "For each concern found, state: what you see, where in the video it occurs "
                "(timestamp if possible), and the recommended staff response. "
                "If no concerns are found, state that the footage appears normal."
            )
        ]
    )

    print(f"[gemini] Analysis complete")
    return response.text


# ─────────────────────────────────────────────
# FUNCTION 3: generate_gemini_response
# Simple test function — kept from original code.
# Hit GET /testing to verify Gemini API key works.
# ─────────────────────────────────────────────
def generate_gemini_response() -> Optional[str]:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Respond with exactly: SubGuard Gemini API connected successfully."
    )
    return response.text
