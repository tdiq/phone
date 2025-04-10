import logging
import gpiozero
import os
import time

from modules.RotaryDial import RotaryDial
from modules.Handset import Handset


logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("PHONE")

PIN_LEFT_RING = 23
PIN_RIGHT_RING = 24
PIN_HOOKSWITCH = 8

class Phone:
    dial = None
    handset = None

    def __init__(self, pick_up_cb, hang_up_cb):
        log.debug("Initializing phone")

        self.handset = Handset()
        self.dial = RotaryDial()
        self.dial.register_callback(cb_dial_number=self.call, cb_got_digit=self.cb_got_digit) 
        #cb_dial_number dialer calls this function when user has finished dialing
        #cb_got_digit dialer calls function when user has dialed first digit

        self.hookswitch = gpiozero.Button(pin=PIN_HOOKSWITCH, pull_up=True, bounce_time=0.05)
        self.hookswitch.when_pressed = lambda: (
            log.debug("Phone off hook"),
            self.handset.off_hook(),    
            pick_up_cb()                 
        )
        self.hookswitch.when_released = lambda: (
            log.debug("Phone on hook"),  
            self.handset.on_hook(),      
            hang_up_cb()                 
        )

        self.leftRing = gpiozero.OutputDevice(PIN_LEFT_RING)
        self.rightRing = gpiozero.OutputDevice(PIN_RIGHT_RING)

        if not os.environ.get("SKIP_TEST"):
            log.debug("Testing ringer...")
            time.sleep(1)
            self.single_ring()
            log.debug("Testing handset...")
            self.handset.set_volume(1)
            self.handset.speak("Ready to work, captain")
            self.handset.set_volume(0.75)

    def stop(self):
        self.kill_ringer()
        self.handset.stop()
        self.dial.stop()

    def single_ring(self):
        log.info("Ringing...")
        for rings in range(0, 10):
            self.rightRing.off()
            self.leftRing.on()

            time.sleep(0.05)

            self.leftRing.off()
            self.rightRing.on()

            time.sleep(0.05)

            self.rightRing.off()
            self.leftRing.off()

    def kill_ringer(self):
        self.rightRing.off()
        self.leftRing.off()

    def call(self, number):
        log.info("calling " + str(number))
        self.dial.cancel_dial_timer()
        

    def cb_off_hook(self, cb):
        log.debug("Phone off hook")
        cb()
        self.handset.off_hook()

    def cb_on_hook(self, cb):
        log.debug("Phone on hook")
        cb()
        self.handset.on_hook()

    def cb_got_digit(self):
        log.debug("Dial has notified phone about first digit. Stopping ringtone")
        self.handset.stop()
