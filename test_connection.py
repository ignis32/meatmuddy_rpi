import time
import mido
from mido import Message

# Define the MIDI input and output ports
input_port = "f_midi"
output_port = "f_midi"

# Define the MIDI clock message type
clock_message_type = "clock"

# Define the hi-hat note number and velocity
hihat_note = 42
hihat_velocity = 100

# Create MIDI input and output objects
input_midi = mido.open_input(input_port)
output_midi = mido.open_output(output_port)

# Variable to keep track of the quarter note count
quarter_note_count = 0


def process_midi():
    global quarter_note_count
    
    # Check if there are any incoming MIDI messages
    if input_midi.poll():
        # Read the next available MIDI message
        message = input_midi.receive()
        
        # Check if the received message is a clock message
        if message.type == clock_message_type:
            #print(message)
            
            # Increment the quarter note count
            
            quarter_note_count += 1
        #    print(f"- {quarter_note_count}")
            # Check if it's a quarter note (every 24 MIDI clock ticks for standard MIDI clocks)
            if (quarter_note_count - 1) % 12 == 0:
                
                # Construct the hi-hat note-on message
                hihat_message = Message("note_on", note=hihat_note, velocity=hihat_velocity)
               #print(hihat_message)
                # Send the hi-hat message to the output port
              #  output_midi.send(hihat_message)
        else:
            print(message)

# Process MIDI messages and do other tasks
while True:
    process_midi()
   # print("uncoupled")
    