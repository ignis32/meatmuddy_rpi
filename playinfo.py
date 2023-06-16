import copy
import multiprocessing
import time
# UI drawing libs
from PIL import Image,ImageDraw,ImageFont
#Waveshare oled stuff
import spidev as SPI
import drivers.waveshare_oled.ST7789 as ST7789  
 
#waveshare epaper stuff  # not working yet

#from waveshare_epd import epd2in13_V3
 

class PlayInfo:
    def __init__(self, file_name=None, beat_number=None, total_beat_numbers=None, bar_number=None, 
                 total_bar_number=None, prev_part_scheduled=False, next_part_scheduled=False, 
                 fill_scheduled=False, startstop_scheduled=False, 
                 song_part_number =0, total_song_part_numbers =0,

                  fill_number=0,  total_fill_numbers=0, state="idle"

                 
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
        # launch a separate thread to draw stuff, to evade interfering with midi timings.
        self.update_required = multiprocessing.Value('b', False)


        self.manager = multiprocessing.Manager()
        self.shared_playinfo_dict =  self.manager.dict()
        self.shared_playinfo_dict['prev_play_info'] = PlayInfo().__dict__

      
        self.start_background_screen_updates()
    

    def visualize(self, play_info):
        # draw visualization only if there is a change.
        if not self.prev_play_info == play_info:
            print(play_info.state)
            self.prev_play_info = copy.deepcopy(play_info)  
            self.shared_playinfo_dict['prev_play_info'] = self.prev_play_info.__dict__  
            self.shared_playinfo_dict['prev_play_info']['state']  = play_info.state
            self.update_required.value = True
            
     
    def get_filename_from_path(self,path):
        segments = str(path).split('/')
        filename = segments[-1]
        return filename

    
 
      

    def start_background_screen_updates(self):
        print("launch process")
        bg_process = multiprocessing.Process(target=self.constant_background_render)
        bg_process.start()
        print("launched process")

    def constant_background_render(self):
 
        while True:
          #  print(",", end="")
            if self.update_required.value:
                
                start_time = time.process_time()

                self.update_required.value = False
               
                play_info_dict = self.shared_playinfo_dict['prev_play_info']
                #print (play_info_dict)
                # Convert it back to a PlayInfo object
                prev_play_info = PlayInfo(**play_info_dict)
                print("RENDER")
               # generating ui 
                line_number=0
                line_height = 30
                line_spacing = 4
                
                
                UI_text_lines = [ 
                    f"{self.get_filename_from_path(prev_play_info.file_name)}",
                    f"{prev_play_info.state }",            
                    f"Beats: {prev_play_info.beat_number}/{prev_play_info.total_beat_numbers}",
                    f"Fill: {prev_play_info.fill_number+1}/{prev_play_info.total_fill_numbers}",
                    f"Part: {prev_play_info.song_part_number +1}/{prev_play_info.total_song_part_numbers}",
                   # f"{prev_play_info.get_flags_as_string()}"
                ]
                
                #print(UI_text_lines)
             
                bg=  {
                        "idle": "WHITE",
                        "playing_intro":"lavender",
                        "playing_outro":"lightsalmon",
                        "playing_groove":"lightgreen" ,
                        "playing_fill":"palegoldenrod"
                        
                }

               

                background_color = bg[prev_play_info.state]
                self.image = Image.new("RGB", (self.disp.width, self.disp.height), background_color)
                self.draw = ImageDraw.Draw(self.image)
                for line_text in UI_text_lines:
                    self.draw.text( (20, (line_number*(line_height + line_spacing))), line_text , font = self.font24, fill = "black")
                    line_number+=1
                
                self.draw.text( (20, (line_number*(line_height + line_spacing))), f"{prev_play_info.get_flags_as_string()}" , font =  self.font36, fill = "black")
                   
                



                self.disp.ShowImage(self.image ,0,0)

                end_time = time.process_time()
                execution_time = end_time - start_time
               # print("PARTIAL REFRESEH time:", execution_time, "seconds")
               # print(".")
               
                time.sleep(0.1)

def main():
    # Create an instance of VisualizePlayInfo
    visualize_play_info = VisualizePlayInfo()

    # Create a PlayInfo instance and visualize it
    play_info_1 = PlayInfo("song1.mid", 3, 4, 1, 4, "intro")
    visualize_play_info.visualize(play_info_1)

    # Change some fields in the PlayInfo instance and visualize it again
    play_info_1.beat_number = 4
    play_info_1.fill_scheduled = True
    visualize_play_info.visualize(play_info_1)

    # Create another PlayInfo instance and visualize it
    play_info_2 = PlayInfo("song2.mid", 2, 4, 1, 4, "groove")
    play_info_2.prev_part_scheduled = True
    play_info_2.next_part_scheduled = True
    visualize_play_info.visualize(play_info_2)

if __name__ == "__main__":
    main()