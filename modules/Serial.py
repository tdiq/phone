import serial
import logging
import os
import threading
import time
import serial.tools.list_ports

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("SERIAL")

class Serial:
    def __init__(self, port=None, port_pattern=None, baud_rate=9600):
        """Initialize serial connection with configurable port and baud rate.
        
        Args:
            port: Direct port to connect to (e.g. '/dev/ttyUSB0')
            port_pattern: Pattern to search for in port descriptions/hardware IDs
            baud_rate: Baud rate for serial connection
            
        Raises:
            ValueError: If both port and port_pattern are provided, or if neither is provided
            serial.SerialException: If no matching port is found or connection fails
        """
        if port and port_pattern:
            raise ValueError("Cannot specify both port and port_pattern")
        if not port and not port_pattern:
            raise ValueError("Must specify either port or port_pattern")

        self.baud_rate = baud_rate
        self.serial = None
        self.running = False
        self.reader_thread = None

        if port_pattern:
            log.debug("Searching for port matching pattern: {}".format(port_pattern))
            self.port = self._find_port_by_pattern(port_pattern)
            if not self.port:
                raise serial.SerialException(
                    "No port found matching pattern: {}".format(port_pattern))
            log.debug("Found matching port: {}".format(self.port))
        else:
            self.port = port
            
        self.connect()

    @staticmethod
    def list_ports():
        """List all available serial ports with their descriptions."""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
        return ports

    def _find_port_by_pattern(self, pattern):
        """Find a port matching the given pattern in description or hardware ID.
        
        Args:
            pattern: String to search for in port description or hardware ID
            
        Returns:
            Port device name if found, None otherwise
        """
        for port in serial.tools.list_ports.comports():
            if (pattern.lower() in port.description.lower() or 
                pattern.lower() in port.hwid.lower()):
                try:
                    # Test if we can open the port
                    test_serial = serial.Serial(port.device, self.baud_rate, timeout=1)
                    test_serial.close()
                    return port.device
                except (OSError, serial.SerialException):
                    continue
        return None

    def try_ports(self, port_list):
        """Try to connect to a list of ports in sequence.
        Returns the first successful port or None."""
        for port in port_list:
            try:
                test_serial = serial.Serial(port, self.baud_rate, timeout=1)
                test_serial.close()
                return port
            except (OSError, serial.SerialException):
                log.debug("Failed to connect to {}".format(port))
                continue
        return None

    def connect(self):
        """Establish serial connection and start reader thread."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1  # 1 second timeout for reading
            )
            log.debug("Serial connection established successfully")
            self.start_reader()
        except serial.SerialException as e:
            log.error("Failed to connect to serial port: {}".format(e))
            raise

    def start_reader(self):
        """Start the background reader thread."""
        self.running = True
        self.reader_thread = threading.Thread(target=self._reader_thread)
        self.reader_thread.daemon = True  # Thread will exit when main program does
        self.reader_thread.start()
        
    def _reader_thread(self):
        """Background thread that continuously reads from serial port."""
        while self.running:
            if self.serial and self.serial.is_open and self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line:
                        log.info("arduino says: {}".format(line))
                except serial.SerialException as e:
                    log.error("Error reading from serial: {}".format(e))
                    break
                except UnicodeDecodeError as e:
                    log.error("Error decoding message: {}".format(e))
            time.sleep(0.01)  # Small delay to prevent CPU hogging
    
    def send_string(self, message):
        """Send a string message over serial connection."""
        if self.serial is None:
            log.error("Serial port not open")
            return
        if self.serial and self.serial.is_open:
            try:
                # Add newline to ensure proper transmission
                message = message + '\n'
                self.serial.write(message.encode('utf-8'))
                self.serial.flush()
                log.debug("Sent message: {}".format(message))
            except serial.SerialException as e:
                log.error("Failed to send message: {}".format(e))
                raise
        else:
            log.error("Serial port not open")
            raise serial.SerialException("Serial port not open")
    
    def light_on(self):
        """Turn the light on."""
        log.debug("Turning light on")
        self.send_string('L1')
    
    def light_off(self):
        """Turn the light off."""
        log.debug("Turning light off")
        self.send_string('L0')
    
    def smoke_on(self):
        """Turn the smoke machine on."""
        log.debug("Turning smoke on")
        self.send_string('S1')
    
    def smoke_off(self):
        """Turn the smoke machine off."""
        log.debug("Turning smoke off")
        self.send_string('S0')
    
    def stop(self):
        """Close the serial connection and stop the reader thread."""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=1.0)
        if self.serial and self.serial.is_open:
            self.serial.close()
            log.debug("Serial connection closed")

if __name__ == "__main__":
    try:
        # List available ports first to help with debugging
        log.info("Available ports:")
        for port_info in Serial.list_ports():
            log.info("  Port: {} | Description: {} | Hardware ID: {}".format(
                port_info['device'], 
                port_info['description'], 
                port_info['hwid']
            ))
        
        # Initialize serial connection using pattern matching
        # Looking for common Arduino/USB-Serial patterns
        log.info("Starting Serial test")
        patterns_to_try = ['USB-SERIAL', 'CH340', 'Arduino', 'usbserial', 'ACM', 'USB Serial']
        serial_conn = None
        
        for pattern in patterns_to_try:
            try:
                log.info("Trying to connect using pattern: {}".format(pattern))
                serial_conn = Serial(port_pattern=pattern, baud_rate=9600)
                log.info("Successfully connected using pattern: {}".format(pattern))
                break
            except (ValueError, serial.SerialException) as e:
                log.info("Could not connect using pattern '{}': {}".format(pattern, e))
                continue
        
        if not serial_conn:
            log.error("Could not find any matching serial device")
            exit(1)
            
        # Wait for Arduino to initialize
        time.sleep(2)
        
        # Test light control
        log.info("Testing light control...")
        serial_conn.light_on()
        time.sleep(2)  # Wait to see the effect
        serial_conn.light_off()
        time.sleep(2)  # Wait to see the effect
        
        # Test smoke control
        log.info("Testing smoke control...")
        serial_conn.smoke_on()
        time.sleep(2)  # Wait to see the effect
        serial_conn.smoke_off()
        time.sleep(2)  # Wait to see the effect
        
        # Test both together
        log.info("Testing combined control...")
        serial_conn.light_on()
        serial_conn.smoke_on()
        time.sleep(2)  # Wait to see the effect
        serial_conn.light_off()
        serial_conn.smoke_off()
        time.sleep(1)  # Wait to see the effect
        
        # Clean up
        log.info("Closing connection...")
        serial_conn.stop()
        log.info("Test completed successfully")
        
    except serial.SerialException as e:
        log.error("Test failed: {}".format(e))
    except KeyboardInterrupt:
        log.info("Test interrupted by user")
        if 'serial_conn' in locals():
            serial_conn.stop() 