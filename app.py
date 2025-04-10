import time
import sys
import logging
import os # <<< Import os

#using pygame for audio and events
os.environ['SDL_VIDEODRIVER'] = 'dummy'

from modules.Phone import Phone
from modules.OSC import OSCHandler

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("app")

CTRL_PC_ADDRESS="10.0.0.45"
# CTRL_PC_ADDRESS="192.168.0.20"

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
            
#WIP - we should probably figure out a way to pass the silence/speech detection status via the callback
    def handle_user_spoke(self):
        log.info("User spoke after the prompt!")
        self.osc.send("/props/phone/user_spoke", 1)
        self.phone.handset.play_file("assets/dialogue/2-you-remember-dont-you.wav") #make this an LLM response? or just precook a bunch of random stuff?
        self.phone.handset.play_file("assets/dialogue/3-happy-birthday-spell.wav")
        self.phone.handset.play_file("assets/dialogue/4-always-listening.wav")



    def handle_user_silent(self):
        log.info("User was silent after the prompt.")
        self.osc.send("/props/phone/user_silent", 1)
        self.phone.handset.play_file("assets/dialogue/2-you-remember-dont-you.wav")
        self.phone.handset.play_file("assets/dialogue/3-happy-birthday-spell.wav")
        self.phone.handset.play_file("assets/dialogue/4-always-listening.wav")

#WIP

    def on_hang_up_phone(self):
        log.info("phone hung up")
        self.osc.send("/props/phone/hangup", 1)


    def on_start_msg(self, address, value):
        log.info("received message to start")
        self.phone.single_ring()

    def stop(self):
        log.info("Safely shutting down tdiq phone...")
        self.phone.stop() 
        if hasattr(self, 'osc') and self.osc:
             self.osc.stop_server()


if __name__ == "__main__":
    tardis = None # Define tardis outside try so finally block can access it
    try:
        tardis = TDIQPhone()
        log.info("Application running. Press Ctrl+C to exit.")
        while True:
            # Main loop could potentially check thread health or do other tasks
            time.sleep(1)

    except KeyboardInterrupt:
        log.info("Ctrl+C received. Shutting down.")
        if tardis:
            tardis.stop()
        sys.exit(0)
    except Exception as e:
        log.error("An unexpected error occurred: {}".format(e), exc_info=True)
        if tardis:
             tardis.stop() # Attempt cleanup even on other errors
        sys.exit(1) # Exit with error code