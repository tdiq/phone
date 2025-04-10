# handset.py
import logging
import os # <<< Added import os
import pygame
from pygame import mixer
import pyaudio
import wave
import audioop
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor as Pool
import threading
import struct
import math
import sys

# --- Configuration ---
LOGLEVEL = os.environ.get("LOGLEVEL", "INFO")
TMP_DIR = "tmp"

# --- Logging Setup ---
logging.basicConfig(level=LOGLEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("HANDSET")

# --- Pygame Event ---
PLAYBACK_FINISHED_EVENT = pygame.USEREVENT + 1

class Handset:

    audioChannel = None
    soundVolume = 1
    pool = None
    speech_speed = "150"

    onHook = True
    _is_listening = False
    _listen_lock = threading.Lock()

    def __init__(self):
        log.debug("Initializing handset")
        self.onHook = True
        try:
            os.makedirs(TMP_DIR, exist_ok=True)
            log.debug("Ensured temporary directory exists: {}".format(TMP_DIR))

            # --- Initialize Pygame Mixer and Display ---
            # Display init is needed for event pump, even if headless.
            # Ensure SDL_VIDEODRIVER is set appropriately (e.g., 'dummy')
            # *before* calling this constructor if running headless.
            mixer.init()
            pygame.display.init() # <<< Put this back
            # --- End Init ---

            self.audioChannel = mixer.Channel(1)
            self.audioChannel.set_endevent(PLAYBACK_FINISHED_EVENT)
            log.debug("Audio channel {} initialized with end event {}".format(self.audioChannel, PLAYBACK_FINISHED_EVENT))

            self.pool = Pool(max_workers=2)
            log.debug("Thread pool initialized.")

        except pygame.error as e:
            # Using .format()
            log.error("Pygame mixer or display init failed: {}. Audio/Events might not work.".format(e), exc_info=True)
            self.audioChannel = None
            self.pool = None
        except Exception as e:
            log.error("Error during Handset init: {}".format(e), exc_info=True)
            self.audioChannel = None
            self.pool = None

    # ... ( _submit_task method remains the same ) ...
    def _submit_task(self, func, *args, **kwargs):
        """Helper to submit tasks to the pool and log errors."""
        if not self.pool:
            log.error("Thread pool not available. Cannot submit task.")
            return None
        try:
            future = self.pool.submit(func, *args, **kwargs)
            future.add_done_callback(self._log_future_exception)
            log.debug("Submitted task {} to pool.".format(func.__name__))
            return future
        except Exception as e:
            log.error("Failed to submit task {} to pool: {}".format(func.__name__, e))
            return None

    # ... ( _log_future_exception method remains the same ) ...
    def _log_future_exception(self, future):
        """Callback for logging results/exceptions from futures."""
        if future.cancelled():
            log.info("Future was cancelled.")
        elif future.exception() is not None:
            log.error("Exception occurred in background task: {}".format(future.exception()), exc_info=future.exception())
        else:
            log.debug("Background task completed successfully. Result: {}".format(future.result()))

    # ... ( play_file method remains the same ) ...
    def play_file(self, filename):
        """Plays a file non-blockingly. Stops previous sound on the channel."""
        if not self.audioChannel:
            log.error("Audio channel not initialized. Cannot play file.")
            return False
        log.info("Playing file: {}".format(filename))
        try:
            s = mixer.Sound(filename)
            s.set_volume(self.soundVolume)
            self.audioChannel.stop() # Stop previous sound first
            self.audioChannel.play(s)
            return True
        except pygame.error as e:
            log.error("Error playing sound file {}: {}".format(filename, e))
            return False

    # ... ( speak method remains the same ) ...
    def speak(self, text, cb=None, sleep=0):
        """Uses espeak TTS in a background thread."""
        log.info("Requesting TTS: '{}'".format(text))
        if self.onHook:
            log.warning("Cannot speak, phone is on hook.")
            return
        if not self.pool:
             log.error("Thread pool not available. Cannot submit speak task.")
             return
        def task():
             try:
                 subprocess.call(["/usr/bin/espeak", "-s", self.speech_speed, text], shell=False)
             except FileNotFoundError:
                  log.error("espeak command not found. Please install espeak.")
             except Exception as e:
                  log.error("Error executing espeak: {}".format(e))
        future = self._submit_task(task)
        if future:
            if cb: future.add_done_callback(cb)
            if sleep > 0:
                future.add_done_callback(lambda f, s=sleep: time.sleep(s))

    # ... ( record method remains the same ) ...
    def record(self, seconds=5, filename=os.path.join(TMP_DIR,'recording.wav')):
        """Records audio for a duration. Returns True if recording saved, False otherwise."""
        if self.onHook:
            log.warning("Cannot record, phone is on hook.")
            return False
        log.info("Recording audio for {}s to {}...".format(seconds, filename))
        rec_format = pyaudio.paInt16
        rec_channels = 1
        sample_rate = 44100
        chunk = 1024
        audio = None
        stream = None
        frames = []
        recording_started = False
        success = False
        try:
            audio = pyaudio.PyAudio()
            stream = audio.open(format=rec_format, channels=rec_channels, rate=sample_rate, input=True, frames_per_buffer=chunk)
            recording_started = True
            log.debug("Audio stream opened for recording.")
            total_chunks = int(sample_rate / chunk * seconds)
            for i in range(total_chunks):
                if self.onHook and self._is_listening:
                    log.warning("Hang up detected during recording loop (in listening mode). Stopping early.")
                    break
                try:
                    data = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data)
                except IOError as e:
                    if e.errno == pyaudio.paInputOverflowed: log.warning("Audio input overflowed. Skipping chunk.")
                    else: raise
            log.debug("Recording loop finished. Recorded {} chunks.".format(len(frames)))
            if frames:
                log.debug("Saving {} frames to {}".format(len(frames), filename))
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(rec_channels)
                    sample_width = 2
                    try: sample_width = audio.get_sample_size(rec_format)
                    except Exception: pass
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(frames))
                log.debug("Recording successfully saved to {}".format(filename))
                success = True
            else:
                log.warning("No frames captured, not saving file {}".format(filename))
        except Exception as e:
            log.error("Error during PyAudio recording: {}".format(e), exc_info=True)
        finally:
            if stream:
                try:
                    if recording_started and stream.is_active(): stream.stop_stream()
                    stream.close()
                    log.debug("Audio stream closed.")
                except Exception: pass
            if audio:
                try: audio.terminate()
                except Exception: pass
            log.debug("PyAudio terminated.")
        return success

    # ... ( _wait_for_playback_or_hangup method remains the same ) ...
    def _wait_for_playback_or_hangup(self, filename):
        """Waits for audio playback to finish or phone to be hung up."""
        if not self.audioChannel or not self.audioChannel.get_busy():
            log.warning("Playback of {} didn't start or was instant.".format(filename))
            return False
        log.debug("Waiting for '{}' playback to finish or hang-up...".format(filename))
        playback_normally_completed = False
        while not self.onHook:
            event_handled = False
            for event in pygame.event.get():
                if event.type == PLAYBACK_FINISHED_EVENT:
                     if not self.audioChannel.get_busy():
                         log.debug("Playback finished event received.")
                         playback_normally_completed = True
                         event_handled = True
                         break
                elif event.type == pygame.QUIT:
                     log.warning("Pygame quit event detected during wait.")
                     self.onHook = True
                     event_handled = True
                     break
            if event_handled and (playback_normally_completed or self.onHook):
                 break
            if self.onHook: break
            time.sleep(0.05)
        return playback_normally_completed

    # ... ( _record_and_analyze method remains the same ) ...
    def _record_and_analyze(self, listen_duration, silence_threshold):
        """Performs recording and analysis. Returns 'speech', 'silence', or 'error'."""
        record_filename = os.path.join(TMP_DIR, "listen_rec_{}.wav".format(int(time.time())))
        log.debug("Recording for {}s to {}".format(listen_duration, record_filename))
        self._is_listening = True
        recorded_ok = self.record(seconds=listen_duration, filename=record_filename)
        self._is_listening = False
        analysis_result = "error"
        if self.onHook:
            log.info("Hung up during/after recording. Discarding result.")
        elif recorded_ok and os.path.exists(record_filename):
            log.debug("Analyzing recording: {}".format(record_filename))
            try:
                with wave.open(record_filename, 'rb') as wf:
                    n_frames = wf.getnframes()
                    if n_frames > 0:
                        frames = wf.readframes(n_frames)
                        width = wf.getsampwidth()
                        rms = audioop.rms(frames, width)
                        log.debug("Analyzed RMS: {}, Threshold: {}".format(rms, silence_threshold))
                        analysis_result = "speech" if rms > silence_threshold else "silence"
                    else:
                         log.debug("Recording appears empty (0 frames).")
                         analysis_result = "silence"
            except Exception as e:
                log.error("Error analyzing audio file {}: {}".format(record_filename, e), exc_info=True)
                analysis_result = "error"
        else:
             log.warning("Recording file {} not found or empty after recording attempt.".format(record_filename))
             analysis_result = "error"
        if os.path.exists(record_filename):
             try: os.remove(record_filename)
             except OSError as e: log.warning("Could not remove temp recording {}: {}".format(record_filename, e))
        return analysis_result

    # ... ( _do_play_and_listen_task method remains the same ) ...
    def _do_play_and_listen_task(self, filename, on_speech_cb, on_silence_cb, listen_duration, silence_threshold):
        """Background task combining the steps."""
        try:
            if not self.play_file(filename):
                raise RuntimeError("Playback failed to start for {}".format(filename))
            playback_completed = self._wait_for_playback_or_hangup(filename)
            if self.onHook:
                log.info("Hung up during playback wait. Cancelling listen.")
                return
            if not playback_completed:
                 log.warning("Playback didn't complete normally (e.g., short file?). Continuing to record.")
            analysis_result = "error"
            if not self.onHook:
                analysis_result = self._record_and_analyze(listen_duration, silence_threshold)
            else:
                 log.info("Hung up right after playback, before recording could start.")
            if not self.onHook:
                if analysis_result == "speech":
                    log.info("Speech detected.")
                    if on_speech_cb:
                        try: on_speech_cb()
                        except Exception as e: log.error("Error in on_speech_cb: {}".format(e), exc_info=True)
                elif analysis_result == "silence":
                    log.info("Silence detected.")
                    if on_silence_cb:
                         try: on_silence_cb()
                         except Exception as e: log.error("Error in on_silence_cb: {}".format(e), exc_info=True)
                else:
                     log.error("Listen process encountered an error during recording/analysis.")
            else:
                 log.info("Hung up before final callback could be made.")
        except Exception as e:
            log.error("Unhandled error in _do_play_and_listen_task thread: {}".format(e), exc_info=True)
        finally:
            self._is_listening = False
            self._listen_lock.release()
            log.debug("Play and listen task finished.")

    # ... ( play_and_listen method remains the same ) ...
    def play_and_listen(self, filename, on_speech_detected_cb, on_silence_detected_cb, listen_duration=3, silence_threshold=500):
        """ Plays audio, then listens for speech. Calls callbacks in background thread. """
        if not self.audioChannel: log.error("Audio channel not available. Cannot play and listen."); return
        if not self.pool: log.error("Thread pool not available. Cannot play and listen."); return
        if self.onHook: log.warning("Phone is on hook. Cannot play and listen."); return
        if not self._listen_lock.acquire(blocking=False): log.warning("Another play_and_listen process is already running. Ignoring new request."); return
        log.info("Initiating play_and_listen: Play '{}', Listen {}s (Threshold: {})".format(filename, listen_duration, silence_threshold))
        self._submit_task(self._do_play_and_listen_task, filename, on_speech_detected_cb, on_silence_detected_cb, listen_duration, silence_threshold)

    # ... ( on_hook method remains the same ) ...
    def on_hook(self):
        """Called when the phone is hung up."""
        if not self.onHook:
             log.info("Phone HUNG UP")
             self.onHook = True
             if self.audioChannel: self.audioChannel.stop()

    # ... ( off_hook method remains the same ) ...
    def off_hook(self):
        """Called when the phone is picked up."""
        if self.onHook:
             log.info("Phone PICKED UP")
             self.onHook = False

    # ... ( stop method remains the same ) ...
    def stop(self):
        """General stop method - primarily stops audio."""
        log.debug("Handset stop called.")
        if self.audioChannel: self.audioChannel.stop()
        self.cleanup()


    # ... ( set_volume method remains the same ) ...
    def set_volume(self, volume):
        log.debug("Setting volume to {}".format(volume))
        self.soundVolume = volume
        if self.audioChannel and self.audioChannel.get_sound():
            try: self.audioChannel.get_sound().set_volume(self.soundVolume)
            except pygame.error as e: log.warning("Could not set volume on current sound: {}".format(e))

    # ... ( cleanup method remains the same ) ...
    def cleanup(self):
        """Clean up resources like thread pool and pygame."""
        log.info("Cleaning up Handset resources...")
        if self.pool:
            log.debug("Shutting down thread pool...")
            self.pool.shutdown(wait=True)
            log.debug("Thread pool shut down.")
        log.debug("Quitting pygame mixer...")
        mixer.quit()
        log.debug("Quitting pygame display...")
        pygame.display.quit()
        log.debug("Pygame quit complete.")


