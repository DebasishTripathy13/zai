# SafeGuard — AI-Powered Women's Safety Device

> An IoT safety wearable that combines edge sensor hardware with a GLM 5.1-powered agentic backend to detect threats, reason about context, and autonomously trigger the right response actions — in the right order.

**By Debasish Tripathy, MIT Manipal**  
Built for the **Z.ai Builder Series · Build with GLM 5.1** · April 2026

---

## The Problem

Personal safety devices today are dumb — they either always alert (false alarms) or never alert (too slow). A fall detector can't tell the difference between tripping on stairs and being shoved. A loud-noise trigger can't distinguish a scream from a crowd cheering.

**SafeGuard** puts a reasoning layer between raw sensor data and emergency alerts — using GLM 5.1 to understand *context*, not just *thresholds*.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PICO W  (Edge)                             │
│  MPU6050 ──► fall threshold  ──► MQTT safety/alert              │
│  INMP441 ──► RMS amplitude   ──► MQTT safety/audio_clip         │
│  Button  ──► manual SOS      ──► MQTT safety/alert              │
│  Camera  ──► raw JPEG        ──► MQTT safety/camera_frame       │
└────────────────────────┬────────────────────────────────────────┘
                         │  MQTT  (HiveMQ broker)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BACKEND SERVER  (Python)                        │
│                                                                  │
│  camera_frame  ──► zai_client.analyze_image()                   │
│                     glm-5v-turbo · weapon / threat detection     │
│                                                                  │
│  audio_clip    ──► zai_client.classify_audio_threat()           │
│                     glm-5 · multilingual distress analysis       │
│                                                                  │
│  alert         ──► safety_agent.run_agent()   ◄── CORE          │
│                     glm-5 function calling                       │
│                     ┌──────────────────────┐                     │
│                     │  trigger_alarm()      │                    │
│                     │  send_emergency_sms() │                    │
│                     │  notify_contacts()    │                    │
│                     │  capture_photo()      │                    │
│                     │  log_incident()       │                    │
│                     └──────────────────────┘                    │
└────────────────────────┬────────────────────────────────────────┘
                         │  Firebase FCM
                         ▼
                ┌─────────────────┐
                │  Flutter App    │
                │  (Guardian)     │
                └─────────────────┘
```

**Edge** handles only what must be fast: raw threshold checks, zero network latency.  
**Backend** handles everything that benefits from reasoning: GLM 5.1 does the thinking.

---

## How GLM 5.1 Is Used

SafeGuard uses GLM 5.1 across three layers, each demonstrating a different capability:

### 1. Vision Threat Detection — `glm-5v-turbo`
Camera frames streamed over MQTT are sent to `glm-5v-turbo`. The model identifies weapons (knife, gun, bat), aggressive posture, and dangerous situations — returning structured JSON with threat type and confidence. This replaces what would otherwise require a separate ML server running YOLOv8 or Google Vision API.

### 2. Audio Distress Classification — `glm-5`
When on-device RMS amplitude exceeds threshold (loud sound), an audio transcript is sent to `glm-5`. The model classifies distress signals with genuine language understanding — catching multilingual phrases (Hindi/Urdu: *bachao*, *chodo*, *madat karo*) and context that keyword lists miss entirely.

### 3. Agentic Multi-Step Response — `glm-5` with function calling
This is the project's core contribution. Instead of hard-coded `if threat_level >= 3: send_sms()` rules, the `safety_agent` presents GLM 5.1 with the full threat situation and a set of callable tools. The model autonomously reasons about:
- **Which** tools are appropriate for this specific situation
- **What order** to call them (evidence capture → deterrence → notification → logging)
- **What parameters** to use (alarm duration, SMS message content, notification priority)

The agent runs a multi-turn loop — each tool result is fed back to the model, which continues planning until the situation is fully handled. A level-2 alert might only notify contacts; a level-4 triggers the alarm, SMS, push notification, photo capture, and incident log — all decided by the model, not by code.

**Why GLM 5.1:** Reliable structured JSON output, strong multilingual understanding, vision + text from one API, and function calling that actually works for sequential multi-tool workflows.

---

## Project Structure

```
├── firmware/               # MicroPython for Raspberry Pi Pico W
│   ├── main.py             # Main sensor loop
│   ├── sensors.py          # MPU6050 IMU + INMP441 microphone
│   ├── alert.py            # LED, vibration, buzzer
│   ├── gsm.py              # SIM800L SMS/call fallback
│   ├── mqtt_client.py      # WiFi + MQTT
│   └── config.py           # WiFi, thresholds, phone numbers
│
├── backend/
│   ├── zai_client.py       # Z.AI API: vision, classification, assessment, reports
│   ├── safety_agent.py     # GLM 5.1 agentic loop with function calling
│   ├── server.py           # FastAPI + MQTT listener + Firebase
│   └── requirements.txt
│
└── docs/  01-06_*.md       # Hardware, firmware, ML, app, cloud, roadmap plans
```

---

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi Pico W | Edge MCU with WiFi |
| MPU6050 | Accelerometer — fall / impact detection |
| INMP441 | MEMS mic — audio amplitude |
| SIM800L | GSM — SMS/call when WiFi unavailable |
| OV2640 | Camera — frames for vision analysis |
| Buzzer + LED strip | On-device alarm |
| Push button | Manual SOS |

---

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
export Z_AI_API_KEY="your_z_ai_key"
cp /path/to/firebase_service_account.json .
python server.py
```

### Firmware (Pico W)
Edit `firmware/config.py` with your WiFi credentials and emergency contact number, then flash all files using [Thonny](https://thonny.org/) or `mpremote`.

---

## The Agent in Action

```python
from backend.safety_agent import run_agent

situation = {
    "threat_level": 3,
    "source": "vision",
    "details": "Knife detected — high confidence",
    "sensor_data": {"accel_magnitude": 2.8, "audio_rms": 3100},
    "location": {"lat": 28.6139, "lon": 77.2090},
}

actions = run_agent(situation)

# GLM 5.1 autonomously calls (in order):
# 1. capture_photo(reason="weapon detected in frame")
# 2. trigger_alarm(duration_seconds=15)
# 3. notify_contacts(title="DANGER", body="Knife nearby", priority="critical")
# 4. send_emergency_sms(message="ALERT: Weapon detected. Loc: 28.61, 77.20", include_location=True)
# 5. log_incident(threat_level=3, description="...", actions_taken=[...])
```

GLM 5.1 sequences the actions logically — evidence first, then deterrence, then notification, then logging. No hardcoded rules.

---

## Threat Response Table

| Trigger | Where detected | GLM 5.1 role |
|---|---|---|
| Fall / impact >2.5g | On device (edge) | Context assessment |
| Loud sound RMS >2000 | On device (edge) | Audio transcript classification |
| Scream / distress words | Backend — `glm-5` | Classify severity, suggest actions |
| Weapon in frame | Backend — `glm-5v-turbo` | Identify, confidence score |
| Multi-signal pattern | Backend — `glm-5` | Holistic situation assessment |
| Agent response plan | Backend — `glm-5` + tools | Autonomous multi-step execution |

---

## Built With

- [Z.AI GLM 5.1](https://z.ai) — vision analysis, distress classification, agentic function calling
- MicroPython — Raspberry Pi Pico W firmware  
- FastAPI + paho-mqtt — backend server  
- Firebase Cloud Messaging — mobile push  
- Flutter — guardian companion app (planned)
