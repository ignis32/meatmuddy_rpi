import copy
import multiprocessing
import time
# UI drawing libs
from PIL import Image,ImageDraw,ImageFont
#Waveshare oled stuff
import spidev as SPI
import drivers.waveshare_oled.ST7789 as ST7789  
import os
#waveshare epaper stuff  # not working yet

#from waveshare_epd import epd2in13_V3
 

class PlayInfo:
    def __init__(self, file_name=None, beat_number=None, total_beat_numbers=None, bar_number=None, 
                 total_bar_number=None, prev_part_scheduled=False, next_part_scheduled=False, 
                 fill_scheduled=False, startstop_scheduled=False, 
                 song_part_number =0, total_song_part_numbers =0,

                  fill_number=0,  total_fill_numbers=0, state="idle",
                   CLOCKRUNS=0
                   
                 ):

        self.file_name = file_name

        self.beat_number = beat_number
        self.total_beat_numbers = total_beat_numbers
        
        self.bar_number = bar_number
        self.total_bar_number = total_bar_number
        
        self.song_part_number  = song_part_number
        self.total_song_part_numbers = total_song_part_numbers

        self.fill_number =fill_number
        self.total_fill_numbers =fill_number

 
        self.prev_part_scheduled = prev_part_scheduled
        self.next_part_scheduled = next_part_scheduled
        self.fill_scheduled = fill_scheduled
        self.startstop_scheduled = startstop_scheduled
        self.state  = state

        self.CLOCKRUNS=CLOCKRUNS

    def get_flags_as_string(self):
        state_str = "["
        state_str += "F" if self.fill_scheduled else "_"
        state_str += "P" if self.prev_part_scheduled else "_"
        state_str += "N" if self.next_part_scheduled else "_"
        state_str += "S" if self.startstop_scheduled else "_"
        state_str += "]"
        return state_str
       

    def __eq__(self, other):
        if isinstance(other, PlayInfo):
            return self.__dict__ == other.__dict__
        else:   
            raise()
        return False


class VisualizePlayInfo:
    def __init__(self):
        self.prev_play_info = PlayInfo()

    def visualize(self, play_info):
        # draw visualization only if there is a change.
        if not self.prev_play_info == play_info:
            self.prev_play_info = copy.deepcopy(play_info)
            
          #  self.render()
     
    def get_filename_from_path(self,path):
        segments = str(path).split('/')
        filename = segments[-1]
        return filename

    
    def render(self):
        # Define a mapping of loop types to their respective symbols
        #loop_type_symbols = {"intro": "I", "outro": "O", "groove": "G", "fill": "F"}

        # Use the mapping to get the symbol for the loop type, default to "" if loop type is not recognized
        #loop_type_symbol = loop_type_symbols.get(self.prev_play_info.loop_type, "")

        # Add the symbol to the filename
        print(f"Filename: ({self.prev_play_info.state}) {self.get_filename_from_path(self.prev_play_info.file_name)}")
        print(f"Beats: {self.prev_play_info.beat_number}/{self.prev_play_info.total_beat_numbers}")
        print(f"Bars: {self.prev_play_info.bar_number}/{self.prev_play_info.total_bar_number}")
        print(f"Part: {self.prev_play_info.song_part_number +1}/{self.prev_play_info.total_song_part_numbers}")
        print(f"Fill: {self.prev_play_info.fill_number+1}/{self.prev_play_info.total_fill_numbers}")
        
        # Create the string based on the boolean values
        # state_str = "["
        # state_str += "F" if self.prev_play_info.fill_scheduled else "_"
        # state_str += "P" if self.prev_play_info.prev_part_scheduled else "_"
        # state_str += "N" if self.prev_play_info.next_part_scheduled else "_"
        # state_str += "S" if self.prev_play_info.startstop_scheduled else "_"
        # state_str += "]"
        
        print(self.prev_play_info.get_flags_as_string())
 

