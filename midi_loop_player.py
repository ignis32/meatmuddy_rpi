import mido
from mido import MidiFile
import math
import time
import os
 

# decorator for function execution time measurement 
def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} execution time: {execution_time/1000} milliseconds")
        return result
    return wrapper

class NoteTracker:
    def __init__(self):
        self.currently_playing_notes = {}

    def process_msg(self, msg):
        if msg.type == 'note_on':
            if msg.velocity > 0:
                self.note_on(msg)
            else:
                self.note_off(msg)  # zero velocity note_on counts for note_off
        elif msg.type == 'note_off':
            self.note_off(msg)
            
    def note_on(self, msg):
        key = (msg.channel, msg.note)
        self.currently_playing_notes[key] = msg
        
    def note_off(self, msg):
        key = (msg.channel, msg.note)
        if key in self.currently_playing_notes:
            del self.currently_playing_notes[key]
            
    def get_all_notes_off(self): 
        notes_off = []
        for key, msg in self.currently_playing_notes.items():
            new_msg = mido.Message('note_off', channel=msg.channel, note=msg.note)
            notes_off.append(new_msg)
        self.currently_playing_notes.clear()
        return notes_off

class TimeSignature:
    def __init__(self, numerator=4, denominator=4):
        self.numerator = numerator
        self.denominator = denominator


