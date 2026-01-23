import tkinter as tk
from pylsl import StreamInfo, StreamOutlet, IRREGULAR_RATE
import time
import threading
from pynput import keyboard

# Global variable to hold the last pressed number
last_number = 0  # Default to 0

# Function to handle key presses
def on_press(key, number_var):
    global last_number
    try:
        if key.char in '12345':
            last_number = int(key.char)
            number_var.set(f"Current number: {last_number}")
            print(f"Last number updated to: {last_number}")
    except AttributeError:
        pass  # Ignore non-character keys

# Function to stream the last number indefinitely
def stream_thread():
    # Create LSL stream info
    info = StreamInfo('LastNumberStream', 'Markers', 1, IRREGULAR_RATE, 'int32', 'lastnumberid')
    outlet = StreamOutlet(info)
    
    print("LSL stream started. Press 1-51223 anywhere (global capture) to indicate engagement level.")
    
    while True:
        # Push the current last_number as a sample
        outlet.push_sample([last_number])
        time.sleep(0.1)  # Stream at 10 Hz; adjust as needed

# Main function to set up GUI and start streaming
def main():
    # Create GUI window
    root = tk.Tk()
    root.title("Number Input (0-5)")
    root.geometry("300x200")
    
    instruction_label = tk.Label(root, text="Press keys 1-5 anywhere to indicate engagement level.\n(Global keyboard capture active.)")
    instruction_label.pack(pady=20)
    
    number_var = tk.StringVar()
    number_var.set("Current number: 0")
    number_label = tk.Label(root, textvariable=number_var, font=("Arial", 24))
    number_label.pack(pady=20)
    
    # Start the keyboard listener
    listener = keyboard.Listener(on_press=lambda key: on_press(key, number_var))
    listener.start()
    
    # Start the streaming thread
    threading.Thread(target=stream_thread, daemon=True).start()
    
    root.mainloop()

def start_user_rating_stream():
    main()