# Firmware Plan — Raspberry Pi Pico W (MicroPython)

---

## Architecture Overview

```
main.py
  ├── sensors.py      → MPU6050 (fall/motion), INMP441 (audio level)
  ├── camera.py       → OV2640 capture + JPEG encoding
  ├── alert.py        → Vibration, LED, speaker alerts
  ├── gsm.py          → SIM800L SMS + call
  ├── mqtt_client.py  → WiFi + MQTT publish/subscribe
  └── config.py       → WiFi credentials, phone numbers, thresholds
```

---

## Threat Level System

```
Level 0 — SAFE        → Green LED, normal monitoring
Level 1 — AWARE       → Yellow LED, subtle vibration
Level 2 — ALERT       → Red LED, strong vibration, audio beep
Level 3 — DANGER      → Red flash, alarm sound, SMS sent, photo captured
Level 4 — CRITICAL    → All of above + emergency call, MQTT broadcast
```

---

## File: config.py

```python
# config.py — Edit these before flashing

WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"

MQTT_BROKER = "broker.hivemq.com"   # Free public broker for testing
MQTT_PORT = 1883
MQTT_TOPIC_ALERT = "safety/alert"
MQTT_TOPIC_STATUS = "safety/status"
DEVICE_ID = "SAFETY_001"

# Emergency contacts
SOS_PHONE_NUMBER = "+91XXXXXXXXXX"   # Primary emergency contact
SOS_PHONE_NUMBER_2 = "+91XXXXXXXXXX" # Secondary contact

# Thresholds
FALL_ACCEL_THRESHOLD = 2.5      # g-force that triggers fall alert
AUDIO_THREAT_THRESHOLD = 2000   # Raw ADC value for loud sound
MOTION_SENSITIVITY = 0.8        # 0.0 (low) to 1.0 (high)

# Timing
SENSOR_POLL_MS = 100            # Poll sensors every 100ms
PHOTO_INTERVAL_S = 5            # Capture photo every 5s during alert
HEARTBEAT_INTERVAL_S = 30       # Send status ping every 30s
```

---

## File: sensors.py

```python
# sensors.py — MPU6050 IMU + INMP441 Microphone

from machine import I2C, Pin, I2S
import math, time

class MPU6050:
    MPU_ADDR = 0x68

    def __init__(self, sda_pin=8, scl_pin=9):
        self.i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        # Wake up MPU6050
        self.i2c.writeto_mem(self.MPU_ADDR, 0x6B, b'\x00')
        time.sleep(0.1)

    def read_accel(self):
        data = self.i2c.readfrom_mem(self.MPU_ADDR, 0x3B, 6)
        ax = (data[0] << 8 | data[1]) / 16384.0
        ay = (data[2] << 8 | data[3]) / 16384.0
        az = (data[4] << 8 | data[5]) / 16384.0
        return ax, ay, az

    def read_gyro(self):
        data = self.i2c.readfrom_mem(self.MPU_ADDR, 0x43, 6)
        gx = (data[0] << 8 | data[1]) / 131.0
        gy = (data[2] << 8 | data[3]) / 131.0
        gz = (data[4] << 8 | data[5]) / 131.0
        return gx, gy, gz

    def get_magnitude(self):
        ax, ay, az = self.read_accel()
        return math.sqrt(ax**2 + ay**2 + az**2)

    def detect_fall(self, threshold=2.5):
        """Returns True if sudden acceleration spike detected (fall/impact)"""
        mag = self.get_magnitude()
        return mag > threshold or mag < 0.3  # spike or free-fall


class Microphone:
    def __init__(self, sck_pin=10, ws_pin=11, sd_pin=12):
        self.audio_in = I2S(
            0,
            sck=Pin(sck_pin),
            ws=Pin(ws_pin),
            sd=Pin(sd_pin),
            mode=I2S.RX,
            bits=16,
            format=I2S.MONO,
            rate=8000,
            ibuf=4096
        )
        self.buf = bytearray(512)

    def get_audio_level(self):
        """Returns RMS audio level — higher = louder"""
        self.audio_in.readinto(self.buf)
        samples = [int.from_bytes(self.buf[i:i+2], 'little', True)
                   for i in range(0, len(self.buf), 2)]
        rms = math.sqrt(sum(s**2 for s in samples) / len(samples))
        return rms

    def detect_scream(self, threshold=2000):
        """Simple loud-sound / scream detection"""
        return self.get_audio_level() > threshold
```

---

## File: alert.py

```python
# alert.py — LED, vibration motor, buzzer alerts

from machine import Pin, PWM
import time

class AlertSystem:
    def __init__(self):
        self.led_r = Pin(17, Pin.OUT)
        self.led_g = Pin(18, Pin.OUT)
        self.led_b = Pin(19, Pin.OUT)
        self.vibration = Pin(16, Pin.OUT)
        self.buzzer = PWM(Pin(14))

    def set_led(self, r, g, b):
        self.led_r.value(r)
        self.led_g.value(g)
        self.led_b.value(b)

    def vibrate(self, duration_ms=500):
        self.vibration.on()
        time.sleep_ms(duration_ms)
        self.vibration.off()

    def beep(self, freq=1000, duration_ms=200):
        self.buzzer.freq(freq)
        self.buzzer.duty_u16(32768)
        time.sleep_ms(duration_ms)
        self.buzzer.duty_u16(0)

    def safe(self):
        self.set_led(0, 1, 0)   # Green

    def aware(self):
        self.set_led(1, 1, 0)   # Yellow
        self.vibrate(200)

    def danger(self):
        self.set_led(1, 0, 0)   # Red
        self.vibrate(1000)
        self.beep(2000, 500)

    def sos_alarm(self):
        """Continuous alarm for critical threat"""
        for _ in range(5):
            self.set_led(1, 0, 0)
            self.beep(3000, 300)
            self.vibrate(300)
            self.set_led(0, 0, 0)
            time.sleep_ms(100)
```

