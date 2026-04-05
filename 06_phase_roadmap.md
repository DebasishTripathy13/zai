# Phase Roadmap — Build Timeline

---

## Phase 1 — Proof of Concept (Week 1–2)
**Goal: Get basic SOS working on breadboard**

### Hardware needed NOW:
- Raspberry Pi Pico W ✅ (you have it)
- MPU6050 module (~₹150)
- Push button + LED (hobby kit)
- USB cable ✅

### Tasks:
- [ ] Flash MicroPython on Pico W
- [ ] Wire MPU6050 via I2C (SDA=GP8, SCL=GP9)
- [ ] Test fall/motion detection in Python REPL
- [ ] Connect Pico W to WiFi
- [ ] Send MQTT alert to HiveMQ broker
- [ ] Verify alert received on MQTT Explorer app (free desktop tool)

### Success Criteria:
Shake the Pico W → MQTT message appears on laptop ✅

---

## Phase 2 — Audio + Alerts (Week 3–4)
**Goal: Add microphone and haptic feedback**

### Additional Hardware:
- INMP441 microphone (~₹300)
- Vibration motor + NPN transistor (~₹80)
- Small buzzer (~₹30)

### Tasks:
- [ ] Wire INMP441 via I2S
- [ ] Test audio level reading
- [ ] Implement scream/loud-noise detection threshold
- [ ] Wire vibration motor via GPIO
- [ ] Implement alert levels (vibration patterns per threat level)
- [ ] Test full flow: loud sound → vibration + MQTT alert

---

## Phase 3 — Emergency SMS (Week 5–6)
**Goal: Real SOS SMS to a phone**

### Additional Hardware:
- SIM800L module (~₹600)
- SIM card with data plan (Airtel/Jio)
- MT3608 boost converter (~₹60)

### Tasks:
- [ ] Wire SIM800L via UART
- [ ] Test AT commands via serial
- [ ] Send test SMS to your number
- [ ] Integrate SOS SMS in main.py
- [ ] Test: button press → SMS received on phone ✅

---

## Phase 4 — Camera Integration (Week 7–8)
**Goal: Capture and transmit photos on threat**

### Additional Hardware:
- OV2640 Camera module (~₹400)

### Tasks:
- [ ] Wire OV2640 via SPI
- [ ] Capture JPEG frame
- [ ] Encode to base64
- [ ] Publish to MQTT topic `safety/camera_frame`
- [ ] Run local_ml_server.py on laptop
- [ ] Test: threat detected → photo captured → ML analyzed

---

## Phase 5 — Mobile App (Week 9–10)
**Goal: Flutter app receives live alerts**

### Tasks:
- [ ] Set up Flutter project
- [ ] Implement MQTT connection in app
- [ ] Build dashboard UI with threat level display
- [ ] Add SOS button in app
- [ ] Set up Firebase push notifications
- [ ] Test: device alert → app notification on phone ✅

---

## Phase 6 — Cloud ML (Week 11–12)
**Goal: AI-powered threat detection**

### Tasks:
- [ ] Set up Google Cloud project
- [ ] Enable Vision AI API
- [ ] Update cloud server to use Vision AI
- [ ] Add YOLOv8 local ML server as fallback
- [ ] Test with actual camera feed
- [ ] Tune threat detection thresholds

---

## Phase 7 — Integration & Testing (Week 13–14)
**Goal: Full system test**

### Tasks:
- [ ] Full end-to-end test (all sensors active)
- [ ] Battery life test (measure real consumption)
- [ ] False positive tuning (adjust thresholds)
- [ ] Edge case testing (no WiFi → offline mode)
- [ ] Documentation update

---

## Phase 8 — Enclosure & Wearable (Week 15–16)
**Goal: Wearable prototype**

### Tasks:
- [ ] Design enclosure in Fusion 360 / Tinkercad
- [ ] 3D print or fabricate housing
- [ ] Solder components to perfboard (compact)
- [ ] LiPo battery + TP4056 charging integration
- [ ] Mount in neck accessory form factor
- [ ] Final demo + video documentation

---

## Tools You'll Need

| Tool | Purpose | Cost |
|---|---|---|
| Thonny IDE | MicroPython editor for Pico W | Free |
| MQTT Explorer | Test MQTT messages | Free |
| VS Code | Python backend development | Free |
| Flutter SDK | Mobile app development | Free |
| Tinkercad | Circuit simulation | Free |
| Fritzing | Wiring diagrams | Free |
| Python 3.11+ | Backend server | Free |

---

## Start Right Now

```bash
# Step 1: Download MicroPython for Pico W
open https://micropython.org/download/RPI_PICO_W/

# Step 2: Copy to Pico W (it's already in bootloader mode!)
cp ~/Downloads/RPI_PICO_W-*.uf2 /Volumes/RPI-RP2/

# Step 3: Install Thonny
pip install thonny

# Step 4: Open Thonny → Run → Select Interpreter → MicroPython (Pico W)
thonny
```
