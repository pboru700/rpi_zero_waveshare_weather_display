import os
import sys
import requests
import pandas as pd
from datetime import date
from dotenv import load_dotenv
import logging
from PIL import Image, ImageDraw, ImageFont
import argparse

logging.basicConfig(level=logging.DEBUG)

# Directories
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
dotenvdir = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

# Load environment variables
try:
    load_dotenv(dotenvdir)
except Exception as e:
    logging.error(f"Failed to load : {e}")

# Constants
try:
    AQICN_TOKEN = os.environ.get("AQICN_TOKEN")
    AIRLY_TOKEN = os.environ.get("AIRLY_TOKEN")
    FONT_SIZE = 24
except Exception as e:
    logging.error(f"Failed to set constants: {e}")

# Date
try:
    TODAY = date.today().strftime("%d-%m-%Y")
except Exception as e:
    logging.error(f"Failed to set date: {e}")

def input_arguments():
    parser = argparse.ArgumentParser(description="Get weather conditions.")
    parser.add_argument(
        "--datafile", default="data.json", type=str,
        help="Path to file with json formatted data."
    )
    parser.add_argument(
        "--rotate", action="store_true", type=str,
        help="Rotates image by 180 degrees when provided"
    )
    parser.add_argument(
        "--city", default="lodz", type=str,
        help="City to check weather conditions, city should be available in datafile under geographic_locations"
    )
    parser.add_argument(
        "--location", default="lodz_bartoka", type=str,
        help="Location ID for chosen station, location should be available in datafile under stations/<api_provider>"
    )
    parser.add_argument(
        "--source", default="airly", type=str, choices=["airly", "aqicn"],
        help="Chose source for weather data, available choices are: airly, aqicn"
    )
    args = parser.parse_args()
    return args.datafile, args.rotate, args.city, args.location, args.source

def load_api_data(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch data from {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response from {url}: {e}")
        return None

def load_weather_conditions(provider, city, location_id, token):
    base_urls = {
        "airly": "https://airapi.airly.eu/v2/measurements/",
        "aqicn": "https://api.waqi.info/feed/"
    }
    urls = {
        "airly": f"point?lat={geo_location[city]['latitude']}&lng={geo_location[city]['longitude']}&locationId={location_id}",
        "aqicn": f"{location_id}/?token={token}"
    }
    try:
        base_url = base_urls.get(provider)
        url = base_url + urls.get(provider)
        headers = {"Accept": "application/json", "apikey": token} if provider == "airly" else None
        data = load_api_data(url, headers)
        return data
    except Exception as e:
        logging.error(f"Failed to load {provider} weather conditions: {e}")
        return None

def draw_conditions(pm25, pm10, pm25_norm, pm10_norm, pressure, humidity, temperature, rotate=False):
    try:
        epd = epd2in13_V4.EPD()
        epd.init()
        epd.Clear(0xFF)

        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)

        calendar = Image.open(os.path.join(picdir, "calendar_big_02.bmp"))
        sun = Image.open(os.path.join(picdir, "sun.bmp"))
        cloud_01 = Image.open(os.path.join(picdir, "clouds_advanced_01.bmp"))
        cloud_02 = Image.open(os.path.join(picdir, "clouds_advanced_02.bmp"))

        # Load other images

        def draw_text(x, y, text, size=FONT_SIZE):
            draw.text((x, y), text,font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), size), fill=0)

        draw.line([(0, 59), (250, 59)], fill=0, width=4)
        draw.line([(124, 0), (124, 122)], fill=0, width=4)

        if rotate:
            image = image.rotate(180)

        # Draw elements
        epd.displayPartBaseImage(epd.getbuffer(image))
    except Exception as e:
        logging.error(f"Failed to draw: {e}")
    finally:
        # Cut of power to screen
        epd.sleep()

if __name__ == "__main__":
    try:
        datafile, rotate, city, location, source = input_arguments()
        with open(datafile) as f:
            DATA = json.load(f)
        GEO_LOCATIONS = DATA["geographic_locations"]
        STATIONS = DATA["stations"]
        AIR_QUALITY_NORMS = DATA["air_quality_norms"]
        weather_data = load_weather_conditions(source, city, STATIONS["airly"][location], AIRLY_TOKEN)
        if weather_data:
            pm25 = weather_data.get("current", {}).get("values", {}).get("pm25")
            pm10 = weather_data.get("current", {}).get("values", {}).get("pm10")
            pm25_norm = AIR_QUALITY_NORMS["pm25"]["good"]
            pm10_norm = AIR_QUALITY_NORMS["pm10"]["good"]
            pressure = weather_data.get("current", {}).get("values", {}).get("PRESSURE")
            humidity = weather_data.get("current", {}).get("values", {}).get("HUMIDITY")
            temperature = weather_data.get("current", {}).get("values", {}).get("TEMPERATURE")
            draw_conditions(pm25, pm10, pm25_norm, pm10_norm, pressure, humidity, temperature, rotate)
    except Exception as e:
        logging.error(f"Failed to execute main function: {e}")
