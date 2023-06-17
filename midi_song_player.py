import time
#external deps
import json
import mido
from transitions import Machine 
#meatmuddy code
from midi_loop_player import MidiLoop
from playinfo import PlayInfo as PlayInfo
from playinfo import VisualizePlayInfo as VisualizePlayInfo          # for cli prints
from playinfo import VisualizePlayInfoWaveshareOLED as VisualizePlayInfoWaveshareOLED # for epaper screen
# config file   
from meatmuddy_config import command_notes as command_notes
from meatmuddy_config import command_cc as command_cc
from meatmuddy_config import command_method as command_method

#import threading
#from queue import Queue
#midi_queue = Queue()

# def read_midi_input():
#     with mido.open_input('f_midi') as midi_input:
#         for msg in midi_input:
#             # Put the MIDI message into the queue
#             midi_queue.put(msg)

# def process_midi_messages():
#     while True:
#         # Get the MIDI message from the queue (blocks if the queue is empty)
#         msg = midi_queue.get()

#         # Process the MIDI message
#         # Your processing code here...

#         # Mark the MIDI message as processed
#         midi_queue.task_done()



#load config
def get_swap_dict(d):
    return {v: k for k, v in d.items()}

notes_command = get_swap_dict(command_notes)
cc_command = get_swap_dict(command_cc)

# just a container for bunch of bool flags for song controls.
class SongFlags:
   
    def __init__(self):

        #command flags
        self.prev = False       # previous part scheduled
        self.next = False       # Indicates if next part is scheduled
        self.fill = False       # Indicates if fill is scheduled
        self.startstop = False  # startstop is scheduled

        self.end_of_midi_loop = False
         
