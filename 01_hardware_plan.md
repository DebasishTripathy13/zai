# Hardware Plan — Women's Safety Device

---

## 1. Core Microcontroller

### Raspberry Pi Pico W ✅ (You already have this)
- Dual-core ARM Cortex-M0+ @ 133 MHz
- 264 KB SRAM, 2 MB Flash
- Built-in WiFi 802.11 b/g/n
- Built-in Bluetooth 5.2
- MicroPython support
- Cost: ~₹600–800

---

## 2. Bill of Materials (BOM)

| # | Component | Purpose | Interface | Cost (INR) |
|---|---|---|---|---|
| 1 | Raspberry Pi Pico W | Main processor | — | ₹600 |
| 2 | OV2640 Camera Module | Visual capture | SPI | ₹400 |
| 3 | INMP441 MEMS Microphone | Audio monitoring | I2S | ₹300 |
| 4 | MPU6050 IMU | Motion/fall detect | I2C | ₹150 |
| 5 | SIM800L GSM Module | Emergency SMS/call | UART | ₹600 |
| 6 | PAM8302 Audio Amplifier | Speaker output | I2S | ₹150 |
| 7 | Small Speaker (8Ω, 1W) | Audio alerts | — | ₹80 |
| 8 | LiPo Battery 1500mAh 3.7V | Power supply | — | ₹400 |
| 9 | TP4056 Charger Module | Battery charging | — | ₹80 |
| 10 | MT3608 Boost Converter | 3.7V → 5V | — | ₹60 |
| 11 | Tactile Push Button | Manual SOS | GPIO | ₹20 |
| 12 | RGB LED | Status indicator | GPIO | ₹20 |
| 13 | Vibration Motor | Haptic alerts | GPIO | ₹60 |
| 14 | 10kΩ Resistors (×5) | Pull-ups | — | ₹20 |
| 15 | Flexible PCB / Perfboard | Assembly | — | ₹200 |
| **Total** | | | | **~₹3,140** |

---

## 3. Pin Wiring Diagram

```
Raspberry Pi Pico W GPIO Layout
================================

[Camera OV2640 - SPI]
  GP2  → CAM_SCK
  GP3  → CAM_MOSI
  GP4  → CAM_MISO
  GP5  → CAM_CS
  GP6  → CAM_RESET
  3.3V → VCC
  GND  → GND

[Microphone INMP441 - I2S]
  GP10 → I2S_SCK (BCLK)
  GP11 → I2S_WS  (LRCLK)
  GP12 → I2S_SD  (Data)
  3.3V → VDD
  GND  → GND
  GND  → L/R (for left channel)

[MPU6050 IMU - I2C]
  GP8  → SDA
  GP9  → SCL
  3.3V → VCC
  GND  → GND

[SIM800L GSM - UART]
  GP0  → TX (→ SIM800L RX)
  GP1  → RX (← SIM800L TX)
  5V   → VCC (needs 4V–4.4V, use boost converter)
  GND  → GND

[PAM8302 Speaker - I2S]
  GP13 → SD  (shutdown, active HIGH)
  GP14 → A+  (audio signal)
  GND  → A-
  5V   → VIN

[Controls & Indicators]
  GP15 → SOS Button (with 10kΩ pullup to 3.3V)
  GP16 → Vibration Motor (via NPN transistor)
  GP17 → RGB LED Red
  GP18 → RGB LED Green
  GP19 → RGB LED Blue

[Power]
  LiPo → TP4056 → MT3608 (5V out) → VSYS pin
  USB-C micro charging port
```

---

## 4. Power Budget

| Component | Current Draw |
|---|---|
| Pico W (active WiFi) | 150 mA |
| OV2640 Camera | 60 mA |
| INMP441 Mic | 1.4 mA |
| MPU6050 | 3.9 mA |
| SIM800L (idle) | 2 mA |
| SIM800L (TX burst) | 2000 mA peak |
| Vibration motor | 100 mA |
| Speaker (avg) | 200 mA |
| **Total (avg)** | **~520 mA** |

**Battery life:** 1500 mAh / 520 mA ≈ **~2.9 hours active**
→ Use sleep modes to extend to **8–10 hours**

---

## 5. Enclosure Design

```
[Top View — Neck Accessory]
┌─────────────────────────────────────────┐
│  [Camera]  [LED]              [Camera]  │  ← back of neck (173° view)
│                                         │
│  [Mic]  [Pico W + Battery]  [Speaker]  │
│                                         │
│         [SIM800L] [MPU6050]            │
└─────────────────────────────────────────┘
Width: ~12 cm  Height: ~2.5 cm  Depth: ~1.2 cm
Material: Flexible polymer + fabric exterior
```

---

## 6. Phase 1 Prototype (Breadboard)

Start with just these components for proof of concept:
1. Pico W
2. MPU6050 (I2C — easiest to start)
3. Push button (SOS)
4. LED (status)
5. WiFi MQTT alert to phone

Get this working first before adding camera + GSM.
