import requests
import pandas as pd
import json
from datetime import date

geographic_locations = {
    "lodz": {
        "latitude": "51.759445",
        "longitude": "19.457216"
    }
}
today = date.today()

def load_weather_conditions(date):
    url = "https://api.open-meteo.com/v1/forecast"
    url_data_location = "?latitude={latitude}&longitude={longitude}".format(
        latitude=geographic_locations["lodz"]["latitude"],
        longitude=geographic_locations["lodz"]["longitude"]
    )
    url_data_conditions = "&hourly=temperature_2m&current_weather=true"
    url_data_time_frame = "&timezone=GMT&start_date={date}&end_date={date}".format(date=today)
    full_url_data = "{}{}{}{}".format(url,url_data_location,url_data_conditions,url_data_time_frame)
    response = requests.get(full_url_data).json()
    weather_df = pd.DataFrame(response)
    current_weather = weather_df['current_weather']
    return current_weather, weather_df

w1, w2 = load_weather_conditions(today)
print(w2)
