# alert.py — LED, vibration motor, buzzer

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
        self.set_led(0, 1, 0)

    def aware(self):
        self.set_led(1, 1, 0)
        self.vibrate(200)

    def danger(self):
        self.set_led(1, 0, 0)
        self.vibrate(1000)
        self.beep(2000, 500)

    def sos_alarm(self):
        for _ in range(5):
            self.set_led(1, 0, 0)
            self.beep(3000, 300)
            self.vibrate(300)
            self.set_led(0, 0, 0)
            time.sleep_ms(100)
