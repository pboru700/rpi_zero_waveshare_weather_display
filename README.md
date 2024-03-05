# rpi_zero_waveshare_weather

AQICN_TOKEN value can be acquired from https://aqicn.org/data-platform/token/. Put it in .env file:

```
AQICN_TOKEN="xxxxx"
```

# Weather Conditions Display with Waveshare 2,13inch e-Paper HAT screen

This Python script fetches weather conditions from specified sources and displays them on a Waveshare 2.13inch Touch e-Paper HAT screen along with additional images. It supports fetching data from Airly, and AQICN APIs.

Prerequisites

Python 3.x installed on your system
Waveshare 2.13inch Touch e-Paper HAT screen
Environment variables set up for API tokens (AQICN_TOKEN and AIRLY_TOKEN)
requests, pandas, dotenv, and PIL Python packages installed
Geographic locations and station IDs defined in a JSON file (default: data.json)
Installation

Clone this repository or download the script.
Install required Python packages using pip install -r requirements.txt.
Usage

bash
Copy code
python weather_display.py [--datafile DATAFILE] [--rotate] [--city CITY] [--location LOCATION]
--datafile: Path to the JSON file containing geographic locations and station IDs. Default is data.json.
--rotate: Rotate the image by 180 degrees (optional).
--city: Specify the city for weather conditions. Default is lodz.
--location: Specify the location ID for the chosen station. Default is lodz_bartoka.
Example

bash
Copy code
python weather_display.py --rotate --city warsaw --location warsaw_station
This command will display weather conditions for Warsaw, Poland, using the station with ID warsaw_station and rotate the output image.

Notes

Make sure to set up the required environment variables for API tokens.
Ensure the specified city and location ID are available in the provided data file.
Author

This script was created by [Your Name]. Feel free to contact [Your Email] for any questions or feedback.
