import threading
import time
import logging
from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client

log = logging.getLogger("OSC")

class OSCHandler:
    """
    A class to handle OSC communication, allowing subscription to addresses
    and sending messages. Compatible with Python 3.5+.

    Attributes:
        listen_ip (str): The IP address the server listens on. '0.0.0.0' means listen on all interfaces.
        listen_port (int): The port the server listens on.
        send_ip (str): The default IP address to send messages TO. Must be a specific unicast address.
        send_port (int): The default port to send messages TO.
    """

    def __init__(self, listen_ip="0.0.0.0", listen_port=7000, send_ip="127.0.0.1", send_port=8000):
        """
        Initializes the OSCHandler.

        Args:
            listen_ip (str): IP for the server to listen ON ("0.0.0.0" for all interfaces). Defaults to "0.0.0.0".
            listen_port (int): Port for the server to listen ON. Defaults to 7000.
            send_ip (str): Specific IP address for the client to send TO. Defaults to "127.0.0.1" (localhost).
            send_port (int): Port for the client to send TO. Defaults to 8000.
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.send_ip = send_ip
        self.send_port = send_port

        self._dispatcher = dispatcher.Dispatcher()
        self._server = osc_server.ThreadingOSCUDPServer(
            (self.listen_ip, self.listen_port), self._dispatcher
        )
        self._server_thread = None

        self._client = udp_client.SimpleUDPClient(self.send_ip, self.send_port)
        log.info("OSC Client configured to send TO {}:{}".format(self.send_ip, self.send_port))

    def subscribe(self, address, callback):
        """
        Subscribes a callback function to a specific OSC address.

        Args:
            address (str): The OSC address pattern (e.g., '/filter').
            callback (function): The function to call when a message arrives.
                                 Must accept address (str) and message arguments (*args).
        """
        self._dispatcher.map(address, callback)
        log.debug("Subscribed callback for address: {}".format(address))

    def send(self, address, *args):
        """
        Sends an OSC message to the configured target address and port.

        Args:
            address (str): The OSC address pattern to send to (e.g., '/control/volume').
            *args: The data arguments to send (int, float, str, bool, etc.).
        """
        try:
            self._client.send_message(address, args)
        except Exception as e:
            log.error("Error sending OSC message to {} at target {}:{}: {}".format(
                address, self.send_ip, self.send_port, e))

    def start_server(self):
        """Starts the OSC server in a separate background thread."""
        if self._server_thread is None or not self._server_thread.is_alive():
            self._server_thread = threading.Thread(target=self._server.serve_forever)
            self._server_thread.daemon = True
            self._server_thread.start()
            listen_addr_display = "all interfaces" if self.listen_ip == "0.0.0.0" else self.listen_ip
            log.debug("OSC Server started listening on {} (IP: {}), Port: {}".format(
                listen_addr_display, self.listen_ip, self.listen_port))
        else:
            print("OSC Server is already running.")

    def stop_server(self):
        """Stops the OSC server gracefully."""
        if self._server and self._server_thread and self._server_thread.is_alive():
            print("Attempting to shut down OSC server...")
            self._server.shutdown()
            self._server_thread.join(timeout=2)
            if self._server_thread.is_alive():
                print("Warning: Server thread did not shut down cleanly.")
            try:
                self._server.server_close()
            except Exception as e:
                print("Exception during server_close: {}".format(e))
            self._server_thread = None
            log.debug("OSC Server stopped.")
        else:
            print("OSC Server is not running or already stopped.")


def handle_slider_change(address, value):
    """Callback function for handling slider changes."""
    print("Received slider value via OSC: Address: {}, Value: {}".format(address, value))

def handle_button_press(address, *args):
    """Callback function for handling button presses."""
    print("Received button press via OSC: Address: {}, Arguments: {}".format(address, args))

if __name__ == "__main__":
    print("--- Starting OSC Example ---")

    osc_manager = OSCHandler(send_ip="10.0.0.45")

    osc_manager.subscribe("/1/fader1", handle_slider_change)
    osc_manager.subscribe("/control/button/play", handle_button_press)
    osc_manager.start_server()

    try:
        status_message = "Script started, sending TO {}:{}".format(osc_manager.send_ip, osc_manager.send_port)
        osc_manager.send("/feedback/status", status_message)
        time.sleep(1)
        osc_manager.send("/data/value", 100, 20.5, "test payload")
        osc_manager.send("test", 100, 20.5, "test payload")
        time.sleep(1)
        

        log.debug("Listening for OSC messages on port {} on all interfaces.".format(osc_manager.listen_port))
        print("Default send target is {}:{}".format(osc_manager.send_ip, osc_manager.send_port))
        print("Try sending OSC to this machine's IP on port {}\n".format(osc_manager.listen_port))

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n--- KeyboardInterrupt received ---")
    except Exception as e:
        print("\n--- An error occurred: {} ---".format(e))
    finally:
        print("--- Shutting down ---")
        osc_manager.stop_server()
        print("--- Program finished ---")