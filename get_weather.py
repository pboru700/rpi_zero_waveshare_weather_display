import os
import sys
import requests
import pandas as pd
import json
from datetime import date
from dotenv import load_dotenv
import logging
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.DEBUG)

# Directories
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
dotenvdir = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4
# Load environment variables
load_dotenv(dotenvdir)

# Constants
TOKEN = os.environ.get("AQICN_TOKEN")
FONT_SIZE = 24
DATA_FILE = 'data.json'

# Load data
with open(DATA_FILE) as f:
    DATA = json.load(f)

GEO_LOCATIONS = DATA["geographic_locations"]
STATIONS = DATA["stations"]
AIR_QUALITY_NORMS = DATA["air_quality_norms"]

# Date
TODAY = date.today().strftime("%d-%m-%Y")
TODAY_REVERSE = date.today().strftime("%Y-%m-%d")

def load_api_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        return None

def load_aqicn_weather_conditions(station_id, token, date):
    base_url = f"https://api.waqi.info/feed/{station_id}/?token={token}"
    data = load_api_data(base_url)
    if data:
        pm10 = data.get("data", {}).get("iaqi", {}).get("pm10", {}).get("v")
        pm25 = data.get("data", {}).get("iaqi", {}).get("pm25", {}).get("v")
        return pm25, pm10
    return None, None

def load_openmeteo_weather_conditions(geo_location, city, date):
    url = "https://api.open-meteo.com/v1/forecast"
    url_data_location = f"?latitude={geo_location[city]['latitude']}&longitude={geo_location[city]['longitude']}"
    url_data_conditions = "&hourly=temperature_2m&current_weather=true"
    url_data_time_frame = f"&timezone=GMT&start_date={date}&end_date={date}"
    full_url_data = f"{url}{url_data_location}{url_data_conditions}{url_data_time_frame}"
    data = load_api_data(full_url_data)
    if data:
        weather_df = pd.DataFrame(data)
        return weather_df['current_weather']
    return None

def air_quality_emote(quality_level, norms):
    if quality_level <= int(norms["good"]):
        return Image.open(os.path.join(picdir, 'emote_smile.bmp'))
    elif int(norms["good"]) < quality_level <= int(norms["medium"]):
        return Image.open(os.path.join(picdir, 'emote_meh.bmp'))
    else:
        return Image.open(os.path.join(picdir, 'emote_bad_air.bmp'))

def draw(pm25, pm10, norms):
    logging.info("Initializing")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    logging.info("Drawing on the image")
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    calendar = Image.open(os.path.join(picdir, 'calendar_big_02.bmp'))
    sun = Image.open(os.path.join(picdir, 'sun.bmp'))
    cloud_01 = Image.open(os.path.join(picdir, 'clouds_advanced_01.bmp'))
    cloud_02 = Image.open(os.path.join(picdir, 'clouds_advanced_02.bmp'))
    upper_left_corner = Image.open(os.path.join(picdir, 'corner.bmp'))
    upper_right_corner = upper_left_corner.rotate(270)
    lower_left_corner = upper_left_corner.rotate(90)
    lower_right_corner = upper_left_corner.rotate(180)

    draw.line([(0, 59), (250, 59)], fill=0, width=4)
    draw.line([(124, 0), (124, 122)], fill=0, width=4)

    def draw_text(x, y, text):
        draw.text(
            (x, y), text,
            font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), FONT_SIZE), fill=0
        )

    # Draw PM2.5 norm, upper left
    draw_text(8, 4, 'PM2.5: ')
    draw_text(24, 30, f'{pm25}/{norms["pm25"]["good"]}')
    pm25_emote = air_quality_emote(pm25, norms["pm25"])
    image.paste(pm25_emote, (86, 8))

    # Draw PM10 norm, lower left
    draw_text(8, 67, 'PM10: ')
    draw_text(24, 93, f'{pm10}/{norms["pm10"]["good"]}')
    pm10_emote = air_quality_emote(pm10, norms["pm10"])
    image.paste(pm10_emote, (86, 71))

    # Draw Weather conditions icons, upper right
    image.paste(sun, (134, 16))
    image.paste(cloud_01, (190, 8))
    image.paste(cloud_02, (174, 32))

    # Draw date and calendar, lower right
    image.paste(calendar, (166, 64))
    draw_text(128, 93, TODAY)

    # Draw corners
    image.paste(upper_left_corner, (0, 0))
    image.paste(upper_right_corner, (247, 0))
    image.paste(lower_left_corner, (0, 119))
    image.paste(lower_right_corner, (247, 119))

    epd.displayPartBaseImage(epd.getbuffer(image))
    logging.info("Goto Sleep...")
    epd.sleep()

if __name__ == "__main__":
    pm25, pm10 = load_aqicn_weather_conditions(
        STATIONS["lodz_czernika"],
        TOKEN,
        TODAY_REVERSE
    )
    if pm25 is not None and pm10 is not None:
        draw(pm25, pm10, AIR_QUALITY_NORMS)
