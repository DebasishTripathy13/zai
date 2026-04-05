# Wiring Diagram — Raspberry Pi Pico W

```
                    ┌──────────────────────────────┐
                    │      Raspberry Pi Pico W      │
                    │                               │
  MPU6050           │  GP8  ──────── SDA            │
  (IMU)             │  GP9  ──────── SCL            │
                    │  3.3V ──────── VCC            │
                    │  GND  ──────── GND            │
                    │                               │
  INMP441           │  GP10 ──────── BCLK (SCK)    │
  (Microphone)      │  GP11 ──────── LRCLK (WS)    │
                    │  GP12 ──────── DATA (SD)      │
                    │  3.3V ──────── VDD            │
                    │  GND  ──────── GND + L/R      │
                    │                               │
  OV2640            │  GP2  ──────── SCK            │
  (Camera)          │  GP3  ──────── MOSI           │
                    │  GP4  ──────── MISO           │
                    │  GP5  ──────── CS             │
                    │  GP6  ──────── RESET          │
                    │  3.3V ──────── VCC            │
                    │  GND  ──────── GND            │
                    │                               │
  SIM800L           │  GP0  ──────── RX (of SIM)   │
  (GSM Module)      │  GP1  ──────── TX (of SIM)   │
                    │  VSYS ──────── VCC (via boost)│
                    │  GND  ──────── GND            │
                    │                               │
  PAM8302           │  GP13 ──────── SD (shutdown)  │
  (Speaker Amp)     │  GP14 ──────── A+ (audio)     │
                    │  GND  ──────── A-             │
                    │  5V   ──────── VIN            │
                    │                               │
  Controls          │  GP15 ──────── SOS Button     │
                    │  GP16 ──────── Vibration Motor│
                    │  GP17 ──────── LED Red        │
                    │  GP18 ──────── LED Green      │
                    │  GP19 ──────── LED Blue       │
                    │                               │
  Power             │  VSYS ──────── MT3608 Out(5V) │
                    │  GND  ──────── Common GND     │
                    └──────────────────────────────┘

Power Chain:
  LiPo 3.7V → TP4056 (charger) → MT3608 (5V boost) → VSYS
  USB-C → TP4056 (charging input)

SOS Button:
  GP15 ── Button ── GND
  (GP15 has internal PULL_UP, so LOW = pressed)

Vibration Motor:
  GP16 ── 1kΩ ── NPN Base (2N2222)
  Collector ── Motor ── 5V
  Emitter ── GND
  Add 1N4001 diode across motor (flyback protection)

RGB LED (Common Cathode):
  GP17 ── 220Ω ── LED Red Anode
  GP18 ── 220Ω ── LED Green Anode
  GP19 ── 220Ω ── LED Blue Anode
  Common Cathode ── GND
```

## Notes
- SIM800L needs 4.0–4.4V, NOT 5V directly. Use MT3608 set to 4.2V.
- SIM800L peak current is 2A. Use a capacitor (1000µF) near its VCC pin.
- OV2640 communicates via SPI. Make sure SPI speed ≤ 4 MHz initially.
- Keep all GNDs connected together (common ground).
