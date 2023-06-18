import mido
import time
import os
import RateLimiter  

source_tempo_known = 120

clock_ticks = 0
start_time = time.perf_counter()  # using time.perf_counter() for better resolution

max_positive_deviation = 0
max_negative_deviation = 0
count_before_deviate = 0

last_clock_arrived_at = time.perf_counter()
max_clock_length_ms = -99999999
min_clock_length_ms =  99999999

def handle_clock():
    global clock_ticks, start_time, max_positive_deviation, max_negative_deviation, count_before_deviate,last_clock_arrived_at,max_clock_length_ms, min_clock_length_ms
     
   
    count_before_deviate += 1

    # clock_ticks += 1
    
    # #calculate bpm  and deviations

    # if clock_ticks == 6:
    #     elapsed_time = time.perf_counter() - start_time  # using time.perf_counter() here as well
    #     tempo_bpm = (60 / elapsed_time) / 4
        
    #     if count_before_deviate > 200 :
    #         deviation = tempo_bpm - source_tempo_known
            
    #         if deviation > max_positive_deviation:
    #             max_positive_deviation = deviation
            
    #         if deviation < max_negative_deviation:
    #             max_negative_deviation = deviation
    #         # Reset the counters
    #         clock_ticks = 0
    #         start_time = time.perf_counter()  # using time.perf_counter() here as well
    #         print("Tempo: {:.2f} BPM".format(tempo_bpm))
    #         print("Max Positive Deviation: {:.2f} BPM".format(max_positive_deviation))
    #         print("Max Negative Deviation: {:.2f} BPM".format(max_negative_deviation))

    # calculate clock time drift
    new_clock_arrived_at =  time.perf_counter()
    clock_diff = new_clock_arrived_at - last_clock_arrived_at
    last_clock_arrived_at = new_clock_arrived_at

    if count_before_deviate > 200 :   
        max_clock_length_ms = max(max_clock_length_ms, clock_diff*1000)    
        min_clock_length_ms = min(min_clock_length_ms, clock_diff*1000)      
            
        
        print("Max clock length  : {:.2f} ms".format(max_clock_length_ms))
        print("Min clock length  : {:.2f} ms".format(min_clock_length_ms))
        

# Get a list of available MIDI input ports
input_ports = mido.get_input_names()

# Print the list of available ports
print("Available MIDI input ports:")
for port in input_ports:
    print('------')
    print(port)

def test_with_constant_read():
    with mido.open_input('f_midi') as inport:
        
        # Set up a callback function to handle incoming MIDI messages
        for message in inport:
            if message.type == 'clock':
                handle_clock()

def non_blocking_read(input_port):
    input_messages = list(input_port.iter_pending())

    if len (input_messages) > 1:
        print(f"{len(input_messages)} clocks at once")
    for message in input_messages:
        if message.type == 'clock':
            handle_clock()


    

def test_non_blocking_read():
    with mido.open_input('f_midi') as inport:
        #rate limiter
        rate_limiter=RateLimiter.RateLimiter(interval=0.007, function_name ="tst non blocking")
        
        while True:
            rate_limiter.start_cycle()
            
            non_blocking_read(inport)
          
            rate_limiter.end_cycle()
# Uncomment the method you want to use:

#os.nice(20)
# test_with_constant_read()
test_non_blocking_read()