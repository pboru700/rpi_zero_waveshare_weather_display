import requests
import pandas as pd
import json
from datetime import date
import folium
from folium.plugins import HeatMap
import os

geographic_locations = {
    "lodz": {
        "latitude": "51.759445",
        "longitude": "19.457216"
    }
}
stations = {
    "lodz_czernika": "8121"
}
token = os.getenv(AQICN_TOKEN)
today = date.today()

def load_aqicn_weather_conditions(station_id, token):
    base_url = "https://api.waqi.info"
    trail_url = "/feed/@{}/?token={}".format(station_id, token)
    full_url = base_url + trail_url
    return pd.read_json(full_url)
    # my_data = pd.read_json(base_url + trail_url) # Join parts of URL
    # print('columns->', my_data.columns) #2 cols ‘status’ and ‘data’

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

if __name__ == "__main__":
    print("---------------------")
    load_aqicn_weather_conditions(stations["lodz_czernika"], token)