class VisualizePlayInfoWaveshareOLED:
    def __init__(self):
        self.prev_play_info = PlayInfo()

    #Waveshare 1.3 LCD hat display init
        # Raspberry Pi pin configuration:
        RST = 27
        DC = 25
        BL = 24
        bus = 0 
        device = 0 

        # 240x240 display with hardware SPI:
        disp = ST7789.ST7789(SPI.SpiDev(bus, device),RST, DC, BL)

        # Initialize library.
        disp.Init()

        # Clear display.
        disp.clear()

        self.disp = disp
        self.font24 = ImageFont.truetype(  'Font.ttc' , 30)
        self.font36 = ImageFont.truetype(  'Font.ttc' , 40)
        # Create blank image for drawing.
        self.image = Image.new("RGB", (self.disp.width, self.disp.height), "WHITE")
        self.draw = ImageDraw.Draw(self.image)
       # self.draw.text((20, 20), f"TEST" , font = self.font24, fill = 255)
        self.disp.ShowImage(self.image,0,0)
       
       
        # stuff shared with a separate process
        # launch a separate thread to draw stuff, to evade interfering with midi timings.
        self.update_required = multiprocessing.Value('b', True)

        self.manager = multiprocessing.Manager()
        self.shared_playinfo_dict =  self.manager.dict()
        self.shared_playinfo_dict['prev_play_info'] = PlayInfo().__dict__ 
        self.start_background_screen_updates()
    

    def visualize(self, play_info):
        # draw visualization only if there is a change.
        if not self.prev_play_info == play_info:
            print(play_info.state)
            self.prev_play_info = copy.deepcopy(play_info)  
            # share data with display update process
            self.shared_playinfo_dict['prev_play_info'] = self.prev_play_info.__dict__  
            self.update_required.value = True  # let know the second process it's time to display new data
          
    def get_filename_from_path(self,path):
        segments = str(path).split('/')
        filename = segments[-1]
        return filename

    def start_background_screen_updates(self):  # launch display updates as a seprate process to let midi part work better
        print("launch background process")
        self.bg_process = multiprocessing.Process(target=self.constant_background_render)
        self.bg_process.start()
        print("launched background process")

    # vital to stop dedicated display process correctly, otherwise brace for zombie (processes) apocalypse
    def stop_background_screen_updates(self):
            self.bg_process.terminate()
            self.bg_process.join()
            self.manager.shutdown()

    def constant_background_render(self):

        # Combination of these params are responsible for ratio  of the computing power
        # distribution between display background updater and main midi handling app.

        # these two are empirically  tuned on my raspberry.
        # 5 / 0.05 works nice with midi but display updates feel laggy
        BACKGROUND_NICE_PRIORITY   =   5   #process priority. Higher the number, the lower is priority.
        BACKGROUND_SLEEP_TIME = 0.01       #how long to sleep between cycles.

        os.nice(5)
        while True:
            if self.update_required.value:
                self.update_required.value = False  # we say that  we handled this update.
                # extract information from the shared memory dict
                play_info_dict = self.shared_playinfo_dict['prev_play_info']
                # Convert it back to a PlayInfo object    
                prev_play_info = PlayInfo(**play_info_dict)
                print("RENDER")
               
                # generating ui                
                line_height = 30
                line_spacing = 4
                    
                UI_text_lines = [ 
                    f"{self.get_filename_from_path(prev_play_info.file_name)}",
                    f"{prev_play_info.state }",            
                    f"Beats: {prev_play_info.beat_number}/{prev_play_info.total_beat_numbers}",
                    f"Fill: {prev_play_info.fill_number+1}/{prev_play_info.total_fill_numbers}",
                    f"Part: {prev_play_info.song_part_number +1}/{prev_play_info.total_song_part_numbers}",
                ]
             
                bg_colors_map=  {
                        "idle": "WHITE",
                        "playing_intro":"lavender",
                        "playing_outro":"lightsalmon",
                        "playing_groove":"lightgreen" ,
                        "playing_fill":"palegoldenrod"                   
                }

                # draw text 
                background_color = bg_colors_map[prev_play_info.state]
                self.image = Image.new("RGB", (self.disp.width, self.disp.height), background_color)
                self.draw = ImageDraw.Draw(self.image)

                line_number=0
                for line_text in UI_text_lines:
                    self.draw.text( (20, (line_number*(line_height + line_spacing))), line_text , font = self.font24, fill = "black")
                    line_number+=1

                self.draw.text( (122, (5*(line_height + line_spacing))), f"{prev_play_info.CLOCKRUNS}" , font = self.font24, fill = "red")
                # draw flags separately with a bigger font
                self.draw.text( (20, (line_number*(line_height + line_spacing))), f"{prev_play_info.get_flags_as_string()}" , font =  self.font36, fill = "black")
                
                # send image to display
                self.disp.ShowImage(self.image ,0,0)
                time.sleep(BACKGROUND_SLEEP_TIME) ## give main midi process to breath

 