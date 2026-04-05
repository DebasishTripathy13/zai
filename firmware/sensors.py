# sensors.py — MPU6050 IMU + INMP441 Microphone

from machine import I2C, Pin, I2S
import math, time


class MPU6050:
    MPU_ADDR = 0x68

    def __init__(self, sda_pin=8, scl_pin=9):
        self.i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        self.i2c.writeto_mem(self.MPU_ADDR, 0x6B, b'\x00')
        time.sleep(0.1)

    def read_accel(self):
        data = self.i2c.readfrom_mem(self.MPU_ADDR, 0x3B, 6)
        ax = (data[0] << 8 | data[1]) / 16384.0
        ay = (data[2] << 8 | data[3]) / 16384.0
        az = (data[4] << 8 | data[5]) / 16384.0
        return ax, ay, az

    def get_magnitude(self):
        ax, ay, az = self.read_accel()
        return math.sqrt(ax**2 + ay**2 + az**2)

    def detect_fall(self, threshold=2.5):
        mag = self.get_magnitude()
        return mag > threshold or mag < 0.3


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
        self.audio_in.readinto(self.buf)
        samples = [int.from_bytes(self.buf[i:i+2], 'little', True)
                   for i in range(0, len(self.buf), 2)]
        rms = math.sqrt(sum(s**2 for s in samples) / len(samples))
        return rms

    def detect_scream(self, threshold=2000):
        return self.get_audio_level() > threshold
