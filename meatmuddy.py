import os
import json
import time
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import spidev as SPI
import drivers.waveshare_oled.ST7789 as ST7789

#GPIO define
RST_PIN        = 25
CS_PIN         = 8
DC_PIN         = 24

KEY_UP_PIN     = 6 
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13

KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

RST = 27
DC = 25
BL = 24
bus = 0 
device = 0 

# 240x240 display with hardware SPI:
disp = ST7789.ST7789(SPI.SpiDev(bus, device),RST, DC, BL)
disp.Init()

# Clear display.
disp.clear()

#init GPIO
GPIO.setmode(GPIO.BCM) 
GPIO.setup(KEY_UP_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_RIGHT_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY_PRESS_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)

width = 240
height = 240
image = Image.new('RGB', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)
disp.ShowImage(image,0,0)

FONT_PATH = 'Font.ttc'  # replace with path to your preferred .ttf file
FONT_SIZE = 24  # adjust this as needed
SONGS_PER_PAGE = 6
SONG_LIST_START = 0
RUNNING_TEXT_SPEED = 1  # Speed of running text

# Load the songs from the song lib
def songs_lib():
    if not os.path.isdir('songs_lib'):
        raise ValueError('song_lib is absent')

    content = os.listdir('songs_lib')
    json_files = [os.path.splitext(file)[0] for file in content if file.endswith('.json')]
    return json_files

class Song:
    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.start_pos = 0
        self.last_update = time.time()

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
        self.songs = [Song(name, i) for i, name in enumerate(songs_lib())]
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

    def handle_keypress(self, key):
        if key == 'up':
            self.position = max(0, self.position - 1)
            print("Up")
        elif key == 'down':
            self.position = min(len(self.songs) - 1, self.position + 1)
            print("Down")
        elif key == "right":
            self.position = min(len(self.songs) - SONGS_PER_PAGE, self.position + SONGS_PER_PAGE)  # Page down  
            print("Right")    
        elif key == "left":
            self.position = max(0, self.position - SONGS_PER_PAGE)  # Page up
            print("Left")
        elif key == 'key_1':  # Add this condition for key 1
            song = self.songs[self.position]
            print("Current song:", song.name)

def main():
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
        menu.update(draw, font)

        disp.ShowImage(image, 0, 0)

try:
    main()
except KeyboardInterrupt:
    print("Interrupted")
finally:
    GPIO.cleanup()
