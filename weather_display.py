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
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
picdir: str = os.path.join(BASE_DIR, "pic")
libdir: str = os.path.join(BASE_DIR, "lib")
dotenvdir: str = os.path.join(BASE_DIR, ".env")

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

# Load .env variables
try:
    load_dotenv(dotenvdir)
except Exception as e:
    logging.error(f"Failed to load: {e}")

# Constants
FONT_SIZE = 24

def input_arguments():
    parser = argparse.ArgumentParser(description="Get weather conditions.")
    parser.add_argument(
        "--datafile", default="data.json", type=str,
        help="Path to file with JSON formatted data."
    )
    parser.add_argument(
        "--rotate", action="store_true",
        help="Rotates image by 180 degrees when provided."
    )
    parser.add_argument(
        "--city", default="lodz", type=str,
        help="City to check weather conditions. The city should be available in datafile under geographic_locations."
    )
    parser.add_argument(
        "--location", default="lodz_bartoka", type=str,
        help="Location ID for the chosen station. The location should be available in datafile under stations/<api_provider>."
    )
    parser.add_argument(
        "--source", default="airly", type=str, choices=["airly"],
        help="Choose source for weather data. Available choices are: airly."
    )
    return parser.parse_args()

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
        "airly": "https://airapi.airly.eu/v2/measurements/"
    }
    lat = geo_location[city]['latitude']
    lon = geo_location[city]['longitude']
    urls = {
        "airly": f"point?lat={lat}&lng={lon}&locationId={location_id}"
    }
    use_headers = {
        "airly": True
    }
    try:
        base_url = base_urls.get(provider)
        url = base_url + urls.get(provider)
        headers = {"Accept": "application/json", "apikey": token} if use_headers[provider] else None
        data = load_api_data(url, headers)
        return data
    except Exception as e:
        logging.error(f"Failed to load {provider} weather conditions: {e}")
        return None

def init_display():
    logging.info("Initializing")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    logging.info("Drawing on the image")
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    return epd, image, draw

def draw_text(image_draw, x, y, text, size=FONT_SIZE):
    try:
        image_draw.text(
            (x, y), text, fill=0,
            font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), size)
        )
    except Exception as e:
        logging.error(f"Failed to draw text: {e}")

def draw_image(canvas, x, y, filename, rotation=None):
    try:
        this_image = Image.open(os.path.join(picdir, filename))
        if rotation:
            this_image = this_image.rotate(rotation)
        canvas.paste(this_image, (x, y))
    except Exception as e:
        logging.error(f"Failed to draw image: {e}")

def fill_empty_space(canvas, x, y):
    draw_image(canvas, x, y, "sun.bmp")
    draw_image(canvas, x + 36, y + 2, "clouds_advanced_01.bmp")
    draw_image(canvas, x + 76, y + 4, "clouds_advanced_02.bmp")

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

def draw_intersecting_lines(draw):
    draw.line([(0, 59), (250, 59)], fill=0, width=4)
    draw.line([(124, 0), (124, 122)], fill=0, width=4)
    return draw

def draw_corners(image):
    draw_image(image, 0, 0, "corner.bmp")
    draw_image(image, 248, 0, "corner.bmp", 270)
    draw_image(image, 0, 119, "corner.bmp", 90)
    draw_image(image, 248, 119, "corner.bmp", 180)
    return image

def draw_norms(draw, image, pm25, pm10, pm25_norm, pm10_norm):
    # Draw PM2.5 norm, upper left
    draw_image(image, 28, 4, "pm25_icon.bmp")
    draw_image(image, 66, 4, air_quality_emote(pm25, pm25_norm, 2 * pm25_norm))
    draw_text(draw, 6, 33, f"{pm25}/{pm25_norm}")

    # Draw PM10 norm, lower left
    draw_image(image, 28, 66, "pm10_icon.bmp")
    draw_image(image, 66, 66, air_quality_emote(pm10, pm10_norm, 2 * pm10_norm))
    draw_text(draw, 6, 96, f"{pm10}/{pm10_norm}")
    return draw, image

def draw_conditions(draw, image, pressure=None, humidity=None, temperature=None):
    # Draw Weather icons, upper right
    fill_empty_space(image, 134, 6)

    # Draw temperature, humidity, and pressure
    if temperature:
        draw_text(draw, 156, 28, f"{temperature}°C")
        draw_image(image, 132, 26, "termometer.bmp")
    else:
        fill_empty_space(image, 134, 26)
    if humidity:
        draw_text(draw, 156, 66, f"{humidity}%")
        draw_image(image, 132, 68, "water_droplet.bmp")
    else:
        fill_empty_space(image, 132, 68)
    if pressure:
        draw_text(draw, 146, 96, f"{pressure}hPa", 20)
        draw_image(image, 128, 99, "pressure.bmp")
    else:
        draw_text(draw, 129, 30, date.today().strftime("%d-%m-%Y"))

    return draw, image

def display_image(epd, draw, image, rotate):
    try:
        if rotate:
            image = image.rotate(180)
        epd.displayPartBaseImage(epd.getbuffer(image))
    except Exception as e:
        logging.error(f"Failed to draw: {e}")
    finally:
        logging.info("Powering off the screen")
        epd.sleep()

def get_tokens():
    try:
        return {
            "airly": os.environ.get("AIRLY_TOKEN")
        }
    except Exception as e:
        logging.error(f"Failed to set constants: {e}")
        return None

def parse_airly_data(data):
    values = {}
    data_values = data["current"]["values"]
    data_norms = data["current"]["standards"]
    values["pm25"] = next((v["value"] for v in data_values if v["name"] == "PM25"), None)
    values["pm10"] = next((v["value"] for v in data_values if v["name"] == "PM10"), None)
    values["pressure"] = next((v["value"] for v in data_values if v["name"] == "PRESSURE"), None)
    values["humidity"] = next((v["value"] for v in data_values if v["name"] == "HUMIDITY"), None)
    values["temperature"] = next((v["value"] for v in data_values if v["name"] == "TEMPERATURE"), None)
    values["pm25_norm"] = next((n["limit"] for n in data_norms if n["pollutant"] == "PM25"), None)
    values["pm10_norm"] = next((n["limit"] for n in data_norms if n["pollutant"] == "PM10"), None)
    return values

def main(tokens):
    try:
        args = input_arguments()
        with open(args.datafile) as f:
            data = json.load(f)
        geo_locs = data["geographic_locations"]
        stations = data["stations"]
        air_norms = data["air_quality_norms"]
        weather_data = get_weather_conditions(
            args.source, args.city, geo_locs, stations["airly"][args.location], tokens[args.source]
        )
        if weather_data:
            if args.source == "airly":
                weather = parse_airly_data(weather_data)
            epd, image, draw = init_display()
            draw = draw_intersecting_lines(draw)
            image = draw_corners(image)
            draw, image = draw_norms(draw, image, weather["pm25"], weather["pm10"], weather["pm25_norm"], weather["pm10_norm"])
            draw, image = draw_conditions(draw, image, weather["pressure"], weather["humidity"], weather["temperature"])
            display_image(epd, draw, image, args.rotate)
    except Exception as e:
        logging.error(f"Failed to execute main function: {e}")

if __name__ == "__main__":
    tokens = get_tokens()
    main(tokens)
