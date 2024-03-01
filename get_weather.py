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

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
dotenvdir = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

load_dotenv(dotenvdir)

TOKEN = os.environ.get("AQICN_TOKEN")

with open('data.json') as f:
    DATA = json.load(f)

GEO_LOCATIONS = DATA["geographic_locations"]
STATIONS = DATA["stations"]
AIR_QUALITY_NORMS = DATA["air_quality_norms"]

TODAY = date.today().strftime("%Y-%m-%d")

FONT_SIZE = 24

def load_api_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        return None


def load_aqicn_weather_conditions(station_id, token, date):
    base_url = f"https://api.waqi.info/feed/@{station_id}/?token={token}"
    data = load_api_data(base_url)
    if data:
        pm10 = data.get("data", {}).get("iaqi", {}).get("pm10", {}).get("v")
        pm25_forecast_days = data.get("data", {}).get("forecast", {}).get("daily", {}).get("pm25", [])
        pm25_forecast_today_all = [x for x in pm25_forecast_days if x["day"] == date]
        pm25_forecast_today_avg = pm25_forecast_today_all[0]["avg"] if pm25_forecast_today_all else None
        return pm25_forecast_today_avg, pm10
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

    draw.line([(0, 59), (250, 59)], fill=0, width=4)
    draw.line([(124, 0), (124, 122)], fill=0, width=4)

    draw.text(
        (8, 6), f'PM2.5: ',
        font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), FONT_SIZE), fill=0
    )
    draw.text(
        (24, 32), f'{pm25}/{norms["pm25"]["good"]}',
        font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), FONT_SIZE), fill=0
    )
    pm25_emote = air_quality_emote(pm25, norms["pm25"])
    image.paste(pm25_emote, (86, 10))

    draw.text(
        (8, 67), f'PM10: ',
        font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), FONT_SIZE), fill=0
    )
    draw.text(
        (24, 93), f'{pm10}/{norms["pm10"]["good"]}',
        font=ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), FONT_SIZE), fill=0
    )
    pm10_emote = air_quality_emote(pm10, norms["pm10"])
    image.paste(pm10_emote, (86, 71))

    epd.displayPartBaseImage(epd.getbuffer(image))

    # logging.info("Clear...")
    # epd.init()
    # epd.Clear(0xFF)

    logging.info("Goto Sleep...")
    epd.sleep()


if __name__ == "__main__":
    pm25, pm10 = load_aqicn_weather_conditions(STATIONS["lodz_czernika"], TOKEN, TODAY)
    if pm25 is not None and pm10 is not None:
        draw(pm25, pm10, AIR_QUALITY_NORMS)