---

## File: gsm.py

```python
# gsm.py — SIM800L emergency SMS and call

from machine import UART, Pin
import time

class GSM:
    def __init__(self, tx_pin=0, rx_pin=1, baudrate=9600):
        self.uart = UART(0, baudrate=baudrate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        time.sleep(2)
        self._send_cmd("AT")          # Check module
        self._send_cmd("AT+CMGF=1")  # Set SMS text mode

    def _send_cmd(self, cmd, wait_ms=500):
        self.uart.write((cmd + "\r\n").encode())
        time.sleep_ms(wait_ms)
        return self.uart.read()

    def send_sms(self, number, message):
        self._send_cmd(f'AT+CMGS="{number}"', 500)
        self.uart.write((message + chr(26)).encode())  # Ctrl+Z to send
        time.sleep(3)

    def make_call(self, number):
        self._send_cmd(f"ATD{number};", 1000)
        time.sleep(10)      # Let it ring for 10 seconds
        self._send_cmd("ATH")  # Hang up

    def send_sos(self, number, lat=None, lon=None):
        if lat and lon:
            msg = (f"SOS! I need help!\n"
                   f"Location: https://maps.google.com/?q={lat},{lon}\n"
                   f"-- Safety Device Alert")
        else:
            msg = "SOS! I need help! Safety device triggered. Please call me immediately."
        self.send_sms(number, msg)
```

---

## File: mqtt_client.py

```python
# mqtt_client.py — WiFi connection + MQTT messaging

import network
import time
from umqtt.simple import MQTTClient
from config import *

class MQTTAlert:
    def __init__(self):
        self.client = None
        self._connect_wifi()
        self._connect_mqtt()

    def _connect_wifi(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        print("Connecting to WiFi", end="")
        for _ in range(20):
            if wlan.isconnected():
                print(" Connected:", wlan.ifconfig()[0])
                return
            print(".", end="")
            time.sleep(1)
        print(" FAILED — running offline mode")

    def _connect_mqtt(self):
        try:
            self.client = MQTTClient(DEVICE_ID, MQTT_BROKER, MQTT_PORT)
            self.client.connect()
            print("MQTT connected")
        except Exception as e:
            print("MQTT failed:", e)
            self.client = None

    def publish_alert(self, threat_level, details=""):
        if not self.client:
            return
        import json
        payload = json.dumps({
            "device": DEVICE_ID,
            "threat_level": threat_level,
            "details": details,
            "timestamp": time.time()
        })
        try:
            self.client.publish(MQTT_TOPIC_ALERT, payload)
        except Exception as e:
            print("MQTT publish error:", e)

    def publish_status(self, status="ok"):
        if not self.client:
            return
        try:
            self.client.publish(MQTT_TOPIC_STATUS, status)
        except Exception as e:
            print("MQTT status error:", e)
```

---

## File: main.py

```python
# main.py — Main loop

import time
from sensors import MPU6050, Microphone
from alert import AlertSystem
from gsm import GSM
from mqtt_client import MQTTAlert
from config import SOS_PHONE_NUMBER, SENSOR_POLL_MS, FALL_ACCEL_THRESHOLD

# Initialize all modules
imu = MPU6050()
mic = Microphone()
alert = AlertSystem()
mqtt = MQTTAlert()
gsm = GSM()

# SOS button
from machine import Pin
sos_btn = Pin(15, Pin.IN, Pin.PULL_UP)

sos_triggered = False

def trigger_sos(reason="Manual SOS"):
    global sos_triggered
    if sos_triggered:
        return
    sos_triggered = True

    print(f"SOS TRIGGERED: {reason}")
    alert.sos_alarm()
    mqtt.publish_alert(4, reason)
    gsm.send_sos(SOS_PHONE_NUMBER)

    # Reset after 30 seconds
    time.sleep(30)
    sos_triggered = False

print("Safety Device Active — Monitoring...")
alert.safe()

while True:
    # 1. Check manual SOS button
    if sos_btn.value() == 0:  # Button pressed (active low)
        trigger_sos("Manual SOS button pressed")

    # 2. Check fall / impact
    if imu.detect_fall(FALL_ACCEL_THRESHOLD):
        alert.danger()
        mqtt.publish_alert(3, "Fall or impact detected")
        time.sleep(2)
        if imu.detect_fall():  # Still abnormal after 2s = real fall
            trigger_sos("Fall detected")

    # 3. Check audio (scream detection)
    if mic.detect_scream():
        alert.aware()
        mqtt.publish_alert(2, "Loud sound / possible scream detected")

    # 4. Heartbeat status
    mqtt.publish_status("ok")

    time.sleep_ms(SENSOR_POLL_MS)
```

---

## Flashing Instructions

1. Download MicroPython UF2 for Pico W:
   https://micropython.org/download/RPI_PICO_W/

2. Hold BOOTSEL button → plug Pico W into USB

3. Drag UF2 file to `RPI-RP2` volume:
   ```bash
   cp ~/Downloads/RPI_PICO_W-*.uf2 /Volumes/RPI-RP2/
   ```

4. Install Thonny IDE (easiest for Pico W):
   ```bash
   pip install thonny
   ```

5. In Thonny: Select interpreter → MicroPython (Raspberry Pi Pico)

6. Upload all `.py` files to Pico W root

7. Edit `config.py` with your WiFi + phone number first!