class MidiLoop:

    def __init__(self, input_port,output_port):
        self.time_signature = TimeSignature(4,4)
        self.output_port = output_port
        self.input_port = input_port
        self.midi_file = None # mido object
        self.note_tracker = NoteTracker() # keep track of the notes so we can close them in the end of the loop
   
        # per track stuff
        self.midi_gens = []   
        self.current_msgs = [] 
        self.tick_counters = []
        
        self.num_tracks_ended = []   # keep track of the ended track, to end loop when all tracks are done. Pun non intended.
        
        # per loop stuff
        self.current_beat_number = 0
        self.abs_tick_counter = 0

        # loop information
        self.ticks_per_quarter_note = None
        self.ticks_per_clock = None
        self.quarter_notes_per_bar = None

        #
        self.time_signature = TimeSignature(4,4)

        # communication with midi song
        self.loop_length_in_ticks =0
        self.ticks_left_to_end = None
        self.command_messages_stack= None
         
    def stop_all_tracked_notes(self):
        notes_off = self.note_tracker.get_all_notes_off()
        for msg in notes_off:
            print(f"closing unclosed note  {msg}")
            self.output_port.send(msg)

    def detect_quarter_notes_per_bar(self):  
        # default to 4/4 time if no time_signature message is found
         
        # find the time_signature message, if it exists
        for i, track in enumerate(self.midi_file.tracks):
            for msg in track:
                if msg.type == 'time_signature':
                     self.time_signature.numerator = msg.numerator
                     self.time_signature.denominator  = msg.denominator
                     break  # assuming only one time_signature event. 
        self.quarter_notes_per_bar = self.time_signature.numerator   * (4  /  self.time_signature.denominator)
        print(f"detected quarter_notes_per_bar { self.quarter_notes_per_bar}")    
       

    def verify_length(self):   # it appears to me that it always should pass the verification, as soon as we fix drum loop length according to clocks anyway.
                               # but I'll keep that for a while

        if  not self.loop_length_in_ticks % self.ticks_per_clock == 0:
            print(f"!!!!!!!!! MIDI loop does not fit midi clock evenly with a remaning {self.loop_length_in_ticks % 24} ticks")
        else:
            print(f"MIDI loop fits midi clock evenly into clocksks.")
            
    def fix_eot_to_bar(self):   # quantize end of track to full bar length.
        
                                                        
        bar_length_ticks = self.quarter_notes_per_bar * self.ticks_per_quarter_note

        # find the last note_off event across all tracks
        last_note_off_time = 0
        longest_track_index = -1

        for i, track in enumerate(self.midi_file.tracks):
            track_time = 0
            for msg in track:
                track_time += msg.time  # MIDO uses relative time, so we sum it up
 
                if msg.type == 'note_off' or (msg.type == 'note_on'): # and msg.velocity == 0): # any note will do
                    if track_time > last_note_off_time:
                        last_note_off_time = track_time
                        longest_track_index = i

        # calculate the next bar time in ticks
        num_bars = last_note_off_time // bar_length_ticks
        if last_note_off_time % bar_length_ticks != 0:
            num_bars += 1
        next_bar_time = num_bars * bar_length_ticks
        print(f"next bar {next_bar_time}")

        # find the end_of_track event in the track with the last note and replace it, therefore adjusting loop length.
        track = self.midi_file.tracks[longest_track_index]
        for msg in track:
            if msg.type == 'end_of_track':
                # add the extra time to the end_of_track event
                msg.time += next_bar_time - last_note_off_time
                print(f"fixed ending {msg.time}")
                self.loop_length_in_ticks=next_bar_time  # basically we've just calculated a loop length expressed in ticks.
                break  # assuming only one end_of_track event per track
        

    def print_meta_messages(self):
        # Iterate over all tracks
        for i, track in enumerate(self.midi_file.tracks): 
            # Iterate over all messages in the current track
            for msg in track:
                # Check if the message is a meta message
                if msg.is_meta:  # not in ['note_on', 'note_off']:
                    print(f"Meta message: {msg}")

    

    @measure_execution_time
    def load_file(self, midi_file_path):
        print ("\n\n")
        print(f"loading drum loop from: {midi_file_path} ")
        self.midi_file = MidiFile(midi_file_path)
        self.file_name = midi_file_path

                                                     # it is actually per quarter note     
        self.ticks_per_quarter_note = self.midi_file.ticks_per_beat
        print(f"ticks_per_quarter_note {self.ticks_per_quarter_note} ")
        self.ticks_per_clock = self.ticks_per_quarter_note / 24  # Default value for time division is 24
        print (f"ticks_per_clock {self.ticks_per_clock}")

        self.detect_quarter_notes_per_bar()
        self.fix_eot_to_bar()   # auto extend end-of-track to end of bar.
        self.verify_length()
        
        self.print_meta_messages()
        print("beats map:")
        print( self.get_beats_absolute_time_ticks())
        self.rewind() # reset iterators and time counters.
   
    @measure_execution_time
    def rewind(self):

        self.midi_gens = [iter(track) for track in self.midi_file.tracks]
        self.current_msgs = [next(gen) for gen in self.midi_gens]  # load first messages
        self.tick_counters = [ 0 for _ in self.midi_gens] # Each track has it's own relative (to previous note) time counter.
        self.abs_tick_counter = 0  # 
        self.num_tracks_ended = [False for _ in self.midi_gens ] # all tracks are playing   # Keep track of the number of tracks that have ended
    
    
    def send_msg (self,msg):

        if   msg.type in ["note_on", "note_off"]:
                          #  print(msg)
                      #      print(".")
                            self.note_tracker.process_msg(msg)
                            self.output_port.send(msg)

    def get_beats_absolute_time_ticks(self):
        
        #quarter_notes_per_bar = self.detect_quarter_notes_per_bar()  # Assuming 4/4 time signature
        print (f"quarter notes in one real beat: { 4 / self.time_signature.denominator}")
      
        ticks_per_denominator_beat = self.ticks_per_quarter_note * (4 / self.time_signature.denominator)
        print(f"ticks_per_denominator_beat { ticks_per_denominator_beat}")

        absolute_times = []
        current_time = 0
                        #<=  includes end, < does not
        while current_time <  self.loop_length_in_ticks:
            absolute_times.append(current_time)

            
            current_time += ticks_per_denominator_beat # * ( self.time_signature.numerator / self.time_signature.denominator)
        self.beats_absolute_time_ticks = absolute_times
        return absolute_times
             
    def calc_beat_number(self):
        ranges = self.beats_absolute_time_ticks
        for i, range_num in enumerate(ranges):
            if self.abs_tick_counter <= range_num:
                return i
       # If the input number is greater than the last range, return the index of the last range
        return len(ranges)   
    
    def print_beat_number(self):
        beat_number = self.calc_beat_number()
        if  not self.current_beat_number == beat_number:
            self.current_beat_number = beat_number
          #  print (f"abs tick: {self.abs_tick_counter}  ticks left: {self.loop_length_in_ticks - self.abs_tick_counter} real beat: { beat_number} / {len(self.beats_absolute_time_ticks)}  denominator {self.time_signature.denominator}th file: {os.path.basename(self.file_name)}") 

    
    def play(self, input_messages):
        self.command_messages_stack = []

        # iterate all incoming midi stuff in input  buffer
        for msg in input_messages: 
            if msg.type == 'clock':
                 
                self.abs_tick_counter  += self.ticks_per_clock   #absolute time is same for all tracks.
                self.ticks_left_to_end = self.loop_length_in_ticks - self.abs_tick_counter
                self.print_beat_number()

                for i in range(len(self.midi_gens)):  # iterate tracks
                    if self.num_tracks_ended[i]:  # do not process this track if we are done with it
                        continue

                    self.tick_counters[i] += self.ticks_per_clock
                                        
                    LOOKAHEAD_OFFSET=  self.ticks_per_clock/2 # for a small lookahead for smoother play. 
                    # we process all message which are in the past or near ahead current clock.
                    # We do not use any internal timing, our sends are just immediate reaction to the incoming midi clock              
                    while self.tick_counters[i] >= self.current_msgs[i].time  - LOOKAHEAD_OFFSET:  
                        if self.current_msgs[i].type == 'end_of_track':
                            print(f"end of track {i} on {self.abs_tick_counter }")
                            self.num_tracks_ended[i] = True
                            if all(self.num_tracks_ended):  ### if all tracks stopped, its a loop end
                                self.rewind()  # reset all the counters and recreate gens.
                                self.stop_all_tracked_notes()
                                return False # report loop end
                            break # otherwise
                        
                        self.send_msg(self.current_msgs[i])
                        # we are not zeroing time counters, because most probably we are not exactly on the
                        # time for this note, only near.
                        self.tick_counters[i] -= self.current_msgs[i].time   
                        self.current_msgs[i] = next(self.midi_gens[i])            
                           
        return True

# def main():
    
#     # init  midi ports.
#     input_port_name = 'f_midi'
#     output_port_name = 'f_midi'

#     output_port = mido.open_output(output_port_name)
#     input_port = mido.open_input(input_port_name)

#     player = MidiLoop(  input_port, output_port)

#     path="file.mid"
#     player.load_file(path)

#     while True:   
#         input_messages =  list(input_port.iter_pending() )
#         still_playing = player.play(input_messages)
#         if not still_playing:
#             print("RELOAD")
            
            
    
#     # Close the ports when finished
#     print("closinge ports")
#     output_port.close()
#     input_port.close()
