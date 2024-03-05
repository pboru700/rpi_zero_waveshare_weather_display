#!/bin/bash

cd "$(dirname "$0")";
CWD="$(pwd)"
echo $CWD
python3 weather_display.py --datafile 'data.json' --city 'lodz' --location 'lodz_bartoka' --rotate
