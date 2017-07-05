# General configuration
import json

with open('settings.json', 'r') as f:
    settings = json.load(f)

network_params = settings[0]
environment_params = settings[1]

centrality_param = {}
partition_param={}
leaders={}

