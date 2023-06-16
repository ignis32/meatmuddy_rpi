import time
import mido
from mido import Message

# Define the MIDI input and output ports
input_port_name = "f_midi"

# Define the MIDI clock message type
clock_message_type = "clock"


# Create MIDI input and output objects
input_port = mido.open_input(input_port_name)


def process_midi():
    global input_midi
    input_messages = list(input_port.iter_pending())
    # Check if there are any incoming MIDI messages

    clock_messages_count = 0
    for msg in input_messages:
          if msg.type == 'clock':
            clock_messages_count += 1

            if clock_messages_count > 1:
                print (input_messages)
                print(f"!!!!!!!!!!!! There are more than one message with type 'clock' {clock_messages_count} in the list. We are failing to keep up")
            


    for message in  input_messages:
        lock_messages_count=0
                 
        # Check if the received message is a clock message
        if message.type == clock_message_type:
            print(".",  end="", flush = True)            
        else:
            print()
            print(message)
    time.sleep(0.018)
# Process MIDI messages and do other tasks
while True:
    process_midi()
   # print("uncoupled")
    