import mido
from mido import MidiFile
import math
import time

from   mm_config  import mm_path as mm_config_path

class NoteTracker:  #class for tracking open notes. Allows us to close them with note_off in the end of the loop.

    def __init__(self):
        self.currently_playing_notes = {}

    def process_msg(self, msg):
        if msg.type == 'note_on':
            self.note_on(msg)
        elif msg.type == 'note_off':
            self.note_off(msg)

    def note_on(self, msg):
        key = (msg.channel, msg.note)
        if msg.velocity > 0:
            self.currently_playing_notes[key] = msg
        elif msg.velocity == 0 and key in self.currently_playing_notes:
            del self.currently_playing_notes[key]

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

class MidiPlayer:

    def __init__(self, output_port, input_port):
        self.output_port = output_port
        self.input_port = input_port
        self.midi_file = None
        self.midi_gens = []
        self.current_msgs = []
        self.tick_counters = []
        self.abs_tick_counters = []
        self.ticks_per_clock = 0
        self.max_drift = 0
        self.note_tracker = NoteTracker() # keep track of the notes so we can close them in the end of the loop
        self.num_tracks_ended = []
 


    def stop_all_notes(self):
        notes_off = self.note_tracker.get_all_notes_off()
        for msg in notes_off:
            print(f"closing unclosed note  {msg}")
            self.output_port.send(msg)

    def detect_beats_per_bar(self,mid):
        # default to 4/4 time if no time_signature message is found
        numerator = 4
        denominator = 4
        # find the time_signature message, if it exists
        for i, track in enumerate(mid.tracks):
            for msg in track:
                if msg.type == 'time_signature':
                    numerator = msg.numerator
                    denominator = msg.denominator
                    break  # assuming only one time_signature event
            #if beats_per_bar != 4:
             #   break  # stop searching after we found the time_signature
        
        beats_per_bar = numerator   * (4  / denominator)

        print(f"detected beats per bar {beats_per_bar}")
        
        return   beats_per_bar  

    def fix_eot_to_bar(self, mid):
        beats_per_bar = self.detect_beats_per_bar(mid)  # for 4/4 time
        bar_length_ticks = beats_per_bar * mid.ticks_per_beat

        # find the last note_off event across all tracks
        last_note_off_time = 0
        last_track_index = -1
        for i, track in enumerate(mid.tracks):
            track_time = 0
            for msg in track:
                track_time += msg.time  # MIDO uses relative time, so we sum it up
 
                if msg.type == 'note_off' or (msg.type == 'note_on'): # and msg.velocity == 0): # any note will do
                    if track_time > last_note_off_time:
                        last_note_off_time = track_time
                        last_track_index = i

        # calculate the next bar time in ticks
        num_bars = last_note_off_time // bar_length_ticks
        if last_note_off_time % bar_length_ticks != 0:
            num_bars += 1
        next_bar_time = num_bars * bar_length_ticks
        print(f"next bar {next_bar_time}")

        # find the end_of_track event in the track with the last note and replace it
        track = mid.tracks[last_track_index]
        for msg in track:
            if msg.type == 'end_of_track':
                # add the extra time to the end_of_track event
                msg.time += next_bar_time - last_note_off_time
                print(f"fixed ending {msg.time}")
                break  # assuming only one end_of_track event per track

    def load_file(self, midi_file_path):
        start_time = time.time() 
        self.midi_file = MidiFile(midi_file_path)
       # print(self.midi_file)
        # Iterate over all tracks
        for i, track in enumerate(self.midi_file.tracks):
         
            # Iterate over all messages in the current track
            for msg in track:
                # Check if the message is a meta message
                if msg.type not in ['note_on', 'note_off']:
                    print(f"Meta message: {msg}")
         
       
        self.fix_eot_to_bar(self.midi_file)
         
       # print(self.midi_file)
        self.ticks_per_beat = self.midi_file.ticks_per_beat
        self.ticks_per_clock = self.ticks_per_beat / 24  # Default value for time division is 24
        self.rewind()

        end_time = time.time()  # Store the end time
        print(f"'load_file' execution time: {end_time - start_time} seconds")
    
    def rewind(self):
        start_time = time.time() 
        self.midi_gens = [iter(track) for track in self.midi_file.tracks]
        self.current_msgs = [next(gen) for gen in self.midi_gens]  # load first messages
        self.tick_counters = [ 0 for _ in self.midi_gens] # compensate for having increment in the begining of play
        self.abs_tick_counters = [0 for _ in self.midi_gens]  #debug
        self.num_tracks_ended = [False for _ in self.midi_gens ] # all tracks are playing   # Keep track of the number of tracks that have ended

        
        print(f"ticks per beat {self.ticks_per_beat}")
        print(f"ticks per clock {self.ticks_per_clock}")
        end_time = time.time()  # Store the end time
        print(f"'rewind' execution time: {end_time - start_time} seconds")

         
        
    def play(self):
        # iterate all incoming midi stuff in input  buffer
        for msg in self.input_port.iter_pending():
            if msg.type == 'clock':
                 for i in range(len(self.midi_gens)):  # iterate tracks
                  
                    if self.num_tracks_ended[i]:  # do not process this track if we are done with it
                        continue

                    self.tick_counters[i] += self.ticks_per_clock
                    self.abs_tick_counters[i] += self.ticks_per_clock  #debug
                    
                    LOOKAHEAD_OFFSET=  self.ticks_per_clock/2 # for a small lookahead for smoother play

                    # we process all message which are in the past or near ahead current clock.
                    while self.tick_counters[i] >= self.current_msgs[i].time  - LOOKAHEAD_OFFSET:  
                        
                        # drift = self.tick_counters[i]-self.current_msgs[i].time  #debug
                        # self.max_drift = max(self.max_drift, drift) #debug
                        # print(f"how late: {drift}  max {self.max_drift} self.num_tracks_ended {self.num_tracks_ended}  ") 

                        if self.current_msgs[i].type == 'end_of_track':
                            print(f"end of track {i} on {self.abs_tick_counters[i]}")
                            self.num_tracks_ended[i] = True
                            if all(self.num_tracks_ended):  ### if all tracks stopped, its a loop end
                                return False # report loop end
                            break # otherwise
                        
                        # if it is a note/cc send it
                        if not self.current_msgs[i].is_meta:
                            print(self.current_msgs[i])
                            self.note_tracker.process_msg(self.current_msgs[i])
                            self.output_port.send(self.current_msgs[i])
                             

                        self.tick_counters[i] -= self.current_msgs[i].time
                      
                        try:
                            self.current_msgs[i] = next(self.midi_gens[i])
                        except StopIteration:
                            print(".")
                            pass
                            # self.num_tracks_ended += 1
                            # if self.num_tracks_ended == len(self.midi_gens):
                            #     return False
                            # break
        return True

# Example usage
output_port_name = 'f_midi'
input_port_name = 'f_midi'
output_port = mido.open_output(output_port_name)
input_port = mido.open_input(input_port_name)

player = MidiPlayer(output_port, input_port)
#player.load_file('6-8.mid')
player.load_file('file.mid')
#player.load_file('able68.mid')
#player.load_file('hhat2.mid')
path=mm_config_path
player.load_file(path)
while True:
     
    #print("loop cycle")
    
  
    still_playing = player.play()
    if not still_playing:
        print("RELOAD")
        player.stop_all_notes()
        player.rewind()
        
    #time.sleep(0.1)


# Close the ports when finished
print("close ports")
output_port.close()
input_port.close()
