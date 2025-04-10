import sys
# Import the UDP client class from python-osc
from pythonosc import udp_client

# --- Configuration ---
# Set the IP address of the computer/application receiving the OSC messages
# Use "127.0.0.1" if it's running on the same machine (localhost)
TARGET_IP = "10.0.0.11"

# Set the port number the receiving application is listening on
TARGET_PORT = 7000 # Example port, change if needed

# --- Define Menu Options and corresponding OSC messages ---
# We use a dictionary where:
# key = The number the user will type (as a string)
# value = A tuple containing: (OSC address path, argument(s) to send)
# Note: The argument '1' is sent as an integer here.
menu_items = {
    "1": ("/props/phone/start", 1),
    "2": ("/props/phone/stop", 1)
    # You can easily add more options here later:
    # "3": ("/some/other/command", "hello"),
    # "4": ("/settings/volume", 0.75),
}

# Define the choice number for exiting the application
EXIT_OPTION = "0"

# --- OSC Sending Function ---
def send_osc_message(client, osc_address, osc_arguments):
    """
    Sends an OSC message using the provided client, address, and arguments.
    Includes basic error handling and confirmation printing.

    Args:
        client (udp_client.SimpleUDPClient): The OSC client instance.
        osc_address (str): The OSC address path (e.g., '/props/phone/start').
        osc_arguments: The argument(s) to send with the message.
                       Can be a single value or a list/tuple for multiple args.
    """
    try:
        # The send_message method takes the address path and the value(s).
        # It handles single values or lists/tuples automatically.
        client.send_message(osc_address, osc_arguments)

        # Print confirmation (using .format() for compatibility)
        print("\n-------------------------")
        print("  OSC Message Sent!")
        # Note: client._address and client._port are internal, using constants is safer
        print("  Target:  {}:{}".format(TARGET_IP, TARGET_PORT))
        print("  Address: {}".format(osc_address))
        print("  Args:    {}".format(osc_arguments))
        print("-------------------------\n")

    except Exception as e:
        # Print error message (using .format() for compatibility)
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("  Error Sending OSC Message:")
        print("  Target:  {}:{}".format(TARGET_IP, TARGET_PORT))
        print("  Address: {}".format(osc_address))
        print("  Args:    {}".format(osc_arguments))
        print("  Error:   {}".format(e))
        print("!!!!!!!!!!!!!!!!!!!!!!!!!\n")

# --- Main Application Logic ---
def main_menu():
    """Runs the main menu loop for the OSC sender application."""

    print("--- Mini OSC Sender App ---")
    print("Targeting OSC Server at: {}:{}".format(TARGET_IP, TARGET_PORT))

    # Create the OSC client instance
    try:
        osc_client = udp_client.SimpleUDPClient(TARGET_IP, TARGET_PORT)
        print("OSC Client ready.")
    except Exception as e:
        print("\n*** FATAL ERROR: Could not create OSC client: {} ***".format(e))
        print("*** Please check network configuration and permissions. ***")
        sys.exit(1) # Exit the script if client fails

    # Start the main loop
    while True:
        # Display the menu options
        print("\n--- Select an OSC message to send ---")
        for key, (address, args) in menu_items.items():
            print("  {}. Send: {} {}".format(key, address, args))
        print("-------------------------------------")
        print("  {}. Exit Application".format(EXIT_OPTION))
        print("-------------------------------------")

        # Get input from the user
        choice = input("Enter your choice: ")

        # Check if the user wants to exit
        if choice == EXIT_OPTION:
            print("Exiting...")
            break # Break out of the while loop

        # Check if the choice is in our defined menu items
        elif choice in menu_items:
            # Get the address and arguments for the chosen menu item
            osc_addr, osc_args = menu_items[choice]
            # Send the message
            send_osc_message(osc_client, osc_addr, osc_args)

        # Handle invalid input
        else:
            print("\n*** Invalid choice '{}'. Please try again. ***".format(choice))

    print("Application finished.")

# --- Run the application ---
if __name__ == "__main__":
    main_menu()