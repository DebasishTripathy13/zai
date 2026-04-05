# mqtt_client.py — WiFi + MQTT messaging

import network
import time
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER, MQTT_PORT, DEVICE_ID
from config import MQTT_TOPIC_ALERT, MQTT_TOPIC_STATUS
import json


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
        print(" FAILED — offline mode")

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
