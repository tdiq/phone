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
        #nfi why this is off by one
        if(digit != 9): 
            digit += 1 
        elif(digit == 10):
            digit = 0
        self.current_number += str(digit)
        log.debug("Got digit " + str(digit) + ". Current number is " + str(self.current_number) )

        if len(self.current_number) == 1:
            self.cb_got_digit() #let phone know we got a digit, used for controlling ringtone

        if len(self.current_number) == MAX_DIAL_DIGITS:
            log.info("Dialed max number of digits. Dialing number " + str(self.current_number))
            self.cb_dial_number(self.current_number)
            self.current_number = ""
            self.dialTimer.cancel()
        else:
            self.cancel_dial_timer()

            self.dialTimer = Timer(DIGIT_TIMEOUT, self.cb_dial_timer)
            self.dialTimer.start()


    def cb_dial_triggered(self):
        log.debug("dial triggered")
        while self.dial.is_pressed:
            last_dial_state = True
        
        # Wait for dialling to complete
        current_digit = 0
        last_timestamp = time.time()
        while (time.time() - last_timestamp) < 0.3:
            current_dial_state = self.dial.is_pressed
            if not current_dial_state and last_dial_state == True:
                current_digit = current_digit + 1
                last_timestamp = time.time()
                
            last_dial_state = current_dial_state
        if current_digit == 10:
            current_digit = 0
        self.got_digit(current_digit)


    def cb_dial_timer(self):
        log.debug("Dial timer elapsed. Calling " + str(self.current_number))
        self.cb_dial_number(self.current_number) #this is the callback set by app.py
        self.current_number = ""

    def cancel_dial_timer(self):
        log.debug("Cancelling dial timer")
        if self.dialTimer is not None:
            self.dialTimer.cancel()

    def register_callback(self, cb_dial_number, cb_got_digit):
        self.cb_dial_number = cb_dial_number
        self.cb_got_digit = cb_got_digit
        

    def stop(self):
        kill_timer(self.dialTimer)