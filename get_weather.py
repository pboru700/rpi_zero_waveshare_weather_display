import os
import sys
import requests
import pandas as pd
import json
from datetime import date
from dotenv import load_dotenv
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
dotenvdir = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(libdir):
    sys.path.append(libdir)
import logging
# from waveshare_epd import epd2in13_V4
from PIL import Image,ImageDraw,ImageFont

logging.basicConfig(level=logging.DEBUG)

font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

load_dotenv(dotenvdir)

token = os.environ.get("AQICN_TOKEN")

f = open('data.json')
data = json.load(f)
geographic_locations = data["geographic_locations"]
stations = data["stations"]
air_quality_norms = data["air_quality_norms"]

today = date.today().strftime("%Y-%m-%d")

def load_aqicn_weather_conditions(station_id, tok, date):
    base_url = "https://api.waqi.info"
    trail_url = "/feed/@{}/?token={}".format(station_id, tok)
    full_url = base_url + trail_url
    response = requests.get(full_url).json()
    pm10 = response["data"]["iaqi"]["pm10"]["v"]
    pm25_forecast_days = response["data"]["forecast"]["daily"]["pm25"]
    pm25_forecast_today_all = [ x for x in pm25_forecast_days if x["day"] == date ]
    pm25_forecast_today_avg = pm25_forecast_today_all[0]["avg"]
    json_object = json.dumps(response, indent = 2)
    return(pm25_forecast_today_avg, pm10)

def load_openmeteo_weather_conditions(geo_location, city, date):
    url = "https://api.open-meteo.com/v1/forecast"
    url_data_location = "?latitude={latitude}&longitude={longitude}".format(
        latitude = geo_location[city]["latitude"],
        longitude = geo_location[city]["longitude"]
    )
    url_data_conditions = "&hourly=temperature_2m&current_weather=true"
    url_data_time_frame = "&timezone=GMT&start_date={date}&end_date={date}".format(date=today)
    full_url_data = "{}{}{}{}".format(url,url_data_location,url_data_conditions,url_data_time_frame)
    response = requests.get(full_url_data).json()
    weather_df = pd.DataFrame(response)
    current_weather = weather_df['current_weather']
    return current_weather

def air_quality_emote(type, quality_level, norms):
    if int(quality_level) <= int(norms[type]["good"]):
        emote = Image.open(os.path.join(picdir, 'emote_smile.png'))
    elif int(norms[type]["good"]) < int(quality_level) <= int(norms[type]["medium"]):
        emote = Image.open(os.path.join(picdir, 'emote_meh.png'))
    else:
        emote = Image.open(os.path.join(picdir, 'emote_bad_air.png'))
    return emote

# def draw(pm25, pm10, norms):
#     logging.info("Initializing")
#     epd = epd2in13_V4.EPD()
#     epd.init()
#     epd.Clear(0xFF)

#     logging.info("Drawing on the image")
#     image = Image.new('1', (epd.height, epd.width), 255)
    # draw = ImageDraw.Draw(image)

    # draw.line([(0,59),(250,59)], fill = 0,width = 4)
    # draw.line([(124,0),(124,122)], fill = 0,width = 4)

    # draw.text(
    #     (8, 8), u'PM2.5: ' + pm25 + u'/' + norms["pm25"]["good"],
    #     font = font24, fill = 0
    # )
    # pm25_emote = air_quality_emote("pm25", pm25, norms)
    # image.paste(pm25_emote, (8, 34))

    # draw.text(
    #     (8, 67), u'PM10: ' + pm10 + u'/' + norms["pm10"]["good"],
    #     font = font24, fill = 0
    # )
    # pm10_emote = air_quality_emote("pm10", pm10, norms)
    # image.paste(pm10_emote, (8,93))

    # epd.displayPartBaseImage(epd.getbuffer(image))

if __name__ == "__main__":
    pm25, pm10 = load_aqicn_weather_conditions(stations["lodz_czernika"], token, today)
    # draw(pm25, pm10, air_quality_norms)
