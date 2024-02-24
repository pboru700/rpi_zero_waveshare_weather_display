import sys
import os
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in13_V4
import time
from PIL import Image,ImageDraw,ImageFont
import traceback

logging.basicConfig(level=logging.DEBUG)

font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

logging.info("Initializing")
epd = epd2in13_V4.EPD()
epd.init()
epd.Clear(0xFF)

logging.info("Drawing on the image")
image = Image.new('1', (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)

draw.line([(0,59),(250,59)], fill = 0,width = 4)
draw.line([(124,0),(124,122)], fill = 0,width = 4)
draw.text((10, 10), u'PM2.5:', font = font24, fill = 0)
draw.text((10, 69), u'PM5:', font = font24, fill = 0)
draw.text((134, 69), u'PM10:', font = font24, fill = 0)

epd.displayPartBaseImage(epd.getbuffer(image))
