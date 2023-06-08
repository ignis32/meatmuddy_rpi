import copy
class PlayInfo:
    def __init__(self, file_name=None, beat_number=None, total_beat_numbers=None, bar_number=None, 
                 total_bar_number=None, loop_type=None, prev_part_scheduled=False, next_part_scheduled=False, 
                 fill_scheduled=False, startstop_scheduled=False):

        self.file_name = file_name
        self.beat_number = beat_number
        self.total_beat_numbers = total_beat_numbers
        self.bar_number = bar_number
        self.total_bar_number = total_bar_number
        self.loop_type = loop_type
        self.prev_part_scheduled = prev_part_scheduled
        self.next_part_scheduled = next_part_scheduled
        self.fill_scheduled = fill_scheduled
        self.startstop_scheduled = startstop_scheduled

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
            
            self.render()
     
    def get_filename_from_path(self,path):
        segments = str(path).split('/')
        filename = segments[-1]
        return filename
    def render(self):
        # Define a mapping of loop types to their respective symbols
        loop_type_symbols = {"intro": "I", "outro": "O", "groove": "G", "fill": "F"}

        # Use the mapping to get the symbol for the loop type, default to "" if loop type is not recognized
        loop_type_symbol = loop_type_symbols.get(self.prev_play_info.loop_type, "")

        # Add the symbol to the filename
        print(f"Filename: ({loop_type_symbol}) {self.get_filename_from_path(self.prev_play_info.file_name)}")
        print(f"Beats: {self.prev_play_info.beat_number}/{self.prev_play_info.total_beat_numbers}")
        print(f"Bars: {self.prev_play_info.bar_number}/{self.prev_play_info.total_bar_number}")
        
        # Create the string based on the boolean values
        state_str = "["
        state_str += "F" if self.prev_play_info.fill_scheduled else "_"
        state_str += "P" if self.prev_play_info.prev_part_scheduled else "_"
        state_str += "N" if self.prev_play_info.next_part_scheduled else "_"
        state_str += "]"
        
        print(state_str)

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