class MidiSong:

    #state machine 

    # using the same transition function for everything as a shorthand. Not exactly the textbook state machine.
    def tr(self, ** params):  
        self.machine.add_transition(trigger='sm_loop', **params)

  
    def setup_state_machine(self):
 
        self.states =  ["idle", "playing_intro", "playing_outro",  "playing_groove", "playing_fill"]
        self.machine = Machine(model=self, states=self.states, initial='idle')

        # Add transitions which describe logic of switching between states.
        # Order matters, as transition rules seem to be checked in the same order as added.  
        # This means a lot for overlapping rules, more narrow rule should be defined before more "generic" one.

        # we can achive same using "unless" more exactly. 
        self.tr( source='idle', dest='playing_intro',            conditions= ['flag_startstop', 'c_song_has_intro'], after = 'clean_flags')
        self.tr( source='idle', dest='playing_groove',           conditions=['flag_startstop','c_song_no_intro'], after = 'clean_flags')

        self.tr( source='playing_intro',  dest='idle',           conditions=['flag_end_of_midi_loop','flag_startstop'], after = ['clean_flags','reset_indexes']) # to stop a falsestart
        self.tr( source='playing_intro',  dest='playing_groove', conditions=['flag_end_of_midi_loop'], after = 'clean_flags')
                
        self.tr( source='playing_groove', dest='playing_fill',   conditions=['flag_fill','c_it_is_fill_time','c_part_has_fills','flag_next'], after = ['clean_flags_but_next' ]) 
        self.tr( source='playing_groove', dest='playing_fill',   conditions=['flag_fill','c_it_is_fill_time','c_part_has_fills'], after = ['clean_flags_but_next']) 
        
        self.tr( source='playing_groove', dest='playing_outro',  conditions=['flag_end_of_midi_loop','flag_startstop','c_song_has_outro'], after = 'clean_flags')                                                                                                               
        self.tr( source='playing_groove', dest='idle',           conditions=['flag_end_of_midi_loop','flag_startstop','c_song_no_outro' ], after = ['clean_flags','reset_indexes' ])  
        
        # processing switch to next groove, both from fill and groove
        self.tr( source='playing_groove', dest='playing_groove', conditions=['flag_end_of_midi_loop', 'flag_next' ], after = 'next_part') 

        self.tr( source='playing_fill',   dest='playing_outro',  conditions=['flag_end_of_midi_loop', 'flag_startstop', 'c_song_has_outro' ], after = 'clean_flags')  
        self.tr( source='playing_fill',   dest='idle',           conditions=['flag_end_of_midi_loop', 'flag_startstop', 'c_song_no_outro' ], after = 'clean_flags')  

        self.tr( source='playing_fill',   dest='playing_groove', conditions=['flag_end_of_midi_loop', 'flag_next' ], after = 'next_part')  
        self.tr( source='playing_fill',   dest='playing_groove', conditions=['flag_end_of_midi_loop'], after = 'next_fill')  # returning to the same groove

        self.tr( source='playing_outro',  dest='idle',           conditions=['flag_end_of_midi_loop'], after = ['clean_flags', 'reset_indexes'])
    
    def reset_indexes(self):
        self.current_part_index = 0
        self.fill_index =  0
        
    def next_part(self):
        self.current_part_index =  (self.current_part_index + 1) % len(self.song_parts)
        self.fill_index =  0
        self.clean_flags()

    def prev_part(self):
        self.current_part_index =  (self.current_part_index - 1) % len(self.song_parts)
        self.fill_index =  0
        self.clean_flags()
    
    def next_fill(self):
        self.fill_index =  (self.fill_index + 1) % len(self.get_current_part().fills)
        self.clean_flags()

    # clean flags when changing state.
    def clean_flags(self):
        self.flag.prev = False
        self.flag.next = False
        self.flag.fill = False
        self.flag.startstop = False
        self.flag.end_of_midi_loop = False

    # a bit different cleaning for the case when fill comes in between the moment when we press next and the moment when actual "next" would happen.
    # and same for startstop.
    def clean_flags_but_next(self):
       # self.flag.prev = False
       # self.flag.next = False
        self.flag.fill = False
       # self.flag.startstop = False
        self.flag.end_of_midi_loop = False

    # condition functions 
    def flag_prev(self):
        return self.flag.prev
    
    def flag_next(self):
        return self.flag.next
    
    def flag_fill(self):
        return self.flag.fill
    
    def flag_startstop(self):
        return self.flag.startstop
    
    def flag_end_of_midi_loop(self):
         return self.flag.end_of_midi_loop
    
    #intro
    def c_song_has_intro(self):
        return self.intro is not None

    def c_song_no_intro(self):
        return self.intro is None
    #outro
    def c_song_has_outro(self):
        return self.outro is not None

    def c_song_no_outro(self):
        return self.outro is None
    
    def c_part_has_fills(self):
        return bool(len(self.get_current_part().fills))
        
    def c_it_is_fill_time(self):
        if len(self.get_current_part().fills):
           # print(f"filltime   {self.get_current_part().ticks_left_to_end }   {self.get_current_part().fills[self.fill_index].loop_length_in_ticks}")
            return self.get_current_part().ticks_left_to_end  < self.get_current_part().fills[self.fill_index].loop_length_in_ticks
        else:
            return False  # it's never time to play fill if there are no fills.


    def __init__(self, input_port, output_port, song_json):

        self.flag=SongFlags()   # command flags grouped in one place
        self.setup_state_machine()      # main hub for setting logic between states
        self.play_info = PlayInfo()     # set of data for UI extracted from loops and other places.
       # self.viz = VisualizePlayInfo()  # realtime printouts of that info.  #TBA support for waveshare displays. 
    
        self.viz = VisualizePlayInfoWaveshareOLED()  # realtime printouts of that info.  #TBA support for waveshare displays. 
        # midi ports 
        self.input_port = input_port    
        self.output_port = output_port

        # song structure data    
        self.intro = None
        self.outro = None
        self.song_parts = []

        # state
        self.current_part_index = 0   # index for cycling through grooves
        self.fill_index = 0           # Index for cycling through fills
        
        # place to store input cc/notes for controlling drum machine
        self.input_commands_queue =  []
        self.load_song()   
        print("Finished loading")

    def load_song(self):  #tba some error handling?
        
        self.song_data = json.loads(song_json)
        self.intro = self.create_midi_loop(self.song_data["intro"]["groove"])
        self.outro = self.create_midi_loop(self.song_data["outro"]["groove"])
   
        for part in self.song_data["song_parts"]:
            midi_part = self.create_midi_loop(part["groove"])
            midi_part.fills = [self.create_midi_loop(fill) for fill in part["fills"]]   
            self.song_parts.append(midi_part)

    def create_midi_loop(self, file):
        if file is None:
            return None
        else:
            midi_loop = MidiLoop(  self.output_port)
            midi_loop.load_file(file)
        return midi_loop

    def get_current_part(self):
        return self.song_parts[self.current_part_index]
    
    def get_current_part_fill(self):
        return self.song_parts[self.current_part_index].fills[self.fill_index]

    def process_commands(self): # processing commands one per cycle.   #tba - consider running it alltogether? why spread?
        if self.input_commands_queue:
            command = self.input_commands_queue.pop(0)  
            print(f"incoming command: {command}")

            if command == "prev":
                print("command prev part")
                self.flag.prev = True
              
            elif command == "next":
                print("command next part")
                self.flag.next = True
                 
            elif command == "fill":
                print("command insert fill")
                self.flag.fill = True

            elif command ==  "startstop" :    
                print("command start/stop received")
                self.flag.startstop = True
            else:
                print("unknown command")
    
    def get_play_info(self):
        self.play_info.fill_scheduled      =  self.flag.fill
        self.play_info.next_part_scheduled =  self.flag.next
        self.play_info.prev_part_scheduled =  self.flag.prev
        self.play_info.startstop_scheduled =  self.flag.startstop
        self.play_info.state = self.state
        # tba  - i do not like that other parts of updating play info data is scattered all over the place
        return self.play_info       

    def extract_command_messages(self, input_messages):

        if command_method == "notes":
            for msg in input_messages:
                if  msg.type == "note_on" :  # stupid ableton has broken cc stuff, using notes for now. TBA - replace with CC.
                    print(msg)
                    try:
                        self.input_commands_queue.append( notes_command [msg.note])
                        print(self.input_commands_queue)
                    except: # ignore irrelevant notes
                        pass

        elif command_method =="cc":
            for msg in input_messages:
                if msg.type == "control_change":          
                    print(msg)
                    try:
                        self.input_commands_queue.append(cc_command[msg.control])
                        print(self.input_commands_queue)
                    except:  #ignore irrelevant control messages
                        pass
        else:
            raise ValueError("no command method choosen")

    def extract_viz_data_from_loop(self, loop):
        self.play_info.beat_number = loop.current_beat_number  ##
        self.play_info.total_beat_numbers = len( loop.beats_absolute_time_ticks)
        self.play_info.file_name = loop.file_name
        self.play_info.song_part_number = self.current_part_index
        self.play_info.fill_number = self.fill_index


        self.play_info.total_song_part_numbers = len(self.song_parts)  #TBA i should not get this info on each loop.
        try:
            self.play_info.total_fill_numbers = len( loop.fills)   #TBA i should not get this info on each loop.
        except:
            self.play_info.total_fill_numbers = "x"
    
    
    def play(self):
         
        while True:
            start_time = time.process_time()
            
            # input_midi_messages =  [ ]
            # while not midi_queue.empty():
            #      input_midi_messages.append(midi_queue.get())
            #      midi_queue.task_done()
                
            # input_midi_messages = []
  
            # if   not midi_queue.empty():
            #     input_midi_messages.append(midi_queue.get())
            #     midi_queue.task_done()
            input_midi_messages = list(self.input_port.iter_pending()) # getting list of input message  got from midi port since the last loop. 
      

            self.extract_command_messages(input_midi_messages)
            self.process_commands()
 
            if self.state == "idle" :
                midi_queue.queue.clear()
                pass

            elif self.state == "playing_intro" :
               self.flag_end_of_midi_loop = self.intro.play(input_midi_messages)
               self.extract_viz_data_from_loop(self.intro)

            elif self.state == "playing_groove":
                self.flag_end_of_midi_loop = self.get_current_part().play(input_midi_messages)
                self.extract_viz_data_from_loop(self.get_current_part())

                # to cover a case when user requests fill later then it was actually best to start,  we play fill silently in parallel.
                # this way, when we actualy trigger playing fill, it already would be in sync with main groove, and can be played as a drop in replacement
               # print(".")
                if self.c_it_is_fill_time():
                    self.get_current_part_fill().play(input_midi_messages, dry_run = True) 

                if self.flag_end_of_midi_loop:  # handling rewind separatly due to no guarantee that both loops would end in the same time
                    self.get_current_part().rewind()        #TBA check rewind  time precision
                    self.get_current_part_fill().rewind()              
        
            elif self.state == "playing_fill":
               
               self.get_current_part_fill().play(input_midi_messages)

               # calculate ending by the playing main groove silently.
               # Less resource effective but more realible for keeping timing strict, to my guess.
               self.flag_end_of_midi_loop = self.get_current_part().play(input_midi_messages, dry_run= True) 
               self.extract_viz_data_from_loop(self.get_current_part_fill())
               
               if self.flag_end_of_midi_loop:  #handling rewind separatly due to no guarantee that both loops would end in the same time
                   self.get_current_part().rewind()        #TBA check rewind  time precision
                   self.get_current_part_fill().rewind()

            elif self.state ==  "playing_outro":
               self.flag_end_of_midi_loop = self.outro.play(input_midi_messages)
               self.extract_viz_data_from_loop(self.outro)
            else:
                raise ValueError(f"unknown state {self.state} quitting.")
                exit()
            self.viz.visualize(self.get_play_info())
            self.sm_loop()
            
            end_time = time.process_time()
            execution_time = end_time - start_time
           # time.sleep(0.005)
           # print(execution_time*1000)

            
def main():
    # init  midi ports.
    input_port_name = "f_midi"
    output_port_name = "f_midi"

    output_port = mido.open_output(output_port_name)
    input_port = mido.open_input(input_port_name)

    song_path="songs_lib/grm_retrofunk_song.json"
    #song_path="songs_lib/grm_dnb152.json"

    # midi_thread = threading.Thread(target=read_midi_input)
    # midi_thread.start()

    with open(song_path, "r") as file:
        song_json = file.read()

    song = MidiSong(input_port, output_port, song_json)
    song.play()

if __name__ == "__main__":
    main()