import json
import mido
from transitions import Machine 

from midi_loop_player import MidiLoop
from meatmuddy_config import command_notes as command_notes
from playinfo import PlayInfo as PlayInfo
from playinfo import VisualizePlayInfo as VisualizePlayInfo

#export
# from transitions.extensions.markup import MarkupMachine
# from transitions.extensions import GraphMachine
# import json
# import yaml

class SongFlags:
   
    def __init__(self):

        #command flags
        self.prev =      False       # previous scheduled
        self.next =      False       # Indicates if next part is scheduled
        self.fill =      False       # Indicates if fill is scheduled
        self.startstop = False  # startstop is scheduled

        self.end_of_midi_loop = False
         
class MidiSong:
    #state machine 
    def tr(self, ** params):
        self.machine.add_transition(trigger='sm_loop', **params)
        
    def setup_state_machine(self):
 
        self.states =  ["idle", "playing_intro", "playing_outro",  "playing_groove", "playing_fill"]
        self.machine = Machine(model=self, states=self.states, initial='idle')
        #self.machine = GraphMachine(model=self, states=self.states, initial='idle',show_conditions=True , use_pygraphviz=False,       )

        # Add transitions which describe logic of switching between states.
        self.tr( source='idle', dest='playing_intro', conditions= ['flag_startstop', 'c_song_has_intro'], after = 'clean_flags')
        self.tr( source='idle', dest='playing_groove', conditions=['flag_startstop','c_song_no_intro'], after = 'clean_flags')

        self.tr( source='playing_intro', dest='playing_groove', conditions=['flag_end_of_midi_loop'], after = 'clean_flags')
        self.tr( source='playing_groove', dest='playing_fill',  conditions=['flag_fill','c_it_is_fill_time','c_part_has_fills'], after = 'clean_flags') 
        self.tr( source='playing_groove', dest='playing_outro', conditions=['flag_end_of_midi_loop','flag_startstop','c_song_has_outro'], after = 'clean_flags')                                                                                                               
        self.tr( source='playing_groove', dest='idle', conditions=['flag_end_of_midi_loop','flag_startstop','c_song_no_outro' ], after = 'clean_flags')  
        
        # processing switch to next groove, both from fill and groove
        self.tr( source='playing_groove', dest='playing_groove', conditions=['flag_end_of_midi_loop', 'flag_next' ], after = 'next_part') 
        self.tr( source='playing_fill', dest='playing_groove', conditions=['flag_end_of_midi_loop', 'flag_next' ], after = 'next_part') 


        self.tr( source='playing_fill',   dest='playing_groove', conditions=['flag_end_of_midi_loop'], after = 'clean_flags')
        self.tr( source='playing_outro', dest='idle', conditions=['flag_end_of_midi_loop'], after = 'clean_flags')
    
    
    def next_part(self):
        self.current_part_index =  (self.current_part_index + 1) % len(self.song_parts)
        self.clean_flags()

    def prev_part(self):
        self.current_part_index =  (self.current_part_index - 1) % len(self.song_parts)
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
        print(bool(len(self.get_current_part().fills)))
        return bool(len(self.get_current_part().fills))
        

    def c_it_is_fill_time(self):
        return self.get_current_part().ticks_left_to_end  <= self.get_current_part().fills[self.fill_index].loop_length_in_ticks
            
    
    #self.get_graph().draw('.my_state_diagram.png', prog='dot')

    #self.to_idle()

    def __init__(self, input_port, output_port, song_json):

          
        self.flag=SongFlags()   # command flags
        self.setup_state_machine()
        self.play_info = PlayInfo()  # set of data for UI
        self.viz = VisualizePlayInfo() 
        # midi ports 
        self.input_port = input_port    
        self.output_port = output_port

        # song structure data    
        self.intro = None
        self.outro = None
        self.song_parts = []

        # state
        self.current_part_index = 0   # index for cycling throug grooves
        self.fill_index = 0  # Index for cycling through fills
        
        # place to store input cc/notes for controlling loops
        self.input_commands_queue =  []
        self.load_song()   

    def load_song(self):
        self.song_data = json.loads(song_json)

        # Tba handle absence of intro and outro
        self.intro = self.create_midi_loop(self.song_data["intro"]["groove"])
        if self.intro is not None:
            self.next_part_scheduled = True  # intro is going to  switch to first section in any case .
        else:
            self.current_part_index = 1 # if no intro, start with first groove.

        self.outro = self.create_midi_loop(self.song_data["outro"]["groove"])
   
        for part in self.song_data["song_parts"]:
            midi_part = self.create_midi_loop(part["groove"])
            midi_part.fills = [self.create_midi_loop(fill) for fill in part["fills"]]  #TBA  case with no fills. Looks like it would be  []
           # midi_part.transition = self.create_midi_loop(part["transition"])
            self.song_parts.append(midi_part)

    def create_midi_loop(self, file):
        if file is None:
            return None
        else:
            midi_loop = MidiLoop(self.input_port, self.output_port)
            midi_loop.load_file(file)
        return midi_loop

    def get_current_part(self):
        return self.song_parts[self.current_part_index]
    
    def get_current_part_fill(self):
        return self.song_parts[self.current_part_index].fills[self.fill_index]

    def process_commands(self):
        if self.input_commands_queue:
            command = self.input_commands_queue.pop(0)  # tba correct sequence?
            print(f"incoming command: {command}")

            if command == command_notes["prev"]:
                print("command prev part")
                self.flag.prev = True
              
            elif command == command_notes["next"]:
                print("command next part")
                self.flag.next = True
                 
            elif command == command_notes["fill"]:
                print("command insert fill")
                self.flag.fill = True

            elif command == command_notes["startstop"]:    
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
        
        return self.play_info       

    def extract_command_messages(self, input_messages):
        for msg in input_messages:
            if (
                msg.type == "note_on"
            ):  # stupid ableton has broken cc stuff, using notes for now. TBA - replace with CC.
                print(msg)
                self.input_commands_queue.append(msg.note)
                print(self.input_commands_queue)

    def extract_viz_data_from_loop(self, loop):
        self.play_info.beat_number = loop.current_beat_number  ##
        self.play_info.total_beat_numbers = len( loop.beats_absolute_time_ticks)
        self.play_info.file_name = loop.file_name
        #print (self.play_info.song_part_number )
        self.play_info.song_part_number = self.current_part_index
        self.play_info.fill_number = self.fill_index


        self.play_info.total_song_part_numbers = len(self.song_parts)  #TBA i should not get this info on each loop.
        try:
            self.play_info.total_fill_numbers = len( loop.fills)   #TBA i should not get this info on each loop.
        except:
            self.play_info.total_fill_numbers = "x"
    
    
    def play(self):
         
        while True:
            self.viz.visualize(self.get_play_info())
            input_midi_messages = list(self.input_port.iter_pending())
            self.extract_command_messages(input_midi_messages)
            self.process_commands()
            #print(self.state)
 
            if self.state == "idle" :
                pass
            elif self.state == "playing_intro" :
               self.flag_end_of_midi_loop = self.intro.play(input_midi_messages)
               self.extract_viz_data_from_loop(self.intro)

            elif self.state == "playing_groove":
               self.flag_end_of_midi_loop = self.get_current_part().play(input_midi_messages)
               self.extract_viz_data_from_loop(self.get_current_part())
        
            elif self.state == "playing_fill":
               #self.flag_end_of_midi_loop = 
               self.get_current_part_fill().play(input_midi_messages)
               self.flag_end_of_midi_loop = self.get_current_part().play(input_midi_messages, dry_run= True)
               self.extract_viz_data_from_loop(self.get_current_part())
                        
            self.sm_loop()

            

# init  midi ports.
input_port_name = "f_midi"
output_port_name = "f_midi"

output_port = mido.open_output(output_port_name)
input_port = mido.open_input(input_port_name)

song_path="songs_lib/grm_retrofunk_song.json"
#song_path="songs_lib/grm_dnb152.json"

with open(song_path, "r") as file:
    song_json = file.read()

song = MidiSong(input_port, output_port, song_json)
song.play()
