import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression

from utils.convention import *
PROCESSED_DIR = "./data_processed"
#     if len(df_data):
#         with pd.ExcelWriter() as ew:
#             df_config.to_excel(ew, sheet_name="Config", index=False)
#             df_data.to_excel(ew, sheet_name="Data", index=False)
FUTURE_CHECK = True
RAISE_OR_PRINT = False
EPS = 1.e-3

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

    if not os.path.exists(full_path):
        return None
    
    df_config = pd.read_excel(full_path, sheet_name="Config")
    config_dict = df_config.set_index('Name')['Value'].to_dict()
    df_data = pd.read_excel(full_path, sheet_name="Data")
    if not "BTCUSD.SPOT" in market_dict.keys():
        return None
    asset_spot = market_dict["BTCUSD.SPOT"]
    spotPrice = asset_spot.spotRate

    domYcName = config_dict["DomesticDiscountingCurve"]
    assetYcName = config_dict["ForeignDiscountingCurve"]
    if (not domYcName in market_dict.keys()) or (not assetYcName in market_dict.keys()):
        return None
    domYc = market_dict[domYcName]
    assetYc = market_dict[assetYcName]

    marketDateStr = config_dict['Date']
    pyMarketDate = dt.strptime(marketDateStr, "%Y-%m-%d")
    marketDate = pyDateToQlDate(pyMarketDate)

    def implied_volatility(row):
        # In BTC, settlement lag is 0
        expiryDate = pyDateToQlDate(dt.strptime(row['ExpiryDate'], "%Y-%m-%d"))
        if expiryDate <= marketDate:
            return None
        domDfOption = domYc.discount(expiryDate)
        assetDfOption = assetYc.discount(expiryDate)
        price = row['Price']
        undisc_price = price / domDfOption

        # underlying futures
        futureExpiryDate = pyDateToQlDate(dt.strptime(row['FutureExpiryDate'], "%Y-%m-%d"))
        if futureExpiryDate <= marketDate  or futureExpiryDate <= expiryDate:
            return None
        domDfUnderlying = domYc.discount(futureExpiryDate)
        assetDfUnderlying = assetYc.discount(futureExpiryDate)
        cp = ql.Option.Call if row['OptionType'] == "Call" else ql.Option.Put
        k = float(row['Strike'])
        dfRatio = domDfUnderlying / domDfOption 
        # dfRatio = assetDfOption / assetDfUnderlying
        # dfRatio = 1.0
        # f = dfRatio * (spotPrice * assetDfUnderlying / domDfUnderlying)
        f = spotPrice * assetDfUnderlying / domDfUnderlying
        dc = ql.ActualActual(ql.ActualActual.ISDA)
        t = dc.yearFraction(marketDate, expiryDate)

        if cp == ql.Option.Call:
            synthCall = undisc_price
            synthPut = undisc_price - f + k
        else:
            synthCall = undisc_price + f - k
            synthPut = undisc_price
            
        # only compute strike which is +/- 50% of fwd
        if (k < 0.5 * f) or (k > 1.5 * f):
            return None
        else:
            if synthCall > 0 and synthPut > 0:
                std = ql.blackFormulaImpliedStdDev(cp, k, f, undisc_price)
                vol = std / np.sqrt(t)
                return vol
            else:
                return None

    df_data["ImpliedVol"] = df_data.apply(implied_volatility, axis=1)

    if FUTURE_CHECK:
        ols_model = LinearRegression()
        for expiryDate in df_data['ExpiryDate'].unique():
            qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
            if qlExpiryDate <= marketDate:
                continue
            df_data_expiry_date = df_data[(df_data['ExpiryDate'] == expiryDate)]
            for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
                qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
                if qlFutureExpiryDate <= marketDate  or qlFutureExpiryDate <= qlExpiryDate:
                    continue
                # from linear regression, compute DF for option expiry and underlying future
                df_data_f_expiry_date = df_data_expiry_date[(df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)]
                strike = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Call"]["Strike"].values
                call = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Call"]["Price"].values
                put = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Put"]["Price"].values
                # y = call - put = DF*(F - K) = -DF * K + (DF*F)
                # a = -DF, b = DF*F
                # DF = -a, F = b / DF
                x = [[k] for k in strike]
                y = call - put
                ols_model.fit(x, y)
                a = ols_model.coef_[0]
                b = ols_model.intercept_
                domDfOption_ref = -a
                f_ref = b / domDfOption_ref

                # DF for option expiry from yield curve
                qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
                domDfOption = domYc.discount(qlExpiryDate)
                assetDfOption = assetYc.discount(qlExpiryDate)

                # underlying futures from yield curve
                qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
                domDfUnderlying = domYc.discount(qlFutureExpiryDate)
                assetDfUnderlying = assetYc.discount(qlFutureExpiryDate)
                # dfRatio = assetDfOption / assetDfUnderlying
                # dfRatio = domDfUnderlying / domDfOption 
                # dfRatio = 1.0
                # f = dfRatio * (spotPrice * assetDfUnderlying / domDfUnderlying)
                f = spotPrice * assetDfUnderlying / domDfUnderlying

                # EPS
                domDfOptionError = domDfOption / domDfOption_ref - 1.0
                if abs(domDfOptionError) > EPS:
                    message = (f"Domestic option DF from option data: {domDfOption}, "
                               f"domestic option DF from yield curve {domDfOption_ref}, "
                               f"relative error: {domDfOptionError}")
                    if RAISE_OR_PRINT:
                        raise ValueError(message)
                    else:
                        print(message)

                futureError = f / f_ref - 1.0
                if abs(futureError) > EPS:
                    message = (f"Future from option data: {f}, "
                               f"future from yield curve {f_ref}, "
                               f"relative error: {futureError}")
                    if RAISE_OR_PRINT:
                        raise ValueError(message)
                    else:
                        print(message)

    df_data.dropna(subset=["ImpliedVol"], inplace=True)
    df_data.to_excel(directory + f"/BTCUSDVOLSURFACE_{YYYYMMDD}.xlsx", index=False)
    return
