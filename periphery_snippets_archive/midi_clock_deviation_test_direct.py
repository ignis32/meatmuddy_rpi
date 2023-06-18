import os
import time


source_tempo_known  = 120

clock_ticks = 0
start_time = time.time()
max_positive_deviation = 0
max_negative_deviation = 0
count_before_deviate = 0

def handle_clock():
    global clock_ticks, start_time, max_positive_deviation, max_negative_deviation, count_before_deviate
    count_before_deviate += 1

    clock_ticks += 1

    if clock_ticks == 24:
        elapsed_time = time.time() - start_time
        tempo_bpm = (60 / elapsed_time)  
        if count_before_deviate > 200:
            deviation = tempo_bpm - source_tempo_known

            if deviation > max_positive_deviation:
                max_positive_deviation = deviation

            if deviation < max_negative_deviation:
                max_negative_deviation = deviation

        print("Tempo: {:.2f} BPM".format(tempo_bpm))
        print("Max Positive Deviation: {:.2f} BPM".format(max_positive_deviation))
        print("Max Negative Deviation: {:.2f} BPM".format(max_negative_deviation))

        # Reset the counters
        clock_ticks = 0
        start_time = time.time()


midi_device = "/dev/midi1"

# Open the MIDI device file
with open(midi_device, "rb") as midi_file:
    while True:
        # Read a single byte from the MIDI device
        byte = midi_file.read(1)
        
        if not byte:
            break  # No more data to read

        # Convert the byte to an integer
        value = ord(byte)

        if value == 0xF8:  # MIDI Clock event
            handle_clock()
