#!/bin/bash

cd "$(dirname "$0")";
CWD="$(pwd)"
echo $CWD
python3 get_weather.py
