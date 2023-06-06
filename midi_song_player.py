import json
from midi_loop_player import MidiLoop
import mido
import json
from meatmuddy_config import command_notes as command_notes


class MidiSong:
    def __init__(self, input_port, output_port, song_json):
        self.input_port = input_port
        self.output_port = output_port
        self.song_data = json.loads(song_json)
        self.intro = None
        self.outro = None
        self.song_parts = []
        self.current_part_index = -1  # Using -1 to indicate no part is being played initially
        self.next_part_scheduled = False  # Indicates if next part is scheduled
        self.fill_scheduled = False  # Indicates if fill is scheduled
        self.fill_index = 0  # Index for cycling through fills
        self.load_song()

        self.playing = False  # initially not playing

        self.input_commands_queue =  []
        # place to store input cc/notes for controlling loops

    def load_song(self):
        self.intro = self.create_midi_loop(self.song_data["intro"]["groove"])
        self.outro = self.create_midi_loop(self.song_data["outro"]["groove"])
        self.next_part_scheduled = True  # intro is going to  switch to first section in any case # tba, handle None intro.

        for part in self.song_data["song_parts"]:
            midi_part = self.create_midi_loop(part["groove"])
            midi_part.fills = [self.create_midi_loop(fill) for fill in part["fills"]]
            midi_part.transition = self.create_midi_loop(part["transition"])
            self.song_parts.append(midi_part)

    def create_midi_loop(self, file):
        midi_loop = MidiLoop(self.input_port, self.output_port)
        midi_loop.load_file(file)
        return midi_loop

    def get_current_part(self):
        if self.current_part_index == -1:
            return self.intro
        elif self.current_part_index == len(self.song_parts):
            self.next_part_scheduled= True  # outro should stop on it's own.
            return self.outro
        else:
            return self.song_parts[self.current_part_index]

    def process_commands(self):
        if self.input_commands_queue:
            command = self.input_commands_queue.pop(0)  # tba correct sequence?
            print(f"incoming command: {command}")

            if command == command_notes["prev"]:
                print("command prev part")
                self.prev_part_scheduled = True

            elif command == command_notes["next"]:
                print("command next part")
                self.next_part_scheduled = True

            elif command == command_notes["fill"]:
                print("command insert fill")
                self.fill_scheduled = True

            elif command == command_notes["startstop"]:
                print("command start/stop received")
                self.playing = not self.playing  # toggle the playing state
                if not self.playing:  # if stopped tight now
                    self.get_current_part().rewind()  # rewind the current part
                    self.current_part_index = -1     # returning to intro
                    self.next_part_scheduled = True  # intro is playable once
                    self.fill_scheduled = False  

            else:
                print("unknown command")

            ## tba start or stop

    def extract_command_messages(self, input_messages):
        for msg in input_messages:
            if (
                msg.type == "note_on"
            ):  # stupid ableton has broken cc stuff, using notes for now. TBA - replace with CC.
                print(msg)
                self.input_commands_queue.append(msg.note)
                print(self.input_commands_queue)

    def play(self):
        while True:
            input_messages = list(self.input_port.iter_pending())
            self.extract_command_messages(input_messages)
            self.process_commands()
            if not self.playing:  # if not playing, just skip the rest of the loop
                continue

            current_part = self.get_current_part()

            # tba - bug - if we command to play too late, it will play full fill anyway, and timing would be odd.
            # We should play only rest of the fill.

            # tba - probably we should count time in current_part as well, and stop fill by current_part instead

            # tba

            if (
                self.fill_scheduled
                and current_part.ticks_left_to_end
                <= current_part.fills[self.fill_index].loop_length_in_ticks
            ):
                # Play fill if fill is scheduled and it's time to start the fill
                still_playing = current_part.fills[self.fill_index].play(input_messages)

                if not still_playing:
                    self.fill_scheduled = False
                    self.fill_index = (self.fill_index + 1) % len( current_part.fills )  # Cycle to next fill
                    current_part.rewind()  # manually rewind current song part, it had not finished in the regular way
            else:
                # Play groove
                still_playing = current_part.play(input_messages)

            if not still_playing and not self.fill_scheduled:
                print("RELOAD")

                if self.next_part_scheduled:
                    self.current_part_index += 1
                    self.fill_index = 0  # reset fills index
                    if self.current_part_index > len( self.song_parts ):  # All parts, including outro, have been played
                        self.playing=False           
                        self.current_part_index=-1 # song rewind?
                        self.next_part_scheduled = True
                    
                    else:
                        self.next_part_scheduled = False  


# init  midi ports.
input_port_name = "f_midi"
output_port_name = "f_midi"

output_port = mido.open_output(output_port_name)
input_port = mido.open_input(input_port_name)

#
# 
# song_path="songs_lib/grm_retrofunk_song.json"
song_path="songs_lib/grm_dnb152.json"

with open(song_path, "r") as file:
    song_json = file.read()

song = MidiSong(input_port, output_port, song_json)
song.play()
