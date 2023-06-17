import os
import json
import time

import mido
from midi_song_player import MidiSong
# Menu UI paprams
FONT_PATH = 'Font.ttc'  # replace with path to your preferred .ttf file
FONT_SIZE = 24  # adjust this as needed
SONGS_PER_PAGE = 6
SONG_LIST_START = 0
RUNNING_TEXT_SPEED = 0.1  # Speed of running text. Less = fasster



# Some GPIO display/keypad init bolierplate.
with open('gpio_init_waveshare_1.13_hat.py', 'r') as file:
    script_contents = file.read()
# Execute the script
exec(script_contents)


# Load the songs from the song lib
def songs_lib():
    if not os.path.isdir('songs_lib'):
        raise ValueError('song_lib is absent')

    content = os.listdir('songs_lib')
    json_files = [os.path.splitext(file)[0] for file in content if file.endswith('.json')]
    return json_files

class SongInfo:

    def __init__(self, filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        
        self.name = data.get('name')
        self.tempo = data.get('tempo')
        self.time_signature = data.get('time_signature')
        self.midi_channel = data.get('midi_channel')

class SongMenuItem:

    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.start_pos = 0
        self.last_update = time.time()
        self.song_info = SongInfo(f"songs_lib/{name}.json")
        self.song_file_path =  f"songs_lib/{name}.json" 
    
    # menu item draws itself knowing it's position.
    def draw(self, draw, font, relative_position, selected=False):
        text_x, text_y = 10, 10 + relative_position*20
        draw.text((text_x - self.start_pos, text_y), self.name, font=font, fill='white')

        if selected:
            draw.rectangle(
                [text_x, text_y, text_x+width, text_y+FONT_SIZE],
                outline="lightgreen"
            )

    def update(self, draw, font):
        text_length = draw.textlength(self.name, font=font)
        if text_length > width:
            now = time.time()
            if now - self.last_update > RUNNING_TEXT_SPEED:
                self.start_pos += FONT_SIZE
                if self.start_pos > text_length:
                    self.start_pos = 0
                self.last_update = now

class Menu:
    def __init__(self):
        self.songs = [SongMenuItem(name, i) for i, name in enumerate(songs_lib())]
        self.position = 0

    def draw(self, draw, font):
        draw.rectangle((0,0,width,height), outline=0, fill=0)

        start_pos = max(0, self.position - SONG_LIST_START)
        end_pos = min(len(self.songs), start_pos + SONGS_PER_PAGE)

        for i in range(start_pos, end_pos):
            relative_position = i - start_pos
            selected = (i == self.position)
            self.songs[i].draw(draw, font, relative_position, selected)

    def update(self, draw, font):
        for song in self.songs:
            song.update(draw, font)

    def print_song_info(self):
        print(f"{self.songs[self.position].song_info.name}")
        print(f"Tempo: {self.songs[self.position].song_info.tempo}")
        print(f"Sig: {self.songs[self.position].song_info.time_signature}")
    
     
    
    def draw_song_info(self, draw,font, start_x, start_y):
        song_name = self.songs[self.position].song_info.name
        tempo = self.songs[self.position].song_info.tempo
        time_signature = self.songs[self.position].song_info.time_signature

        # Clear the bottom section of the display.
        draw.rectangle((start_x, start_y, width, height), outline=0, fill=0)
        draw.rectangle((start_x-4, start_y-4, width-1, height-1), outline="lightgreen" )


        # Display the song information at the specified position on the screen.
        text = f"{song_name}"
        draw.text((start_x, start_y), text, font=font, fill='lightblue')

        text = f"Tempo: {tempo}"
        draw.text((start_x, start_y + FONT_SIZE+4), text, font=font, fill='pink')

        text = f"Time Sig : {time_signature}"
        draw.text((start_x, start_y + (FONT_SIZE+4)*2), text, font=font, fill='yellow')

       # disp.ShowImage(image, 0, 0)
    
        #print(self.songs[self.position].song_info.__dict__)
    def handle_keypress(self, key):
        if key == 'up':
            self.position = max(0, self.position - 1)
            print("Up")
            self.print_song_info()
        elif key == 'down':
            self.position = min(len(self.songs) - 1, self.position + 1)
            print("Down")
            self.print_song_info()
        elif key == "right":
            self.position = min(len(self.songs) - SONGS_PER_PAGE, self.position + SONGS_PER_PAGE)  # Page down  
            print("Right")   
            self.print_song_info() 
        elif key == "left":
            self.position = max(0, self.position - SONGS_PER_PAGE)  # Page up
            print("Left")
            self.print_song_info()
        elif key == 'key_1':  # Add this condition for key 1
            song = self.songs[self.position]
            print("opening Current song:", song.name)
            self.play_song()
   
    def play_song(self):
        input_port_name = "f_midi"
        output_port_name = "f_midi"

        output_port = mido.open_output(output_port_name)
        input_port = mido.open_input(input_port_name)

        song_path= self.songs[self.position].song_file_path
        #song_path="songs_lib/grm_dnb152.json"

        # midi_thread = threading.Thread(target=read_midi_input)
        # midi_thread.start()

        with open(song_path, "r") as file:
            song_json = file.read()

            song = MidiSong(input_port, output_port, song_json)
            song.play()

def main():
    os.nice(-10)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    menu = Menu()

    while True:
        if not GPIO.input(KEY_UP_PIN):
            menu.handle_keypress('up')
        if not GPIO.input(KEY_DOWN_PIN):
            menu.handle_keypress('down')
        if not GPIO.input(KEY_LEFT_PIN):
            menu.handle_keypress('left')
        if not GPIO.input(KEY_RIGHT_PIN):
            menu.handle_keypress('right')
        if not GPIO.input(KEY_RIGHT_PIN):
            menu.handle_keypress('right')
        if not GPIO.input(KEY1_PIN):
            menu.handle_keypress('key_1')
            
        

        menu.draw(draw, font)
        menu.update(draw, font) #something for running line
        menu.draw_song_info(draw, font,10,140)
        disp.ShowImage(image, 0, 0)

try:
    main()
except KeyboardInterrupt:
    print("Interrupted")
finally:
    GPIO.cleanup()
