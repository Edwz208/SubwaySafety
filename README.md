# WatchLine

AI-powered subway safety detection system that monitors live camera feeds, detects dangerous situations in real time, and instantly alerts station staff with video evidence and an AI-generated dispatch message.

---

## What it does

- Connects to phone cameras over Wi-Fi using the IP Webcam app
- Runs YOLOv8-Pose to detect and track people in the frame
- Classifies safety events: fallen person, aggression, erratic movement, crouching, lying down
- Saves a video clip of every critical incident automatically
- Generates a plain-English dispatch message using Google Gemini
- Pushes instant alerts to all connected staff dashboards via WebSocket
- Streams the live annotated camera feed to the React frontend

---

## Tech stack

| Layer | Technology |
|---|---|
| AI detection | YOLOv8-Pose (Ultralytics) |
| AI summaries | Google Gemini 2.0 Flash |
| Backend | FastAPI + Uvicorn |
| Real-time alerts | WebSocket |
| Frontend | React + Vite + Zustand |
| Database | Supabase (PostgreSQL) |
| Camera | IP Webcam (Android) |
| Networking | Tailscale VPN |
| Cloud | Vultr (Ubuntu 22.04) |

---

## Getting started

**1. Install dependencies**

```bash
pip install fastapi uvicorn ultralytics opencv-python-headless
pip install numpy pillow python-multipart pydantic-settings
pip install python-dotenv websockets google-genai
```

**2. Set up your .env file**

Create `backend/.env` with the following:

```
DATABASE_URL=postgresql://your_supabase_connection_string
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=any_long_random_string
REFRESH_KEY=another_long_random_string
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com).

**3. Start the backend**

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**4. Start the frontend**

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

**5. Run detection**

```bash
# Laptop webcam
cd backend
python test_visual.py

# Phone camera (update the IP in test_phone.py first)
python test_phone.py
```

---

## Phone camera setup

1. Install **IP Webcam** on Android and tap Start Server
2. Make sure your phone and laptop are on the same Wi-Fi network
3. Note the IP address shown on screen (e.g. `192.168.1.45:8080`)
4. Update the `source` URL in `test_phone.py` with that IP
5. For cross-network access, install Tailscale on both devices and use the `100.x.x.x` IP instead

---

## Detected events

| Event | Severity | Description |
|---|---|---|
| FALLEN | Critical | Person lying flat with head near ground |
| AGGRESSION | Critical | Fast wrist movement + extended elbow angle |
| LYING_DOWN | High | Person horizontal based on pose keypoints |
| CROUCHING | High | Head dropped toward hip level |
| ERRATIC | Medium | Chaotic or unpredictable movement pattern |

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/stream/add` | Register a camera |
| GET | `/feed/{camera_id}` | Live MJPEG stream |
| GET | `/clips/` | List all saved clips |
| GET | `/clips/{filename}` | Stream a clip file |
| DELETE | `/clips/{filename}` | Delete a clip |
| WS | `/alert` | WebSocket alert stream |
| GET | `/test_alert` | Send a test alert |

---

## Configuration

All detection thresholds are in `classifiers.py` inside the `CFG` dictionary. Key ones to tune:

| Setting | Default | What it controls |
|---|---|---|
| `LYING_ASPECT_RATIO` | 1.6 | How horizontal a body must be to count as lying down |
| `ERRATIC_CV_THRESHOLD` | 0.65 | How chaotic movement must be to trigger ERRATIC |
| `PUNCH_WRIST_SPEED_NORM` | 0.8 | Wrist speed threshold for AGGRESSION |
| `MIN_BBOX_HEIGHT_PX` | 80 | Minimum person size in pixels to process |
| `ALERT_COOLDOWN_SECONDS` | 20 | Seconds between repeated alerts per person |
| `GEMINI_COOLDOWN` | 60 | Seconds between Gemini API calls |

---

## Notes

- Clips are saved as `.avi` using the XVID codec — mp4v fails silently on Windows
- Gemini free tier has daily limits — the 60 second cooldown prevents quota exhaustion during demos
- Track IDs reset when a person leaves and re-enters the frame
- Regenerate your Gemini API key and Supabase password after any public demo
