#!/bin/bash

cd "$(dirname "$0")";
CWD="$(pwd)"
echo $CWD
python3 get_weather.py --datafile 'data.json' --city 'lodz' --location 'lodz_bartoka' --rotate
