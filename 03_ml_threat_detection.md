# ML & Threat Detection Plan

---

## Strategy: Edge + Cloud Hybrid

```
Pico W (Edge)                    Backend Server (cloud_server / server.py)
─────────────────                ────────────────────────────────────────
MPU6050 → fall detection    →    Camera frames → Z.AI glm-5v-turbo (vision)
INMP441 → RMS amplitude     →    Audio transcript → Z.AI glm-5 (classification)
Button  → manual SOS        →    Alert history → Z.AI glm-5 (situation assessment)
                                 Incident data → Z.AI glm-5 (report generation)
```

**Keep on device (latency-critical):** fall threshold, audio RMS, manual SOS, heartbeat.  
**Offload to Z.AI API (non-critical):** image threat detection, audio keyword classification,
multi-signal context assessment, incident report generation.

The Pico W is NOT powerful enough to run ML models directly.
All AI inference runs on the backend server via Z.AI API calls.

---

## Option A — Z.AI API (Recommended)

### Services Used
- **Z.AI glm-5v-turbo** — vision model for weapon / threat detection in camera frames
- **Z.AI glm-5** — text model for audio transcript classification, situation assessment, reports
- **Firebase** — real-time push alerts to mobile app

### Setup
```bash
cd backend
pip install -r requirements.txt
export Z_AI_API_KEY="your_key_here"
python server.py
```

### Image Threat Detection (replaces Google Vision / YOLOv8)
```python
# backend/zai_client.py — see full file for all functions

import requests, base64, json, os

Z_AI_API_KEY = os.getenv("Z_AI_API_KEY")
Z_AI_URL = "https://api.z.ai/api/paas/v4/chat/completions"

def analyze_image(image_bytes: bytes) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    resp = requests.post(
        Z_AI_URL,
        headers={"Authorization": f"Bearer {Z_AI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-5v-turbo",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": (
                        "Analyze this image for personal safety threats. "
                        "Look for weapons (knife, gun, bat, scissors), aggressive body language, "
                        "or dangerous situations. "
                        'Reply ONLY with valid JSON: '
                        '{"threat": true/false, "type": "weapon/aggression/none", '
                        '"objects": ["list"], "confidence": "low/medium/high"}'
                    )}
                ]
            }],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=15,
    )
    return json.loads(resp.json()["choices"][0]["message"]["content"])
```

### MQTT + Z.AI Threat Detection Server
```python
# backend/server.py (excerpt) — see full file

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    if msg.topic == "safety/camera_frame":
        image_bytes = base64.b64decode(data["image"])
        result = analyze_image(image_bytes)          # Z.AI vision call
        if result["threat"]:
            level = 4 if result["confidence"] == "high" else 3
            client.publish("safety/alert", json.dumps({
                "threat_level": level,
                "details": f"Threat: {result['type']} — {result['objects']}"
            }))
```

---

## Option B — Local ML on Laptop (Free / Offline Fallback)

### Model: YOLOv8 (object detection)
Fast, free, runs on CPU. Use only when Z.AI API is unavailable.

```bash
pip install ultralytics opencv-python
```

```python
# local_ml_server.py — offline fallback only

from ultralytics import YOLO
import cv2, paho.mqtt.client as mqtt, base64, json, numpy as np

model = YOLO("yolov8n.pt")  # nano model — fast
THREAT_CLASSES = ["knife", "scissors", "baseball bat", "gun"]

def analyze_frame(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    results = model(frame)
    detected = [model.names[int(b.cls)] for r in results for b in r.boxes]
    threats = [d for d in detected if d in THREAT_CLASSES]
    return threats

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    if "image" in data:
        image_bytes = base64.b64decode(data["image"])
        threats = analyze_frame(image_bytes)
        if threats:
            client.publish("safety/alert", json.dumps({
                "threat_level": 3,
                "details": f"Threat detected: {threats}"
            }))

client = mqtt.Client()
client.connect("broker.hivemq.com", 1883)
client.subscribe("safety/camera_frame")
client.on_message = on_message
print("Offline ML Server running...")
client.loop_forever()
```

---

## Audio Threat Detection

### On-Device (Pico W — keep, latency-critical)
RMS amplitude thresholding in `sensors.py` — triggers if loudness > threshold.
This fires immediately without any network round-trip.

### Cloud Classification via Z.AI glm-5 (replaces OpenAI Whisper)
After on-device RMS triggers, the device sends an audio clip to the backend.
The backend transcribes it (e.g. faster-whisper locally, free) then classifies
the transcript via Z.AI:

```python
# backend/zai_client.py

def classify_audio_threat(transcript: str) -> dict:
    resp = requests.post(
        Z_AI_URL,
        headers={"Authorization": f"Bearer {Z_AI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "glm-5",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a personal safety assistant. Analyze audio transcripts for "
                        "distress signals. Recognise English and Hindi/Urdu distress words "
                        "(bachao, chodo, ruko, madat karo)."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f'Audio transcript: "{transcript}"\n\n'
                        "Does this indicate a personal safety emergency? "
                        'Reply ONLY with valid JSON: '
                        '{"threat": true/false, "keywords": ["matched"], "severity": "none/low/medium/high"}'
                    )
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=10,
    )
    return json.loads(resp.json()["choices"][0]["message"]["content"])
```

---

## Threat Classification Table

| Signal | Detection Method | Where | Action |
|---|---|---|---|
| Fall/Impact | MPU6050 accel spike >2.5g | **On device** | Level 3 alert |
| Loud sound | INMP441 RMS >2000 | **On device** | Level 2 alert → send clip |
| Scream keyword | Z.AI glm-5 transcript analysis | **Backend (Z.AI)** | Level 3 alert |
| Weapon visible | Z.AI glm-5v-turbo vision | **Backend (Z.AI)** | Level 4 alert |
| Situation pattern | Z.AI glm-5 context assessment | **Backend (Z.AI)** | Escalate if needed |
| Manual press | GPIO button | **On device** | Level 4 SOS |
| No motion (60s) | MPU6050 idle | **On device** | Check-in prompt |
