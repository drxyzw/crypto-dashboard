import QuantLib as ql
import pandas as pd

from utils.file import *
from market.yield_curve.parse_yield_curve import *
from market.assset.parse_spot import *

PROCESSED_DIR = "./data_processed"
DATE = "20250613"
PROCESSED_DIR_DATE = PROCESSED_DIR+ "/" + DATE

# load all excels from a directory
files = getAllFilesInDirectory(PROCESSED_DIR_DATE)
market_raw_dfs = {}
for file in files:
    config_sheet = pd.read_excel(file, sheet_name="Config")
    config_dict = convertDataframeToDictionary(config_sheet)
    marketDate = config_dict['Date']
    name = config_dict['Name']
    dataType = config_dict['Type'].upper()
    dataSubype = config_dict['SubType'].upper()
    # only filter market data. Option prices are handles elsewhere
    if dataType != "MARKET" or dataSubype == "OPTION":
        continue
    
    data_sheet = pd.read_excel(file, sheet_name="Data")

    market_raw_dict = config_dict.copy()
    market_raw_dict['Data'] = data_sheet
    market_raw_dfs[name] = market_raw_dict

parsed_market_objects = {}
# choose a first group (yield curve without dependency)
yc_no_dependency = {}
allowed_keys_for_no_dependency = {'Type', 'SubType', 'Date', 'Name', 'CCY', 'Data'}
for name, mkt_object in market_raw_dfs.items():
    keys = set(mkt_object.keys())
    if (allowed_keys_for_no_dependency == keys) or (allowed_keys_for_no_dependency - keys):
        yc_no_dependency[name] = mkt_object
        parsed_yc = parse_yield_curve(mkt_object, parsed_market_objects)
        parsed_market_objects[name] = parsed_yc

# choose a second group (asset spot)
spots = {}
for name, mkt_object in market_raw_dfs.items():
    subtype = mkt_object['SubType'].upper()
    if subtype == "SPOT":
        spots[name] = mkt_object
        parsed_spot = parse_spot(mkt_object, parsed_market_objects)
        parsed_market_objects[name] = parsed_spot

# choose a third group (yield curve with dependency)
yc_with_dependency = {}
for name in market_raw_dfs.keys() - yc_no_dependency.keys() - spots.keys():
    mkt_object = market_raw_dfs[name]
    yc_with_dependency[name] = mkt_object
    parsed_yc = parse_yield_curve(mkt_object, parsed_market_objects)
    parsed_market_objects[name] = parsed_yc

# store other market objects
others = {}
for name in market_raw_dfs.keys() - yc_no_dependency.keys() - spots.keys() - yc_with_dependency.keys():
    mkt_object = market_raw_dfs[name]
    others[name] = mkt_object



print("Finished loading")




