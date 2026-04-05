# main.py — Women's Safety Device Main Loop
# Flash this to Raspberry Pi Pico W

import time
from machine import Pin
from sensors import MPU6050, Microphone
from alert import AlertSystem
from gsm import GSM
from mqtt_client import MQTTAlert
from config import SOS_PHONE_NUMBER, SENSOR_POLL_MS, FALL_ACCEL_THRESHOLD, HEARTBEAT_INTERVAL_S

# --- Initialize Modules ---
imu = MPU6050()
mic = Microphone()
alert = AlertSystem()
mqtt = MQTTAlert()
gsm = GSM()

sos_btn = Pin(15, Pin.IN, Pin.PULL_UP)

# --- State ---
sos_triggered = False
last_heartbeat = 0
heartbeat_count = 0


def trigger_sos(reason="Manual SOS"):
    global sos_triggered
    if sos_triggered:
        return
    sos_triggered = True

    print(f"[SOS] {reason}")
    alert.sos_alarm()
    mqtt.publish_alert(4, reason)
    gsm.send_sos(SOS_PHONE_NUMBER)

    time.sleep(30)  # Cooldown to avoid repeated alerts
    sos_triggered = False


# --- Startup ---
print("Safety Device v1.0 — Active")
alert.safe()

# --- Main Loop ---
while True:
    now = time.time()

    # 1. Manual SOS button (active low)
    if sos_btn.value() == 0:
        trigger_sos("Manual SOS button pressed")

    # 2. Fall / impact detection
    if imu.detect_fall(FALL_ACCEL_THRESHOLD):
        print("[WARN] Fall/impact detected")
        alert.danger()
        mqtt.publish_alert(3, "Fall or impact detected")
        time.sleep(2)
        if imu.detect_fall():  # Still abnormal = real fall
            trigger_sos("Fall detected — no recovery")

    # 3. Scream / loud noise detection
    if mic.detect_scream():
        print("[WARN] Loud sound detected")
        alert.aware()
        mqtt.publish_alert(2, "Loud sound / possible scream")

    # 4. Heartbeat
    if now - last_heartbeat > HEARTBEAT_INTERVAL_S:
        heartbeat_count += 1
        mqtt.publish_status(f"ok-{heartbeat_count}")
        last_heartbeat = now

    time.sleep_ms(SENSOR_POLL_MS)
