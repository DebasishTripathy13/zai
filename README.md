# Women's Safety Device — Smart Neck Accessory
## Project by Debasish Tripathy, MIT Manipal

---

## Project Overview

A fashionable IoT neck accessory that acts as a personal safety device.
It uses AI-powered threat detection, emergency alerts, and ad hoc mesh networking.

---

## Folder Structure

```
womens-safety-device/
├── README.md                  ← You are here
├── 01_hardware_plan.md        ← Components, wiring, BOM
├── 02_firmware_plan.md        ← Raspberry Pi Pico W MicroPython code plan
├── 03_ml_threat_detection.md  ← Machine learning & cloud AI plan
├── 04_mobile_app_plan.md      ← Companion mobile app plan
├── 05_cloud_backend_plan.md   ← MQTT broker, cloud storage, APIs
├── 06_phase_roadmap.md        ← Week-by-week build timeline
├── firmware/                  ← Pico W MicroPython source code
│   ├── main.py
│   ├── sensors.py
│   ├── camera.py
│   ├── alert.py
│   ├── gsm.py
│   └── mqtt_client.py
└── docs/
    └── wiring_diagram.md
```

---

## Quick Start

1. Read `01_hardware_plan.md` → buy components
2. Read `02_firmware_plan.md` → flash Pico W
3. Read `03_ml_threat_detection.md` → set up cloud AI
4. Read `06_phase_roadmap.md` → follow the timeline

---

## Core Features

| Feature | Status | File |
|---|---|---|
| Motion/fall detection (MPU6050) | Planned | firmware/sensors.py |
| Audio threat detection (INMP441) | Planned | firmware/sensors.py |
| Camera capture (OV2640) | Planned | firmware/camera.py |
| Emergency SOS SMS (SIM800L) | Planned | firmware/gsm.py |
| Cloud ML threat analysis | Planned | 03_ml_threat_detection.md |
| MQTT alert messaging | Planned | firmware/mqtt_client.py |
| Mobile app companion | Planned | 04_mobile_app_plan.md |
| Mesh networking | Planned | 05_cloud_backend_plan.md |
