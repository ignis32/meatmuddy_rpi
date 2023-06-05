import json
from midi_loop_player import MidiLoop  
import mido 

class MidiSong:
    def __init__(self, input_port, output_port, song_json):
        self.input_port = input_port
        self.output_port = output_port
        self.song_data = json.loads(song_json)
        self.intro = MidiLoop(self.input_port, self.output_port)
        self.outro = MidiLoop(self.input_port, self.output_port)
        self.song_parts = []
        self.current_part_index = -1  # Using -1 to indicate no part is being played initially
        self.load_song()

    def load_song(self):
        self.intro.load_file(self.song_data['intro']['groove'])
        self.outro.load_file(self.song_data['outro']['groove'])

        for part in self.song_data['song_parts']:
            midi_part = MidiLoop(self.input_port, self.output_port)
            midi_part.load_file(part['groove'])
            midi_part.fills = [self.create_midi_loop(fill) for fill in part['fills']]
            midi_part.transition = self.create_midi_loop(part['transition'])
            self.song_parts.append(midi_part)

    def create_midi_loop(self, file):
        midi_loop = MidiLoop(self.input_port, self.output_port)
        midi_loop.load_file(file)
        return midi_loop

    def get_current_part(self):
        if self.current_part_index == -1:
            return self.intro
        elif self.current_part_index == len(self.song_parts):
            return self.outro
        else:
            return self.song_parts[self.current_part_index]

    def play(self):
        while True:
            current_part = self.get_current_part()
            still_playing = current_part.play()
            if not current_part.command_messages_stack == []:
                command = current_part.command_messages_stack[0]
                print(f"incoming command: 48")

            if not still_playing:
                print(self.get_current_part().file_name)
                print("RELOAD")
                current_part.stop_all_tracked_notes()
                current_part.rewind()
                
                
                self.current_part_index += 1
               
                if self.current_part_index > len(self.song_parts):  # All parts, including outro, have been played
                    break

# init  midi ports.
input_port_name = 'f_midi'
output_port_name = 'f_midi'

output_port = mido.open_output(output_port_name)
input_port = mido.open_input(input_port_name)

with open('demo_song.json', 'r') as file:
    song_json = file.read()

song = MidiSong(input_port, output_port, song_json)

# for i in song.song_parts:
#     print (i.file_name)
#print (song.song_parts)


#print (json.dumps(song.song_data, indent=3))
song.play()