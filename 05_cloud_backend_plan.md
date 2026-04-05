# Cloud & Backend Plan

---

## Architecture

```
┌─────────────┐    MQTT     ┌──────────────────┐    REST    ┌─────────────────┐
│  Pico W     │ ──────────► │  HiveMQ Broker   │ ─────────► │  Backend Server │
│  (Device)   │             │  (Cloud MQTT)    │            │  (Python)       │
└─────────────┘             └──────────────────┘            └────────┬────────┘
                                     │                               │
                                     │ subscribe                     │ Z.AI API calls
                                     ▼                               ▼
                            ┌─────────────────┐        ┌────────────────────────┐
                            │  Mobile App     │        │  Z.AI API              │
                            │  (Flutter)      │        │  glm-5v-turbo (vision) │
                            └─────────────────┘        │  glm-5 (text/analysis) │
                                     ▲                  └────────────────────────┘
                                     │ FCM push
                              ┌──────┴──────┐
                              │  Firebase   │
                              └─────────────┘
```

**AI inference is fully offloaded to Z.AI** — no Google Cloud Vision, no OpenAI, no on-device ML.

---

## MQTT Topics

| Topic | Direction | Description |
|---|---|---|
| `safety/alert` | Device → Backend | Threshold-based alert (fall, RMS, button) |
| `safety/status` | Device → Backend | Heartbeat / battery level |
| `safety/camera_frame` | Device → Backend | JPEG image (base64) → Z.AI vision |
| `safety/audio_clip` | Device → Backend | Audio transcript → Z.AI classification |
| `safety/command` | App → Device | Remote commands (siren, photo) |
| `safety/network` | Device ↔ Device | Mesh/ad hoc alerts |

---

## Backend Server (Python + FastAPI + Z.AI)

### Install dependencies
```bash
cd backend
pip install -r requirements.txt
# requirements.txt: fastapi uvicorn paho-mqtt firebase-admin requests
```

### Environment
```bash
export Z_AI_API_KEY="your_z_ai_api_key"
```

### backend/server.py
```python
# Full file at backend/server.py — key excerpt below

import json, base64, threading, logging
from fastapi import FastAPI
import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, messaging
from zai_client import analyze_image, classify_audio_threat, assess_situation, generate_incident_report

app = FastAPI()
cred = credentials.Certificate("firebase_service_account.json")
firebase_admin.initialize_app(cred)

device_tokens = {}   # user_id → FCM token
alert_history = []   # rolling window for context assessment

def handle_camera_frame(data):
    """Offloads image threat detection to Z.AI glm-5v-turbo."""
    result = analyze_image(base64.b64decode(data["image"]))
    if result["threat"]:
        level = 4 if result["confidence"] == "high" else 3
        alert = {"threat_level": level, "details": f"Threat: {result['type']} — {result['objects']}"}
        mqtt_client.publish("safety/alert", json.dumps(alert))
        push("SAFETY ALERT", alert["details"])

def handle_audio_clip(data):
    """Offloads audio keyword classification to Z.AI glm-5."""
    result = classify_audio_threat(data.get("transcript", ""))
    if result["threat"]:
        level = {"high": 3, "medium": 2, "low": 1}.get(result["severity"], 2)
        push("AUDIO ALERT", f"Distress keywords: {result['keywords']}")

def handle_alert(data):
    """Context-aware assessment via Z.AI glm-5 — smarter than simple threshold logic."""
    alert_history.append(data)
    if data.get("threat_level", 0) >= 2:
        assessment = assess_situation(alert_history[-5:], data.get("sensor_data", {}))
        if assessment["threat_level"] >= 3:
            report = generate_incident_report({"alert": data, "assessment": assessment})
            push("SAFETY ALERT", f"Level {assessment['threat_level']}: {assessment['summary']}")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    handlers = {
        "safety/camera_frame": handle_camera_frame,
        "safety/audio_clip":   handle_audio_clip,
        "safety/alert":        handle_alert,
    }
    if handler := handlers.get(msg.topic):
        threading.Thread(target=handler, args=(data,), daemon=True).start()

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect("broker.hivemq.com", 1883)
mqtt_client.subscribe([("safety/alert", 0), ("safety/camera_frame", 0), ("safety/audio_clip", 0)])

threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Ad Hoc / Mesh Networking

On the Pico W, use WiFi in Access Point mode to create a local mesh:

```python
# mesh.py — Pico W acts as both AP and STA simultaneously

import network, socket, json

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="SAFETY_MESH", password="safety123", authmode=3)

def broadcast_alert(threat_level, details):
    """Broadcast to all devices on mesh network"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    payload = json.dumps({"level": threat_level, "details": details}).encode()
    sock.sendto(payload, ("192.168.4.255", 5005))
    sock.close()

def listen_for_mesh_alerts(callback):
    """Listen for alerts from nearby devices"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5005))
    while True:
        data, addr = sock.recvfrom(1024)
        alert = json.loads(data.decode())
        callback(alert, addr)
```

---

## Data Storage

### Local SQLite (development / offline)
```python
import sqlite3

conn = sqlite3.connect("incidents.db")
conn.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        threat_level INTEGER,
        details TEXT,
        latitude REAL,
        longitude REAL,
        photo_path TEXT
    )
""")
conn.commit()

def log_incident(threat_level, details, lat=None, lon=None, photo=None):
    from datetime import datetime
    conn.execute(
        "INSERT INTO incidents VALUES (NULL, ?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), threat_level, details, lat, lon, photo)
    )
    conn.commit()
```

### Cloud Storage (production — for incident photos/audio)
Any S3-compatible storage (AWS S3, Cloudflare R2, etc.) works here.
This is separate from the AI inference stack and can be chosen independently.
