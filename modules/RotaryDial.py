import gpiozero
from threading import Timer
import time
import logging
import os

from modules.Utils import kill_timer

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("DIAL")

PIN_DIAL = 25
PIN_HOOK = 8
MAX_DIAL_DIGITS = 3

DIGIT_TIMEOUT = 5 #Time between dialling numbers. If this elapses, current number is called.

class RotaryDial:

    dialTimer = None
    last_input = 0

    cb_number_dialed = None #callback function for when number is dialled

    current_number = ""

    def __init__(self):
        log.debug("Initializing dial")
        self.dial = gpiozero.Button(pin=PIN_DIAL, pull_up=True, bounce_time=0.05)
        self.dial.when_pressed = self.cb_dial_triggered


  #If digit meets MAX_DIAL_DIGIT length, call number. Otherwise reset dial timer.
    def got_digit(self, digit):
        log.debug("got digit")
        return


    def cb_dial_triggered(self):
        log.debug("ignoring dial trigger")


    def cb_dial_timer(self):
        log.debug("Dial timer elapsed")

    def cancel_dial_timer(self):
        log.debug("Cancelling dial timer")
        if self.dialTimer is not None:
            self.dialTimer.cancel()

    def register_callback(self, cb_dial_number, cb_got_digit):
        self.cb_dial_number = cb_dial_number
        self.cb_got_digit = cb_got_digit
        

    def stop(self):
        kill_timer(self.dialTimer)