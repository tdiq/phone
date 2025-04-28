import logging
import socket
import time
import array

log = logging.getLogger("ARTNET")

class ArtNetClient:
    """
    A minimal Art-Net implementation for sending DMX values over network.
    Compatible with Python 3.5+.
    
    Attributes:
        target_ip (str): The IP address to send ArtNet data to
        universe (int): The universe number (0-255)
        packet_size (int): Size of DMX packet (usually 512)
    """
    
    HEADER = b'Art-Net\x00'  # Art-Net Header
    PROTOCOL_VERSION = 14    # Current protocol is 14
    OPCODE_ARTDMX = 0x5000  # ArtDMX opcode
    
    def __init__(self, target_ip="127.0.0.1", universe=0, packet_size=512):
        """
        Initialize ArtNet sender.
        
        Args:
            target_ip (str): IP address to send ArtNet data to. Defaults to "127.0.0.1".
            universe (int): Universe number (0-255). Defaults to 0.
            packet_size (int): Size of DMX packet. Defaults to 512.
        """
        self.target_ip = target_ip
        self.universe = min(255, max(0, universe))  # Clamp between 0-255
        self.packet_size = min(512, max(24, packet_size))  # Clamp between 24-512
        
        # Initialize socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Initialize DMX buffer with zeros
        self._buffer = array.array('B', [0] * self.packet_size)
        
        log.info("ArtNet Client configured to send TO {}, Universe: {}".format(
            self.target_ip, self.universe))
    
    def _make_packet(self):
        """Construct the Art-Net packet with current buffer data."""
        # Packet header
        packet = bytearray(self.HEADER)  # Art-Net header
        packet.extend([
            self.OPCODE_ARTDMX & 0xFF,        # Opcode LSB
            (self.OPCODE_ARTDMX >> 8) & 0xFF, # Opcode MSB
            0x00,                             # Protocol version high
            self.PROTOCOL_VERSION,            # Protocol version low
            0x00,                             # Sequence (disabled)
            0x00,                             # Physical input port
            self.universe & 0xFF,             # Universe LSB
            0x00,                             # Universe MSB (Net + Subnet)
            (self.packet_size >> 8) & 0xFF,   # Length MSB
            self.packet_size & 0xFF,          # Length LSB
        ])
        
        # Add DMX data
        packet.extend(self._buffer)
        return packet
    
    def send_value(self, channel, value):
        """
        Send a single DMX value to a specific channel.
        
        Args:
            channel (int): DMX channel number (1-512)
            value (int): DMX value (0-255)
        """
        try:
            # Adjust channel to 0-based index
            channel_idx = channel - 1
            if not 0 <= channel_idx < self.packet_size:
                raise ValueError("Channel must be between 1 and {}".format(self.packet_size))
            if not 0 <= value <= 255:
                raise ValueError("Value must be between 0 and 255")
            
            self._buffer[channel_idx] = value
            packet = self._make_packet()
            self._socket.sendto(packet, (self.target_ip, 6454))  # 6454 is the Art-Net port
            log.debug("Sent DMX value {} to channel {}".format(value, channel))
        except Exception as e:
            log.error("Error sending ArtNet value to channel {}: {}".format(channel, e))
    
    def blackout(self):
        """Sets all channels to 0."""
        try:
            for i in range(self.packet_size):
                self._buffer[i] = 0
            packet = self._make_packet()
            self._socket.sendto(packet, (self.target_ip, 6454))
            log.debug("Set all channels to 0")
        except Exception as e:
            log.error("Error setting blackout: {}".format(e))
    
    def all_on(self):
        """Sets all channels to 1."""
        try:
            for i in range(self.packet_size):
                self._buffer[i] = 1
            packet = self._make_packet()
            self._socket.sendto(packet, (self.target_ip, 6454))
            log.debug("Set all channels to 1")
        except Exception as e:
            log.error("Error setting all on: {}".format(e))

    def stop(self):
        """Closes the socket."""
        try:
            self._socket.close()
            log.debug("ArtNet Client stopped")
        except Exception as e:
            log.error("Error stopping ArtNet client: {}".format(e))


if __name__ == "__main__":
    print("--- Starting ArtNet Example ---")

    artnet = ArtNetClient(target_ip="192.168.0.10", universe=0)

    try:
        print("420 blaze em")
        
        artnet.send_value(channel=450, value=30)  
        time.sleep(2)            
        artnet.blackout()
        
    except KeyboardInterrupt:
        print("\n--- KeyboardInterrupt received ---")
    except Exception as e:
        print("\n--- An error occurred: {} ---".format(e))
    finally:
        print("--- Shutting down ---")
        artnet.stop()
        print("--- Program finished ---") 