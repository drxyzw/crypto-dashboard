import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import os

from utils.convention import *
PROCESSED_DIR = "./data_processed"
#     if len(df_data):
#         with pd.ExcelWriter() as ew:
#             df_config.to_excel(ew, sheet_name="Config", index=False)
#             df_data.to_excel(ew, sheet_name="Data", index=False)

def implied_volatility(row):
    return 0.1

def build_volatility_surface(market_dict):
    if not market_dict:
        print("Input market is empty")
        return None
    ql_date = ql.Settings.instance().evaluationDate
    py_date = qlDateToPyDate(ql_date)
    YYYYMMDD = py_date.strftime("%Y%m%d")

    PROCESSED_FILE = f"BTCUSDOPTION_{YYYYMMDD}.xlsx"
    directory = PROCESSED_DIR + f"./{YYYYMMDD}"
    full_path = directory + "/" + PROCESSED_FILE
    df_config = pd.read_excel(full_path, sheet_name="Config")
    df_data = pd.read_excel(full_path, sheet_name="Data")

    asset_spot = market_dict[df_config[""]]
    return
