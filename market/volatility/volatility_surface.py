import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
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
    config_dict = df_config.set_index('Name')['Value'].to_dict()
    df_data = pd.read_excel(full_path, sheet_name="Data")
    asset_spot = market_dict["BTCUSD.SPOT"]
    spotPrice = asset_spot.spotRate

    domYcName = config_dict["DomesticDiscountingCurve"]
    domYc = market_dict[domYcName]
    assetYcName = config_dict["ForeignDiscountingCurve"]
    assetYc = market_dict[assetYcName]

    marketDateStr = config_dict['Date']
    marketDate = pyDateToQlDate(dt.strptime(marketDateStr, "%Y-%m-%d"))

    def calcImpliedVol(row):
        # In BTC, settlement lag is 0
        expiryDate = pyDateToQlDate(dt.strptime(row['ExpiryDate'], "%Y-%m-%d"))
        domDfOption = domYc.discount(expiryDate)
        price = row['Price']
        undisc_price = price / domDfOption

        # underlying futures
        futureExpiryDate = pyDateToQlDate(dt.strptime(row['FutureExpiryDate'], "%Y-%m-%d"))
        domDfUnderlying = domYc.discount(futureExpiryDate)
        assetDfUnderlying = assetYc.discount(futureExpiryDate)
        cp = ql.Option.Call if row['OptionType'] == "Call" else ql.Option.Put
        k = float(row['Strike'])
        f = spotPrice * assetDfUnderlying / domDfUnderlying
        dc = ql.ActualActual(ql.ActualActual.ISDA)
        t = dc.yearFraction(marketDate, expiryDate)
        # only compute strike which is +/- 50% of fwd
        if (k < 0.5 * f) or (k > 1.5 * f):
            return None
        else:
            std = ql.blackFormulaImpliedStdDev(cp, k, f, undisc_price)
            vol = std / np.sqrt(t)
            return vol

    df_data["ImpliedVol"] = df_data.apply(calcImpliedVol, axis=1)

    return
