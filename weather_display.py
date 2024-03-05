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
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "pic")
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib")
dotenvdir = os.path.join(os.path.dirname(__file__), ".env")

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

# Load .env variables
try:
    load_dotenv(dotenvdir)
except Exception as e:
    logging.error(f"Failed to load : {e}")

# Constants
FONT_SIZE = 24

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

def draw_text(image_draw, x, y, text, size=FONT_SIZE):
    image_draw.text(
        (x, y), text, fill=0,
        font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), size)
    )

def draw_image(canvas, x, y, filename, rotation=None):
    this_image = Image.open(os.path.join(picdir, filename))
    if rotation:
        this_image.rotate(rotation)
        canvas.paste(this_image, (x, y))

def air_quality_emote(quality_level, norm_good, norm_medium):
    try:
        if quality_level <= norm_good:
            return "emote_smile.bmp"
        elif norm_good < quality_level <= norm_medium:
            return "emote_meh.bmp"
        else:
            return "emote_bad_air.bmp"
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
        image = Image.new("1", (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)

        # Draw intersecting lines
        draw.line([(0, 59), (250, 59)], fill=0, width=4)
        draw.line([(124, 0), (124, 122)], fill=0, width=4)

        # Draw PM2.5 norm, upper left
        draw_image(image, 28, 1, "pm25_icon.bmp")
        draw_image(image, 66, 1, air_quality_emote(pm25, pm25_norm, 2 * pm25_norm))
        draw_text(draw, 8, 30, f"{pm25}/{pm25_norm}")

        # Draw PM10 norm, lower left
        draw_image(image, 28, 63, "pm10_icon.bmp")
        draw_image(image, 28, 1, air_quality_emote(pm10, pm10_norm, 2 * pm10_norm))
        draw_text(draw, 8, 93, f"{pm10}/{pm10_norm}")

        # Draw Weather icons, upper right
        draw_image(image, 134, 6, "sun.bmp")
        draw_image(image, 170, 8, "clouds_advanced_01.bmp")
        draw_image(image, 210, 10, "clouds_advanced_02.bmp")

        # Draw temperature, himidity and pressure
        if temperature:
            draw_text(draw, 156, 28, f"{temperature}°C")
            draw_image(image, 132, 26, "termometer.bmp")
        if humidity:
            draw_text(draw, 156, 65, f"{humidity}%")
            draw_image(image, 132, 67, "water_droplet.bmp")
        if pressure:
            draw_text(draw, 146, 93, f"{pressure}hPa", 20)
            draw_image(image, 128, 96, "pressure.bmp")
        else:
            draw_text(draw, 129, 30, date.today().strftime("%d-%m-%Y"))

        # Draw corners
        draw_image(image, 0, 0, "corner.bmp")
        draw_image(image, 247, 0, "corner.bmp", 270)
        draw_image(image, 0, 119, "corner.bmp", 90)
        draw_image(image, 247, 119, "corner.bmp", 180)

        if rotate:
            image = image.rotate(180)

        # Display image
        epd.displayPartBaseImage(epd.getbuffer(image))
    except Exception as e:
        logging.error(f"Failed to draw: {e}")
    finally:
        logging.info("Powering off the screen")
        epd.sleep()

if __name__ == "__main__":
    try:
        aqicn_token = os.environ.get("AQICN_TOKEN")
        airly_token = os.environ.get("AIRLY_TOKEN")
    except Exception as e:
        logging.error(f"Failed to set constants: {e}")

    try:
        datafile, rotate, city, location, source = input_arguments()
        with open(datafile) as f:
            data = json.load(f)
        geo_locs = data["geographic_locations"]
        stations = data["stations"]
        air_norms = data["air_quality_norms"]
        weather_data = get_weather_conditions(
            source, city, geo_locs, stations["airly"][location], airly_token
        )
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
            draw_conditions(
                pm25, pm10, pm25_norm, pm10_norm,
                pressure, humidity, temperature, rotate
            )
    except Exception as e:
        logging.error(f"Failed to execute main function: {e}")
