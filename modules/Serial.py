import serial
import logging
import os
import threading
import time

logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))
log = logging.getLogger("SERIAL")

class Serial:
    def __init__(self, port='/dev/tty.usbserial-1160', baud_rate=9600):
        """Initialize serial connection with configurable port and baud rate."""
        log.debug("Initializing serial connection on port {} at {} baud".format(port, baud_rate))
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.running = False
        self.reader_thread = None
        self.connect()
    
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
        # Initialize serial connection
        log.info("Starting Serial test")
        serial = Serial(port='/dev/tty.usbserial-1160', baud_rate=9600)
        
        # Wait for Arduino to initialize
        time.sleep(2)
        
        # Test light control
        log.info("Testing light control...")
        serial.light_on()
        time.sleep(2)  # Wait to see the effect
        serial.light_off()
        time.sleep(2)  # Wait to see the effect
        
        # Test smoke control
        log.info("Testing smoke control...")
        serial.smoke_on()
        time.sleep(2)  # Wait to see the effect
        serial.smoke_off()
        time.sleep(2)  # Wait to see the effect
        
        # Test both together
        log.info("Testing combined control...")
        serial.light_on()
        serial.smoke_on()
        time.sleep(2)  # Wait to see the effect
        serial.light_off()
        serial.smoke_off()
        time.sleep(1)  # Wait to see the effect
        
        # Clean up
        log.info("Closing connection...")
        serial.stop()
        log.info("Test completed successfully")
        
    except serial.SerialException as e:
        log.error("Test failed: {}".format(e))
    except KeyboardInterrupt:
        log.info("Test interrupted by user")
        if 'serial' in locals():
            serial.stop() 