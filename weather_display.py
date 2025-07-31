import os
import sys
import json
import logging
import argparse
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

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
except Exception as exception:
    logging.error("Failed to load: %e", exception)

# Constants
FONT_SIZE = 20

def input_arguments():
    parser = argparse.ArgumentParser(
        description="Get weather conditions.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--datafile", default="data.json", type=str,
        help=("Path to file with JSON formatted data.")
    )
    parser.add_argument(
        "--rotate", action="store_true",
        help=("Rotates image by 180 degrees when provided.")
    )
    parser.add_argument(
        "--city", default="lodz", type=str,
        help=("City to check weather conditions.\n"
              "The city should be available in datafile under geographic_locations.")
    )
    parser.add_argument(
        "--location", default="lodz_bartoka", type=str,
        help=("Location ID for the chosen station.\n"
            "The location should be available in datafile under stations/<api_provider>.")
    )
    parser.add_argument(
        "--source", default="airly", type=str, choices=["airly"],
        help=("Choose source for weather data. Available choices are: airly.")
    )
    return parser.parse_args()

def load_api_data(url, headers=None):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Failed to fetch data from %u: %e", url, e)
        return None
    except json.JSONDecodeError as e:
        logging.error("Failed to decode JSON response from %u: %e", url, e)
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
        logging.error("Failed to load %s weather conditions: %e", provider, e)
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

# def draw_text(image_draw, res_x, res_y, text, angle, size=FONT_SIZE):
#     try:
#         image_draw.text(
#             (res_x, res_y), text, fill=0,
#             font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), size)
#         )
#     except Exception as e:
#         logging.error("Failed to draw text: %e", e)

