# backend/server.py — Women's Safety Device Backend Server
# AI inference fully offloaded to Z.AI API (no on-device ML required)
#
# Listens to MQTT topics from the Pico W, calls Z.AI for analysis,
# then pushes alerts to the mobile app via Firebase Cloud Messaging.
#
# Start: Z_AI_API_KEY=xxx python server.py

import json
import base64
import threading
import logging

from fastapi import FastAPI
import paho.mqtt.client as mqtt
import firebase_admin
from firebase_admin import credentials, messaging

from zai_client import (
    analyze_image,
    classify_audio_threat,
    assess_situation,
    generate_incident_report,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("safety-server")

app = FastAPI(title="Women's Safety Device Backend")

# Firebase — push notifications to mobile app
cred = credentials.Certificate("firebase_service_account.json")
firebase_admin.initialize_app(cred)

# In production replace with a real database
device_tokens: dict[str, str] = {}   # user_id → FCM token
alert_history: list[dict] = []       # rolling window of recent alerts
mqtt_client = mqtt.Client()


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.post("/register_token")
async def register_token(user_id: str, fcm_token: str):
    device_tokens[user_id] = fcm_token
    log.info(f"Registered FCM token for {user_id}")
    return {"status": "registered"}


# ── Push notification helper ──────────────────────────────────────────────────

def push(title: str, body: str) -> None:
    for uid, token in device_tokens.items():
        try:
            messaging.send(messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            ))
        except Exception as e:
            log.error(f"Push failed for {uid}: {e}")


# ── MQTT message handlers (each runs in its own thread) ──────────────────────

def handle_camera_frame(data: dict) -> None:
    """
    Offloads image threat detection to Z.AI glm-5v-turbo.
    Previously would have been Google Cloud Vision or local YOLOv8.
    """
    image_bytes = base64.b64decode(data["image"])
    try:
        result = analyze_image(image_bytes)
        log.info(f"[vision] {result}")
        if result.get("threat"):
            level = 4 if result.get("confidence") == "high" else 3
            alert = {
                "threat_level": level,
                "details": f"Threat detected: {result['type']} — {result.get('objects', [])}",
                "source": "vision",
            }
            _record_and_alert(alert)
    except Exception as e:
        log.error(f"[vision] error: {e}")


def handle_audio_clip(data: dict) -> None:
    """
    Offloads audio keyword classification to Z.AI glm-5.
    Previously would have been OpenAI Whisper + manual keyword matching.

    Device sends: {"transcript": "text from audio"} or {"audio_b64": "..."}
    If transcript is not available, the device should run a lightweight
    speech-to-text locally and send the resulting text here.
    """
    transcript = data.get("transcript", "")
    if not transcript:
        log.warning("[audio] no transcript in payload — skipping")
        return
    try:
        result = classify_audio_threat(transcript)
        log.info(f"[audio] {result}")
        if result.get("threat"):
            severity_to_level = {"high": 3, "medium": 2, "low": 1}
            level = severity_to_level.get(result.get("severity", "low"), 2)
            alert = {
                "threat_level": level,
                "details": f"Audio distress: keywords={result.get('keywords', [])}",
                "source": "audio",
            }
            _record_and_alert(alert)
    except Exception as e:
        log.error(f"[audio] error: {e}")


def handle_alert(data: dict) -> None:
    """
    Context-aware situation assessment using Z.AI glm-5.
    Replaces simple threshold logic — smarter multi-signal reasoning done in cloud,
    not on the resource-constrained Pico W.
    """
    _record_alert(data)
    level = data.get("threat_level", 0)
    if level < 2:
        return

    sensor_data = data.get("sensor_data", {})
    try:
        assessment = assess_situation(alert_history[-5:], sensor_data)
        log.info(f"[assess] {assessment}")

        assessed_level = assessment.get("threat_level", level)
        if assessed_level >= 3:
            report = generate_incident_report({
                "alert": data,
                "assessment": assessment,
                "recent_history": alert_history[-3:],
            })
            log.info(f"[report]\n{report}")
            push(
                "SAFETY ALERT",
                f"Level {assessed_level}: {assessment.get('summary', data.get('details', ''))}"
            )
    except Exception as e:
        log.error(f"[assess] error: {e}")
        # Fallback — still notify on high raw level
        if level >= 3:
            push("SAFETY ALERT", f"Threat level {level}: {data.get('details', '')}")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _record_alert(alert: dict) -> None:
    alert_history.append(alert)
    if len(alert_history) > 20:
        alert_history.pop(0)


def _record_and_alert(alert: dict) -> None:
    _record_alert(alert)
    mqtt_client.publish("safety/alert", json.dumps(alert))
    push("SAFETY ALERT", alert["details"])


# ── MQTT setup ────────────────────────────────────────────────────────────────

_TOPIC_HANDLERS = {
    "safety/camera_frame": handle_camera_frame,
    "safety/audio_clip":   handle_audio_clip,
    "safety/alert":        handle_alert,
}


def on_message(client, userdata, msg) -> None:
    try:
        data = json.loads(msg.payload)
    except Exception:
        return
    handler = _TOPIC_HANDLERS.get(msg.topic)
    if handler:
        threading.Thread(target=handler, args=(data,), daemon=True).start()


def mqtt_listener() -> None:
    mqtt_client.on_message = on_message
    mqtt_client.connect("broker.hivemq.com", 1883)
    mqtt_client.subscribe([(t, 0) for t in _TOPIC_HANDLERS])
    log.info("MQTT listener connected — waiting for device messages")
    mqtt_client.loop_forever()


threading.Thread(target=mqtt_listener, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
