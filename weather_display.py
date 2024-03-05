import os
import sys
import requests
import pandas as pd
import json
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

# Load .env variables
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
        "--rotate", action="store_true",
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

def get_weather_conditions(provider, city, geo_location, location_id, token):
    base_urls = {
        "airly": "https://airapi.airly.eu/v2/measurements/",
        "aqicn": "https://api.waqi.info/feed/",
        "openmeteo": "https://api.open-meteo.com/v1/forecast"
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

def air_quality_emote(quality_level, norm_good, norm_medium):
    try:
        if quality_level <= norm_good:
            return Image.open(os.path.join(picdir, 'emote_smile.bmp'))
        elif norm_good < quality_level <= norm_medium:
            return Image.open(os.path.join(picdir, 'emote_meh.bmp'))
        else:
            return Image.open(os.path.join(picdir, 'emote_bad_air.bmp'))
    except Exception as e:
        logging.error(f"Failed to determine air quality emote: {e}")
        return None

def draw_conditions(pm25, pm10, pm25_norm, pm10_norm, pressure, humidity, temperature, rotate=False):
    try:
        logging.info("Initializing")
        epd = epd2in13_V4.EPD()
        epd.init()
        epd.Clear(0xFF)

        logging.info("Drawing on the image")
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)

        # Load pictures
        sun = Image.open(os.path.join(picdir, 'sun.bmp'))
        upper_left_corner = Image.open(os.path.join(picdir, 'corner.bmp'))
        upper_right_corner = upper_left_corner.rotate(270)
        lower_left_corner = upper_left_corner.rotate(90)
        lower_right_corner = upper_left_corner.rotate(180)
        termometer = Image.open(os.path.join(picdir, 'termometer.bmp'))
        water_droplet = Image.open(os.path.join(picdir, 'water_droplet.bmp'))
        pressure_icon = Image.open(os.path.join(picdir, 'pressure.bmp'))
        pm25_icon = Image.open(os.path.join(picdir, 'pm25_icon.bmp'))
        pm10_icon = Image.open(os.path.join(picdir, 'pm10_icon.bmp'))
        calendar = Image.open(os.path.join(picdir, "calendar_big_02.bmp"))
        sun = Image.open(os.path.join(picdir, "sun.bmp"))
        cloud_01 = Image.open(os.path.join(picdir, "clouds_advanced_01.bmp"))
        cloud_02 = Image.open(os.path.join(picdir, "clouds_advanced_02.bmp"))

        def draw_text(x, y, text, size=FONT_SIZE):
            draw.text((x, y), text,font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), size), fill=0)

        draw.line([(0, 59), (250, 59)], fill=0, width=4)
        draw.line([(124, 0), (124, 122)], fill=0, width=4)

        # Draw PM2.5 norm, upper left
        image.paste(pm25_icon, (28, 1))
        pm25_emote = air_quality_emote(pm25, pm25_norm, 2 * pm25_norm)
        if pm25_emote:
            image.paste(pm25_emote, (66, 1))
        draw_text(8, 30, f'{pm25}/{pm25_norm}')

        # Draw PM10 norm, lower left
        image.paste(pm10_icon, (28, 63))
        pm10_emote = air_quality_emote(pm10, pm10_norm, 2 * pm10_norm)
        if pm10_emote:
            image.paste(pm10_emote, (66, 63))
        draw_text(8, 93, f'{pm10}/{pm10_norm}')

        # Draw Weather conditions icons, upper right
        image.paste(sun, (134, 6))
        image.paste(cloud_01, (170, 8))
        image.paste(cloud_02, (210, 10))

        # Draw temperature, himidity and pressure
        if temperature:
            draw_text(156, 28, f"{temperature}°C")
            image.paste(termometer, (132, 26))
        if humidity:
            draw_text(156, 65, f"{humidity}%")
            image.paste(water_droplet, (132, 67))
        if pressure:
            draw_text(146, 93, f"{pressure}hPa", 20)
            image.paste(pressure_icon, (128, 96))
        else:
            draw_text(129, 30, TODAY)

        # Draw corners
        image.paste(upper_left_corner, (0, 0))
        image.paste(upper_right_corner, (247, 0))
        image.paste(lower_left_corner, (0, 119))
        image.paste(lower_right_corner, (247, 119))

        if rotate:
            image = image.rotate(180)

        # Draw elements
        epd.displayPartBaseImage(epd.getbuffer(image))
    except Exception as e:
        logging.error(f"Failed to draw: {e}")
    finally:
        logging.info("Powering off the screen")
        epd.sleep()

if __name__ == "__main__":
    try:
        datafile, rotate, city, location, source = input_arguments()
        with open(datafile) as f:
            data = json.load(f)
        geo_locations = data["geographic_locations"]
        stations = data["stations"]
        air_quality_norms = data["air_quality_norms"]
        weather_data = get_weather_conditions(source, city, geo_locations, stations["airly"][location], AIRLY_TOKEN)
        if weather_data:
            values = weather_data["current"]["values"]
            norms = weather_data["current"]["standards"]
            pm25 = [ v["value"] for v in values if v["name"] == "PM25" ][0]
            pm10 = [ v["value"] for v in values if v["name"] == "PM10" ][0]
            pressure = [ v["value"] for v in values if v["name"] == "PRESSURE" ][0]
            humidity = [ v["value"] for v in values if v["name"] == "HUMIDITY" ][0]
            temperature = [ v["value"] for v in values if v["name"] == "TEMPERATURE" ][0]
            pm25_norm = [ n["limit"] for n in norms if n["pollutant"] == "PM25" ][0]
            pm10_norm = [ n["limit"] for n in norms if n["pollutant"] == "PM10" ][0]
            draw_conditions(pm25, pm10, pm25_norm, pm10_norm, pressure, humidity, temperature, rotate)
    except Exception as e:
        logging.error(f"Failed to execute main function: {e}")
