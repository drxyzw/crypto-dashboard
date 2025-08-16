import QuantLib as ql
import pandas as pd
from datetime import datetime as dt

from utils.file import *
from utils.convention import *
from market.yield_curve.parse_yield_curve import *
from market.assset_index.parse_spot import *

PROCESSED_DIR = "./data_processed"
# DATE = "20250613"

def loadMarket(py_date, names = []):
    print(f"Finished loading fixing")
    loadFixing()

    YYYYMMDD = dt.strftime(py_date, "%Y%m%d")
    processed_dir_with_date = PROCESSED_DIR+ "/" + YYYYMMDD

    ql.Settings.instance().evaluationDate = pyDateToQlDate(py_date)

    # load all excels from a directory
    files_to_exclude = ["VOLSURFACE", "IMPLIEDVOL", "QPROBABILITY"]
    files = getAllFilesInDirectory(processed_dir_with_date)
    market_raw_dfs = {}
    for file in files:
        if any([kw in file for kw in files_to_exclude]):
            continue
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
        if len(names) == 0 or name in names:
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
        # to add functions to parse other markt objects
        # parsed_market_objects[name] = parsed_yc

    print(f"Finished loading on {YYYYMMDD}")
    return parsed_market_objects

def loadFixing():
    # load fixing
    FIXING_DIRECTORY = "./data_raw"
    sofr_file_name = FIXING_DIRECTORY + "/SOFR_latest.xlsx"
    df_sofr = pd.read_excel(sofr_file_name)
    
    # parse
    df_sofr["Date"] = df_sofr["Date"].map(lambda x: YYYYMMDDHyphenToQlDate(x))

    sofr_index = SOFR_index()
    sofr_index.addFixings(df_sofr["Date"].values, df_sofr["Rate"].values)
    
    print("Fixing has been set.")