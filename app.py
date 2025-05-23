import time
import sys
import logging
import os
import signal

#using pygame for audio and events
os.environ['SDL_VIDEODRIVER'] = 'dummy'

from modules.Phone import Phone
from modules.OSC import OSCHandler
from modules.ArtNet import ArtNetClient
from modules.Serial import Serial

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("app")

CTRL_PC_ADDRESS="192.168.0.20"
DMX_TO_ARTNET_ADDRESS="192.168.0.10"
SMOKE_MACHINE_DMX_ADDRESS = 450

tdiq_phone_instance = None

class TDIQPhone:
    def __init__(self):
        log.info("Initializing...")

        self.phone = Phone(pick_up_cb=self.on_pick_up_phone, hang_up_cb=self.on_hang_up_phone)

        self.osc = OSCHandler(send_ip=CTRL_PC_ADDRESS)
        self.osc.subscribe("/props/phone/start", self.on_start_msg)
        self.osc.start_server()
        self.artnet = ArtNetClient(target_ip=DMX_TO_ARTNET_ADDRESS, universe=0)
        self.phone.handset.loop_file("assets/dialogue/call2.wav")
        log.info("Initialization complete")

    def on_pick_up_phone(self):
            log.info("phone picked up")
            self.osc.send("/props/phone/pickup", 1)
            # self.phone.handset.loop_file("assets/dialogue/call2.wav")
            # log.info("smokin meats")
            # self.artnet.send_value(channel=SMOKE_MACHINE_DMX_ADDRESS, value=30)
            # time.sleep(0.75)
            # log.info("done smokin em")
            # self.artnet.send_value(channel=SMOKE_MACHINE_DMX_ADDRESS, value=0)


    def on_hang_up_phone(self):
        self.osc.send("/props/phone/hangup", 1)
        self.phone.handset.stop_loop()

    def on_start_msg(self, address, value):
        log.info("received message to start")
        self.phone.single_ring()

    def stop(self):
        log.info("Safely shutting down tdiq phone...")
        if hasattr(self, 'osc') and self.osc:
             self.osc.stop_server()
             log.info("OSC server stopped.")
        if hasattr(self, 'phone') and self.phone:
            self.phone.stop()
            log.info("Phone resources released.")
        
        self.artnet.send_value(channel=SMOKE_MACHINE_DMX_ADDRESS, value=0)

        log.info("Shutdown tasks complete.")


def shutdown_handler(signum, frame):
    """Gracefully shut down the application upon receiving SIGTERM or SIGINT."""
    log.warning("Received signal {}. Initiating shutdown...".format(signum))
    if tdiq_phone_instance:
        tdiq_phone_instance.stop()
    else:
        log.warning("Application instance not found for cleanup.")
    log.warning("Exiting application.")
    sys.exit(0) 


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        # Assign the instance to the global variable
        tdiq_phone_instance = TDIQPhone()
        log.info("We're up...")

        # Keep the main thread alive. signal.pause() waits efficiently for signals.
        while True:
            signal.pause() # Wait here until a signal is received and handled

    except Exception as e:
        log.error("An unexpected critical error occurred: {}".format(e), exc_info=True)
        if tdiq_phone_instance:
             log.info("Attempting emergency cleanup...")
             tdiq_phone_instance.stop()
        sys.exit(1)