# --- Standalone Test Block ---

# ... ( create_dummy_wav function remains the same ) ...
def create_dummy_wav(filename="test_prompt.wav", duration_ms=1500, freq=440):
    """Creates a simple mono WAV file with a sine wave tone."""
    if os.path.exists(filename): log.info("Dummy WAV file '{}' already exists.".format(filename)); return
    log.info("Creating dummy WAV file '{}' ({}ms, {}Hz)".format(filename, duration_ms, freq))
    sample_rate = 44100; n_samples = int(sample_rate * duration_ms / 1000.0); n_channels = 1; sampwidth = 2; n_frames = n_samples; comptype = "NONE"; compname = "not compressed"; amplitude = 16000
    try:
        with wave.open(filename, 'wb') as wf:
            wf.setparams((n_channels, sampwidth, sample_rate, n_frames, comptype, compname))
            for i in range(n_samples):
                value = int(amplitude * math.sin(2 * math.pi * freq * i / sample_rate))
                packed_value = struct.pack('<h', value)
                wf.writeframes(packed_value)
        log.info("Successfully created '{}'".format(filename))
    except Exception as e: log.error("Failed to create dummy WAV '{}': {}".format(filename, e))


if __name__ == "__main__":
    # --- Test Configuration ---
    # TEST_AUDIO_FILE = os.path.join(TMP_DIR, "test_prompt.wav")
    TEST_AUDIO_FILE = "assets/dialogue/1_child_have-to-whisper.wav"
    TEST_LISTEN_DURATION = 5
    TEST_SILENCE_THRESHOLD = 1000

    # --- MODIFICATION: Set Dummy Video Driver ---
    print("Setting SDL_VIDEODRIVER=dummy")
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    # --- End Modification ---

    print("\n--- Handset Standalone Test ---")
    print(" Temporary directory: {}".format(TMP_DIR))
    print(" Test audio file: {}".format(TEST_AUDIO_FILE))
    print(" Listen duration: {}s".format(TEST_LISTEN_DURATION))
    print(" Silence threshold: {} (Lower = more sensitive to noise)".format(TEST_SILENCE_THRESHOLD))
    print("-----------------------------")

    pygame.quit() # Ensure Pygame is fully quit before initializing

    create_dummy_wav(TEST_AUDIO_FILE)
    if not os.path.exists(TEST_AUDIO_FILE):
         print("ERROR: Test audio file '{}' could not be created/found. Exiting.".format(TEST_AUDIO_FILE))
         sys.exit(1)

    print("\nInitializing Handset (with dummy driver)...")
    handset = Handset() # Now calls init which includes pygame.display.init()
    if not handset.audioChannel:
         print("ERROR: Handset initialization failed (audio channel is None).")
         print("       Make sure audio devices are available and Pygame/PyAudio are installed correctly.")
         sys.exit(1)
    if not handset.pool:
         print("ERROR: Handset initialization failed (thread pool is None).")
         sys.exit(1)
    print("Handset initialized successfully.")

    def speech_callback(): print("\n*** TEST: Speech Detected! ***\n")
    def silence_callback(): print("\n*** TEST: Silence Detected! ***\n")

    try:
        while True:
            print("\nOptions:")
            print("  1. Simulate PICK UP phone")
            print("  2. Simulate HANG UP phone")
            print("  3. Play test sound ('play_file')")
            print("  4. Test TTS ('speak')")
            print("  5. Test Recording ('record')")
            print("  6. Test 'play_and_listen' (will play sound then listen)")
            print("  q. Quit")
            choice = input("Enter choice: ").strip().lower()

            if choice == '1': handset.off_hook()
            elif choice == '2': handset.on_hook()
            elif choice == '3':
                if handset.onHook: print("Phone is on hook. Pick up first (option 1).")
                else: handset.play_file(TEST_AUDIO_FILE)
            elif choice == '4':
                 if handset.onHook: print("Phone is on hook. Pick up first (option 1).")
                 else: handset.speak("Testing one two three.")
            elif choice == '5':
                 if handset.onHook: print("Phone is on hook. Pick up first (option 1).")
                 else:
                     rec_file = os.path.join(TMP_DIR, "manual_test_record.wav")
                     print("Recording for 3 seconds to {}...".format(rec_file))
                     success = handset.record(seconds=3, filename=rec_file)
                     if success: print("Recording saved.")
                     else: print("Recording failed.")
            elif choice == '6':
                if handset.onHook: print("Phone is on hook. Pick up first (option 1).")
                else:
                    print("\nStarting 'play_and_listen':")
                    print(" - Playing: {}".format(TEST_AUDIO_FILE))
                    print(" - Then listening for {} seconds...".format(TEST_LISTEN_DURATION))
                    print( "Speak clearly during the listening phase to test speech detection.")
                    print( "Stay silent to test silence detection.")
                    handset.play_and_listen(filename=TEST_AUDIO_FILE, on_speech_detected_cb=speech_callback, on_silence_detected_cb=silence_callback, listen_duration=TEST_LISTEN_DURATION, silence_threshold=TEST_SILENCE_THRESHOLD)
                    print("(play_and_listen started in background, waiting for results...)")
            elif choice == 'q': print("Quitting..."); break
            else: print("Invalid choice.")

            # Event pump in main loop is still good practice
            try:
                 pygame.event.pump()
            except pygame.error as e:
                 # This might still fail if dummy driver setup wasn't perfect, but log it
                 log.warning("pygame.event.pump() failed in main loop: {}".format(e))
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Exiting.")
    finally:
        print("\nCleaning up resources...")
        handset.cleanup()
        print("Test finished.")