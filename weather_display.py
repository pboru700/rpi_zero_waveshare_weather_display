import os
import sys
import json
import logging
import argparse
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.DEBUG)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
PICDIR = os.path.join(BASE_DIR, "pic")
LIBDIR = os.path.join(BASE_DIR, "lib")

if os.path.exists(LIBDIR):
    sys.path.append(LIBDIR)

from waveshare_epd import epd2in13_V4

try:
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception as e:
    logging.error("Failed to load .env: %s", e)

FONT_SIZE = 24


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get weather conditions.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--datafile", default="data.json", type=str,
        help="Path to file with JSON formatted data.",
    )
    parser.add_argument(
        "--rotate", action="store_true",
        help="Rotates image by 180 degrees when provided.",
    )
    parser.add_argument(
        "--city", default="lodz", type=str,
        help=(
            "City to check weather conditions.\n"
            "The city should be available in datafile under geographic_locations."
        ),
    )
    parser.add_argument(
        "--location", default="lodz_bartoka", type=str,
        help=(
            "Location ID for the chosen station.\n"
            "The location should be available in datafile under stations/<api_provider>."
        ),
    )
    parser.add_argument(
        "--source", default="airly", type=str, choices=["airly"],
        help="Choose source for weather data. Available choices are: airly.",
    )
    return parser.parse_args()


def fetch_json(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Failed to fetch data from %s: %s", url, e)
        return None
    except json.JSONDecodeError as e:
        logging.error("Failed to decode JSON from %s: %s", url, e)
        return None


def get_weather_conditions(provider, city, geo_locations, location_id, token):
    lat = geo_locations[city]["latitude"]
    lon = geo_locations[city]["longitude"]
    if provider == "airly":
        url = f"https://airapi.airly.eu/v2/measurements/point?lat={lat}&lng={lon}&locationId={location_id}"
        return fetch_json(url, {"Accept": "application/json", "apikey": token})
    return None


def init_display():
    logging.info("Initializing display")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)
    logging.info("Drawing on the image")
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    return epd, image, draw


def draw_text(draw, x, y, text, size=FONT_SIZE):
    try:
        font = ImageFont.truetype(os.path.join(PICDIR, "Font.ttc"), size)
        draw.text((x, y), text, fill=0, font=font)
    except Exception as e:
        logging.error("Failed to draw text: %s", e)


def draw_image(canvas, x, y, filename, rotation=None):
    try:
        img = Image.open(os.path.join(PICDIR, filename))
        if rotation:
            img = img.rotate(rotation)
        canvas.paste(img, (x, y))
    except Exception as e:
        logging.error("Failed to draw image: %s", e)


def fill_empty_space(canvas, x, y):
    draw_image(canvas, x, y, "sun.bmp")
    draw_image(canvas, x + 36, y + 2, "clouds_advanced_01.bmp")
    draw_image(canvas, x + 76, y + 4, "clouds_advanced_02.bmp")


def air_quality_emote(value, good_threshold, medium_threshold):
    if value <= good_threshold:
        return "emote_smile.bmp"
    if value <= medium_threshold:
        return "emote_meh.bmp"
    return "emote_bad_air.bmp"


def draw_intersecting_lines(draw, canvas_w, canvas_h, width=4):
    half = width // 2
    x_mid = canvas_w // 2 - half
    y_mid = canvas_h // 2 - half
    draw.line([(1, y_mid), (canvas_w, y_mid)], fill=0, width=width)
    draw.line([(x_mid, 1), (x_mid, canvas_h)], fill=0, width=width)
    return draw


def draw_corners(canvas, canvas_w, canvas_h, corner_size=3):
    draw_image(canvas, 0, 0, "corner.bmp")
    draw_image(canvas, canvas_w - corner_size, 0, "corner.bmp", 270)
    draw_image(canvas, 0, canvas_h - corner_size, "corner.bmp", 90)
    draw_image(canvas, canvas_w - corner_size, canvas_h - corner_size, "corner.bmp", 180)
    return canvas


def draw_norms(draw, canvas, x, y, data):
    pm25 = data["pm25"]
    pm10 = data["pm10"]
    pm25_norm = data["pm25_norm"]
    pm10_norm = data["pm10_norm"]

    # PM2.5 — upper left quadrant
    draw_image(canvas, x + 22, y, "pm25_icon.bmp")
    draw_image(canvas, x + 62, y, air_quality_emote(pm25, pm25_norm, 2 * pm25_norm))
    draw_text(draw, x + 4, y + 29, f"{pm25}/{pm25_norm}")

    # PM10 — lower left quadrant
    draw_image(canvas, x + 22, y + 62, "pm10_icon.bmp")
    draw_image(canvas, x + 62, y + 62, air_quality_emote(pm10, pm10_norm, 2 * pm10_norm))
    draw_text(draw, x + 4, y + 92, f"{pm10}/{pm10_norm}")

    return draw, canvas


def draw_single_condition(value, unit, canvas, draw, x, y, icon_file, font=FONT_SIZE):
    if value:
        draw_text(draw, x + 20, y, f"{value}{unit}", font)
        draw_image(canvas, x + 2, y + 2, icon_file)
    else:
        fill_empty_space(canvas, x, y)


def draw_conditions(draw, canvas, data):
    temperature = data["temp"]
    humidity = data["humi"]
    pressure = data["pres"]

    # Weather readings — right half of display
    fill_empty_space(canvas, 134, 6)
    draw_single_condition(temperature, "°C", canvas, draw, 132, 24, "termometer.bmp")
    draw_single_condition(humidity, "%", canvas, draw, 130, 64, "water_droplet.bmp")
    draw_single_condition(pressure, "hPa", canvas, draw, 126, 94, "pressure.bmp", font=20)

    return draw, canvas


def display_image(epd, canvas, rotate):
    try:
        if rotate:
            canvas = canvas.rotate(180)
        epd.displayPartBaseImage(epd.getbuffer(canvas))
    except Exception as e:
        logging.error("Failed to display image: %s", e)
    finally:
        logging.info("Powering off the screen")
        epd.sleep()


def get_token(source):
    return os.environ.get(source.upper())


def parse_airly_data(data):
    values = data["current"]["values"]
    norms = data["current"]["standards"]

    def find_value(name):
        return next((v["value"] for v in values if v["name"] == name), None)

    def find_norm(pollutant):
        return next((n["limit"] for n in norms if n["pollutant"] == pollutant), None)

    return {
        "temp": find_value("TEMPERATURE"),
        "humi": find_value("HUMIDITY"),
        "pres": find_value("PRESSURE"),
        "pm25": find_value("PM25"),
        "pm10": find_value("PM10"),
        "pm25_norm": find_norm("PM25"),
        "pm10_norm": find_norm("PM10"),
    }


def main():
    try:
        args = parse_args()
        token = get_token(args.source)

        with open(args.datafile) as f:
            data = json.load(f)

        geo_locs = data["geographic_locations"]
        station = data["stations"][args.source][args.location]

        weather_data = get_weather_conditions(args.source, args.city, geo_locs, station, token)
        weather = parse_airly_data(weather_data)

        epd, image, draw = init_display()
        draw = draw_intersecting_lines(draw, epd.height, epd.width, 4)
        image = draw_corners(image, epd.height, epd.width, 3)
        draw, image = draw_norms(draw, image, 6, 4, weather)
        draw, image = draw_conditions(draw, image, weather)
        display_image(epd, image, args.rotate)

    except Exception as e:
        logging.error("Failed to execute main: %s", e)


if __name__ == "__main__":
    main()
