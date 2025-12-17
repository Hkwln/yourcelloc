#!/bin/sh
adb shell dumpsys telephony.registry > ./data/output.txt
python3 getinfo.py
rm ./data/output.txt
rm ./data/cell_towers.csv
