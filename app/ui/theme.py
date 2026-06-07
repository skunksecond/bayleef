import os
import json

script_dir = os.path.dirname(os.path.abspath(__file__))

with open(script_dir + "/theme.json") as f:
    THEME = json.load(f)