def draw_text(image_canvas, res_x, res_y, text, angle=90, fill=0, bg_colour=255, padding=10):
    font=ImageFont.truetype(os.path.join(picdir, "Font.ttc"), FONT_SIZE)

    dummy_img = Image.new("RGB", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    text_width, text_height = dummy_draw.textsize(text, font=font, fill=fill)

    img_width = text_width + 2 * padding
    img_height = text_height + 2 * padding
    text_canvas = Image.new("RGB", (img_width, img_height), bg_colour)
    draw = ImageDraw.Draw(text_canvas)

    draw.text((padding, padding), text, font=font, fill=fill)

    rotated = text_canvas.rotate(angle, expand=True)
    image_canvas.paste(rotated, (res_x, res_y))

def draw_image(image_canvas, res_x, res_y, filename, rotation=90):
    try:
        this_image = Image.open(os.path.join(picdir, filename))
        if rotation:
            this_image = this_image.rotate(rotation)
        image_canvas.paste(this_image, (res_x, res_y))
    except Exception as e:
        logging.error("Failed to draw image: %e", e)

def fill_empty_space(canvas, res_x, res_y):
    draw_image(canvas, res_x, res_y, "sun.bmp")
    draw_image(canvas, res_x + 36, res_y + 2, "clouds_advanced_01.bmp")
    draw_image(canvas, res_x + 76, res_y + 4, "clouds_advanced_02.bmp")

def air_quality_emote(quality_level, norm_good, norm_medium):
    try:
        if quality_level <= norm_good:
            return "emote_smile.bmp"
        if norm_good < quality_level <= norm_medium:
            return "emote_meh.bmp"
        return "emote_bad_air.bmp"
    except Exception as e:
        logging.error("Failed to determine air quality emote: %e", e)
        return None

def draw_intersecting_lines(image_canvas, res_x, res_y, width = 4):
    top = res_x*3/4
    middle = res_x/2
    bottom = res_x/4
    shift = width/2
    shifted_top = top - shift
    shifted_middle = middle - shift
    shifted_bottom = bottom - shift
    image_canvas.line([(shifted_top, - 5), (shifted_top, res_y )], fill=0, width=width)
    image_canvas.line([(shifted_middle, - 5), (shifted_middle, res_y)], fill=0, width=width)
    image_canvas.line([(shifted_bottom,  - 5), (shifted_bottom, res_y)], fill=0, width=width)
    return image_canvas

def draw_corners(image_canvas, res_x, res_y, square_image_width = 3):
    draw_image(image_canvas, 0, 0, "corner.bmp")
    draw_image(image_canvas, res_x - square_image_width, 0, "corner.bmp", 270)
    draw_image(image_canvas, 0, res_y - square_image_width, "corner.bmp", 90)
    draw_image(image_canvas, res_x - square_image_width, res_y - square_image_width, "corner.bmp", 180)
    return image_canvas

def draw_norms(text_canvas, res_x, res_y, image_canvas, data):
    try:
        pm25 = data["pm25"]
        pm10 = data["pm10"]
        pm25_norm = data["pm25_norm"]
        pm10_norm = data["pm10_norm"]
    except Exception as e:
        logging.error("Failed to determine weather norms: %e", e)
    # Draw PM2.5 norm, upper left
    draw_image(image_canvas, res_x, res_y, "pm25_icon.bmp")
    draw_image(image_canvas, res_x, res_y + 44, air_quality_emote(pm25, pm25_norm, 2 * pm25_norm))
    draw_text(image_canvas, res_x + 26, res_y + 20, f"{pm25}/{pm25_norm}")

    # Draw PM10 norm, lower left
    draw_image(image_canvas, res_x + 62, res_y, "pm10_icon.bmp")
    draw_image(image_canvas, res_x + 62, res_y + 44, air_quality_emote(pm10, pm10_norm, 2 * pm10_norm))
    draw_text(image_canvas, res_x + 88, res_y + 20, f"{pm10}/{pm10_norm}")
    return text_canvas, image_canvas

def draw_single_condition(param, unit, image_canvas, text_canvas, res_x, res_y, param_filename, font = FONT_SIZE):
    if param:
        draw_text(text_canvas, res_x + 20, res_y, f"{param}{unit}", font)
        draw_image(image_canvas, res_x + 2, res_y + 2, param_filename)
    else:
        fill_empty_space(image_canvas, res_x, res_y)

def draw_conditions(text_canvas, image_canvas, data):
    try:
        temperature = data["temp"]
        humidity = data["humi"]
        pressure = data["pres"]
    except Exception as e:
        logging.error("Failed to determine weather conditions: %e", e)

    # Draw Weather icons, upper right
    fill_empty_space(image_canvas, 134, 6)

    draw_single_condition(temperature, "°C", image_canvas, text_canvas, 132, 24, "termometer.bmp")
    draw_single_condition(humidity, "%", image_canvas, text_canvas, 130, 64, "water_droplet.bmp")
    draw_single_condition(pressure, "hPa", image_canvas, text_canvas, 126, 94, "pressure.bmp", font = 20)

    return text_canvas, image_canvas

def display_image(epd, image_canvas, rotate, rotation = 0):
    try:
        if rotate:
            image_canvas = image_canvas.rotate(rotation)
        epd.displayPartBaseImage(epd.getbuffer(image_canvas))
    except Exception as e:
        logging.error("Failed to draw: %e", e)
    finally:
        logging.info("Powering off the screen")
        epd.sleep()

def get_token(source):
    try:
        return os.environ.get(source.upper())
    except Exception as e:
        logging.error("Failed to set constants: %e", e)
        return None

def parse_airly_data(data):
    values = {}
    data_values = data["current"]["values"]
    data_norms = data["current"]["standards"]
    values["pm25"] = next((v["value"] for v in data_values if v["name"] == "PM25"), None)
    values["pm10"] = next((v["value"] for v in data_values if v["name"] == "PM10"), None)
    values["pres"] = next((v["value"] for v in data_values if v["name"] == "PRESSURE"), None)
    values["humi"] = next((v["value"] for v in data_values if v["name"] == "HUMIDITY"), None)
    values["temp"] = next((v["value"] for v in data_values if v["name"] == "TEMPERATURE"), None)
    values["pm25_norm"] = next((n["limit"] for n in data_norms if n["pollutant"] == "PM25"), None)
    values["pm10_norm"] = next((n["limit"] for n in data_norms if n["pollutant"] == "PM10"), None)
    return values

def main():
    try:
        args = input_arguments()
        token = get_token(args.source)
        with open(args.datafile) as f:
            data = json.load(f)
        geo_locs = data["geographic_locations"]
        stations = data["stations"]
        station = stations[args.source][args.location]
        if args.source == "airly":
            weather_data = get_weather_conditions(
                args.source, args.city, geo_locs, station, token
            )
            weather = parse_airly_data(weather_data)
        epd, image, draw = init_display()
        height = epd.height
        width = epd.width
        # draw = draw_intersecting_lines(draw, height, width, 4)
        # image = draw_corners(image, height, width, 3)
        draw = draw_intersecting_lines(draw, height, width, 4)
        draw, image = draw_norms(draw, 2, 26, image, weather)
        # draw, image = draw_conditions(draw, image, weather)
        display_image(epd, image, args.rotate)
    except Exception as e:
        logging.error("Failed to execute main function: %e", e)

if __name__ == "__main__":
    main()
