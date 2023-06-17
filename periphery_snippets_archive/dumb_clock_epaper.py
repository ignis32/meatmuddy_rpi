#!/usr/bin/python
# Striped down waveshare example, that shows that epaper can print the clock in seconds.
 

import sys
import os
import logging
from waveshare_epd import epd2in13_V3
import time
from PIL import Image,ImageDraw,ImageFont
import traceback

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd2in13_V3 Demo")
    
    epd = epd2in13_V3.EPD()
    logging.info("init and Clear")
    epd.init()
    epd.Clear(0xFF)

    # Drawing on the image
    font15 = ImageFont.truetype(  'Font.ttc' , 15)
    font24 = ImageFont.truetype(  'Font.ttc' , 24)
     
    # # partial update
    logging.info("4.show time...")
    time_image = Image.new('1', (epd.height, epd.width), 255)
    time_draw = ImageDraw.Draw(time_image)
    
    #epd.displayPartBaseImage(epd.getbuffer(time_image))
    num = 0
    old_time_str =""
    while (True):
       
        start_time = time.process_time()
        time_str = time.strftime('%H:%M:%S')
       # time_draw.rectangle((120, 80, 220, 105), fill = 255)

        time_draw.text((120, 80), old_time_str , font = font24, fill = 255)
        time_draw.text((120, 80), time_str, font = font24, fill = 0)
        old_time_str = time_str
        epd.displayPartial(epd.getbuffer(time_image))
        
        end_time = time.process_time()
        execution_time = end_time - start_time
        print("Execution time:", execution_time, "seconds")

        num = num + 1
        if(num == 20):
            break
    
    logging.info("Clear...")
    epd.init()
    epd.Clear(0xFF)
    
    logging.info("Goto Sleep...")
    epd.sleep()
        
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in13_V3.epdconfig.module_exit()
    exit()
