# gsm.py — SIM800L emergency SMS and call

from machine import UART, Pin
import time


class GSM:
    def __init__(self, tx_pin=0, rx_pin=1, baudrate=9600):
        self.uart = UART(0, baudrate=baudrate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        time.sleep(2)
        self._send_cmd("AT")
        self._send_cmd("AT+CMGF=1")

    def _send_cmd(self, cmd, wait_ms=500):
        self.uart.write((cmd + "\r\n").encode())
        time.sleep_ms(wait_ms)
        return self.uart.read()

    def send_sms(self, number, message):
        self._send_cmd(f'AT+CMGS="{number}"', 500)
        self.uart.write((message + chr(26)).encode())
        time.sleep(3)

    def make_call(self, number):
        self._send_cmd(f"ATD{number};", 1000)
        time.sleep(10)
        self._send_cmd("ATH")

    def send_sos(self, number, lat=None, lon=None):
        if lat and lon:
            msg = (f"SOS! I need help!\n"
                   f"Location: https://maps.google.com/?q={lat},{lon}\n"
                   f"-- Safety Device Alert")
        else:
            msg = "SOS! I need help! Safety device triggered. Please call me immediately."
        self.send_sms(number, msg)
