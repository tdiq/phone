import time
import sys
import logging
import os
import signal

#using pygame for audio and events
os.environ['SDL_VIDEODRIVER'] = 'dummy'

from modules.Phone import Phone
from modules.OSC import OSCHandler

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("app")

CTRL_PC_ADDRESS="10.0.0.45"
# CTRL_PC_ADDRESS="192.168.0.20"

# This allows the signal handler to access it for cleanup.
tdiq_phone_instance = None

class TDIQPhone:
    def __init__(self):
        log.info("Initializing...")

        self.phone = Phone(pick_up_cb=self.on_pick_up_phone, hang_up_cb=self.on_hang_up_phone)

        self.osc = OSCHandler(send_ip=CTRL_PC_ADDRESS)
        self.osc.subscribe("/props/phone/start", self.on_start_msg)
        self.osc.start_server()

        log.info("Initialization complete")

    def on_pick_up_phone(self):
            log.info("phone picked up")
            self.osc.send("/props/phone/pickup", 1)

            intro_audio = "assets/dialogue/1_child_have-to-whisper.wav"
            self.phone.handset.play_and_listen(
                filename=intro_audio,
                on_speech_detected_cb=self.handle_user_spoke,
                on_silence_detected_cb=self.handle_user_silent,
                listen_duration=4, # seconds
                silence_threshold=1000 # threshold for speech detection
            )

 # WIP - we should probably figure out a way to pass the silence/speech detection status via the callback
    def handle_user_spoke(self):
        log.info("User spoke after the prompt!")
        self.osc.send("/props/phone/user_spoke", 1)
        self.phone.handset.play_file("assets/dialogue/2-you-remember-dont-you.wav")
        self.phone.handset.play_file("assets/dialogue/3-happy-birthday-spell.wav")
        self.phone.handset.play_file("assets/dialogue/4-always-listening.wav")

    def handle_user_silent(self):
        log.info("User was silent after the prompt.")
        self.osc.send("/props/phone/user_silent", 1)
        self.phone.handset.play_file("assets/dialogue/2-you-remember-dont-you.wav")
        self.phone.handset.play_file("assets/dialogue/3-happy-birthday-spell.wav")
        self.phone.handset.play_file("assets/dialogue/4-always-listening.wav")

    def on_hang_up_phone(self):
        self.osc.send("/props/phone/hangup", 1)

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