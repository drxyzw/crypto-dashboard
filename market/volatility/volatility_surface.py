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
FUTURE_FROM_DATA_NOT_YC = True
RAISE_OR_PRINT = False
EPS = 1.e-3

SMILE_INTERPOLATION = "CUBIC"
# SMILE_INTERPOLATION = "AFI"


def implyFutureAndDomDF(df_data, marketDate):
    ols_model = LinearRegression()
    for expiryDate in df_data['ExpiryDate'].unique():
        qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
        if qlExpiryDate <= marketDate:
            continue
        df_data_expiry_date = df_data[(df_data['ExpiryDate'] == expiryDate)]
        for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            if qlFutureExpiryDate <= marketDate or qlFutureExpiryDate < qlExpiryDate:
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
            mask = (df_data['ExpiryDate'] == expiryDate) & (df_data['FutureExpiryDate'] == futureExpiryDate)
            df_data.loc[mask, "ImpliedFuture"] = f_ref
            df_data.loc[mask, "ImpliedDomDF"] = domDfOption_ref
    return df_data

def implied_volatility(row, marketDate, impliedFuture, domYc = None, assetYc = None, asset_spot = None):
    # In BTC, settlement lag is 0
    expiryDate = pyDateToQlDate(dt.strptime(row['ExpiryDate'], "%Y-%m-%d"))
    if expiryDate <= marketDate:
        return None
    price = row['Price']
    if impliedFuture:
        domDfOption = row["ImpliedDomDF"]
    else:
        domDfOption = domYc.discount(expiryDate)
        assetDfOption = assetYc.discount(expiryDate)
    undisc_price = price / domDfOption
    # underlying futures
    futureExpiryDate = pyDateToQlDate(dt.strptime(row['FutureExpiryDate'], "%Y-%m-%d"))
    if futureExpiryDate <= marketDate  or futureExpiryDate < expiryDate:
        return None
    if impliedFuture:
        f = row["ImpliedFuture"]
    else:
        domDfUnderlying = domYc.discount(futureExpiryDate)
        assetDfUnderlying = assetYc.discount(futureExpiryDate)
        spotPrice = asset_spot.spotRate
        f = spotPrice * assetDfUnderlying / domDfUnderlying
    cp = ql.Option.Call if row['OptionType'] == "Call" else ql.Option.Put
    k = float(row['Strike'])
    # dfRatio = assetDfOption / assetDfUnderlying
    # dfRatio = 1.0
    # f = dfRatio * (spotPrice * assetDfUnderlying / domDfUnderlying)
    dc = ql.Actual365Fixed()
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

def checkFuture(df_data, marketDate, domYc, assetYc, asset_spot):
    for expiryDate in df_data['ExpiryDate'].unique():
        qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
        if qlExpiryDate <= marketDate:
            continue
        df_data_expiry_date = df_data[(df_data['ExpiryDate'] == expiryDate)]
        for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            if qlFutureExpiryDate <= marketDate or qlFutureExpiryDate < qlExpiryDate:
                continue
            # DF for option expiry from yield curve
            qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
            domDfOption = domYc.discount(qlExpiryDate)
            assetDfOption = assetYc.discount(qlExpiryDate)

            # underlying futures from yield curve
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            domDfUnderlying = domYc.discount(qlFutureExpiryDate)
            assetDfUnderlying = assetYc.discount(qlFutureExpiryDate)
            spotPrice = asset_spot.spotRate
            # dfRatio = assetDfOption / assetDfUnderlying
            # dfRatio = domDfUnderlying / domDfOption 
            # dfRatio = 1.0
            # f = dfRatio * (spotPrice * assetDfUnderlying / domDfUnderlying)
            f = spotPrice * assetDfUnderlying / domDfUnderlying

            f_ref = df_data_expiry_date[
                (df_data_expiry_date['ExpiryDate'] == expiryDate)
                & (df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)]["ImpliedFuture"].values[0]
            domDfOption_ref = df_data_expiry_date[
                (df_data_expiry_date['ExpiryDate'] == expiryDate)
                & (df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)]["ImpliedDomDF"].values[0]

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
            
def arbitrageCheck(row, domDfOption, optionType):
    prices = row["Price"].values / domDfOption
    ks = row["Strike"].values
    flags = [set() for _ in range(len(ks))]
    slopes = [0.] * len(ks)

    for i in range(len(ks)-1):
        slope = (prices[i+1] - prices[i]) / (ks[i+1] - ks[i])
        slopes[i] = slope

    for i in range(1, len(ks)-1):
        if ((optionType == "Call" and (slopes[i-1] <= -1. or 0. <= slopes[i-1])) or
            (optionType == "Put" and (slopes[i-1] <= 0. or 1. <= slopes[i-1]))):
            if ((optionType == "Call" and (slopes[i] <= -1. or 0. <= slopes[i])) or
            (optionType == "Put" and (slopes[i] <= 0. or 1. <= slopes[i]))):
                flags[i].add("CS")
            else:
                flags[i-1].add("CS")

        if not slopes[i-1] < slopes[i]:
            flags[i].add("BF")

    for i in range(len(ks)):
        flags[i] = ",".join(flags[i])
        
    return flags
    
def checkCalendarArbitrageOnVolatility(row, df_smile_obj):
    if row['Arbitrage'] == '':
        arb_flags = set()
    else:
        arb_flags = set(row['Arbitrage'].split(","))
    t = row["TTM"]
    expiryDate = row["ExpiryDate"]
    strike = row["Strike"]
    vol = row["Vol"]
    # TTMs = df_smile_obj['TTM'].unique().values
    expiryDates = list(df_smile_obj['ExpiryDate'].unique())
    expiryDates.sort()
    expiryDate_i = expiryDates.index(expiryDate)
    if expiryDate_i == 0:
        i_m1 = expiryDate_i
        i_0 = expiryDate_i + 1
        i_p1 = expiryDate_i + 2
    elif expiryDate_i == len(expiryDates) - 1:
        i_m1 = expiryDate_i - 2
        i_0 = expiryDate_i - 1
        i_p1 = expiryDate_i
    else:
        i_m1 = expiryDate_i - 1
        i_0 = expiryDate_i
        i_p1 = expiryDate_i + 1

    v_m1 = df_smile_obj[df_smile_obj['ExpiryDate'] == expiryDates[i_m1]]["SmileObject"].values[0]
    v_0 = df_smile_obj[df_smile_obj['ExpiryDate'] == expiryDates[i_0]]["SmileObject"].values[0]
    v_p1 = df_smile_obj[df_smile_obj['ExpiryDate'] == expiryDates[i_p1]]["SmileObject"].values[0]
    var_m1 = v_m1.variance(strike)
    var_0 = v_0.variance(strike)
    var_p1 = v_p1.variance(strike)
    var_m1_0 = var_0 - var_m1
    var_0_p1 = var_p1 - var_0

    arbDetected = False   
    if expiryDate_i == 0:
        if var_m1_0 < 0. and var_0_p1 >= 0.:
            arbDetected = True
    elif expiryDate_i == len(expiryDates)  - 1:
        if var_m1_0 >= 0. and var_0_p1 < 0.:
            arbDetected = True
    else:
        if var_m1_0 < 0.:
        # if var_m1_0 < 0. or var_0_p1 < 0.:
            arbDetected = True

    if arbDetected:
        arb_flags.add("CA")
        return ",".join(arb_flags)
    else:
        return row['Arbitrage']

def checkCalendarArbitrageOnPrice(row, df_price):
    if row['Arbitrage'] == '':
        arb_flags = set()
    else:
        arb_flags = set(row['Arbitrage'].split(","))
    expiryDate = row["ExpiryDate"]
    strike = row["Strike"]
    ot = row["OptionType"]
    # TTMs = df_smile_obj['TTM'].unique().values
    expiryDates = list(df_price['ExpiryDate'].unique())
    expiryDates.sort()
    expiryDate_i = expiryDates.index(expiryDate)
    if expiryDate_i == 0:
        i_m1 = expiryDate_i
        i_0 = expiryDate_i + 1
        i_p1 = expiryDate_i + 2
    elif expiryDate_i == len(expiryDates) - 1:
        i_m1 = expiryDate_i - 2
        i_0 = expiryDate_i - 1
        i_p1 = expiryDate_i
    else:
        i_m1 = expiryDate_i - 1
        i_0 = expiryDate_i
        i_p1 = expiryDate_i + 1

    # domDF = df_price[df_price]["ImpliedDomDF"]
    masked_m1 = df_price[((df_price['ExpiryDate'] == expiryDates[i_m1])
                        & (df_price['OptionType'] == ot)
                        & (df_price['Strike'] == strike))]
    und_price_m1 = (masked_m1["Price"].values[0] / masked_m1["ImpliedDomDF"].values[0]
                    if not masked_m1.empty else None)

    masked_0 = df_price[((df_price['ExpiryDate'] == expiryDates[i_0])
                        & (df_price['OptionType'] == ot)
                        & (df_price['Strike'] == strike))]
    und_price_0 = (masked_0["Price"].values[0] / masked_0["ImpliedDomDF"].values[0]
                   if not masked_0.empty else None)

    masked_p1 = df_price[(df_price['ExpiryDate'] == expiryDates[i_p1])
                        & (df_price['OptionType'] == ot)
                        & (df_price['Strike'] == strike)]
    und_price_p1 = (masked_p1["Price"].values[0] / masked_p1["ImpliedDomDF"].values[0]
                    if not masked_p1.empty else None)

    und_price_m1_0 = ((und_price_0 - und_price_m1)
                      if not und_price_0 is None and not und_price_m1 is None else None)
    und_price_0_p1 = ((und_price_p1 - und_price_0)
                      if not und_price_p1 is None and not und_price_0 is None else None)

    arbDetected = False   
    if expiryDate_i == 0:
        if (not und_price_m1_0 is None) and (not und_price_0_p1 is None):
            if und_price_m1_0 < 0. and und_price_0_p1 >= 0.:
                arbDetected = True
        elif (not und_price_0_p1 is None):
            if und_price_m1_0 < 0.:
                arbDetected = True
    elif expiryDate_i == len(expiryDates) - 1:
        if (not und_price_m1_0 is None) and (not und_price_0_p1 is None):
            if und_price_m1_0 >= 0. and und_price_0_p1 < 0.:
                arbDetected = True
        elif (not und_price_m1_0 is None):
            if und_price_0_p1 < 0.:
                arbDetected = True
    else:
        if (not und_price_m1_0 is None) and (und_price_m1_0 < 0.):
        # if var_m1_0 < 0. or var_0_p1 < 0.:
            arbDetected = True

    if arbDetected:
        arb_flags.add("CA")
        return ",".join(arb_flags)
    else:
        return row['Arbitrage']

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

    if FUTURE_FROM_DATA_NOT_YC:
        df_data = implyFutureAndDomDF(df_data, marketDate)
        df_data["ImpliedVol"] = df_data.apply(
            lambda x: implied_volatility(x, marketDate, impliedFuture=True,
                                         domYc = domYc, assetYc = assetYc, 
                                         asset_spot = asset_spot), axis=1)
    else:
        df_data["ImpliedVol"] = df_data.apply(
            lambda x: implied_volatility(x, marketDate, impliedFuture=False,
                                         domYc = domYc, assetYc = assetYc, 
                                         asset_spot = asset_spot), axis=1)
        if FUTURE_CHECK:
            df_data = implyFutureAndDomDF(df_data, marketDate)
            checkFuture(df_data, marketDate, domYc = domYc, assetYc = assetYc, 
                                         asset_spot = asset_spot)

    df_data.dropna(subset=["ImpliedVol"], inplace=True)

    dfs_smile = []
    dfs_smile_obj = []
    for expiryDate in df_data['ExpiryDate'].unique():
        qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
        if qlExpiryDate <= marketDate:
            continue
        df_data_expiry_date = df_data[(df_data['ExpiryDate'] == expiryDate)]
        for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            if qlFutureExpiryDate <= marketDate or qlFutureExpiryDate < qlExpiryDate:
                continue
            df_data_f_expiry_date = df_data_expiry_date[
                    (df_data_expiry_date['ExpiryDate'] == expiryDate)
                    & (df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)]
            if FUTURE_FROM_DATA_NOT_YC:
                f = df_data_f_expiry_date["ImpliedFuture"].values[0]
                domDfOption = df_data_f_expiry_date["ImpliedDomDF"].values[0]
            else:
                domDfOption = domYc.discount(qlExpiryDate)
                domDfUnderlying = domYc.discount(qlFutureExpiryDate)
                assetDfUnderlying = assetYc.discount(qlFutureExpiryDate)
                spotPrice = asset_spot.spotRate
                f = spotPrice * assetDfUnderlying / domDfUnderlying
                
            # arbitrage check along strike
            mask_call = ((df_data['ExpiryDate'] == expiryDate)
                         & (df_data['FutureExpiryDate'] == futureExpiryDate)
                         & (df_data['OptionType'] == "Call"))
            df_data.loc[mask_call, "Arbitrage"] = arbitrageCheck(df_data[mask_call], domDfOption, "Call")
            mask_put = ((df_data['ExpiryDate'] == expiryDate)
                         & (df_data['FutureExpiryDate'] == futureExpiryDate)
                         & (df_data['OptionType'] == "Put"))
            df_data.loc[mask_put, "Arbitrage"] = arbitrageCheck(df_data[mask_put], domDfOption, "Put")

            # volatility smile
            dc = ql.Actual365Fixed()
            t = dc.yearFraction(marketDate, qlExpiryDate)
            call_strikes = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Call"]["Strike"].values.astype(np.float64)
            put_strikes = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Put"]["Strike"].values.astype(np.float64)
            call_vols = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Call"]["ImpliedVol"].values.astype(np.float64)
            put_vols = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Put"]["ImpliedVol"].values.astype(np.float64)
            call_arb_flags = df_data[mask_call]["Arbitrage"]
            # call_arb_flags = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Call"]["Arbitrage"]
            # put_arb_flags = df_data_f_expiry_date[df_data_f_expiry_date["OptionType"] == "Put"]["Arbitrage"]
            put_arb_flags = df_data[mask_put]["Arbitrage"]
            strikes = np.concatenate((put_strikes[put_strikes < f], call_strikes[call_strikes >= f]))
            vols = np.concatenate((put_vols[put_strikes < f], call_vols[call_strikes >= f]))
            arb_flags = np.concatenate((put_arb_flags[put_strikes < f], call_arb_flags[call_strikes >= f]))
            stds = vols * np.sqrt(t)

            # volatility smile
            if SMILE_INTERPOLATION == "CUBIC":
                smileSection = ql.CubicInterpolatedSmileSection(t, strikes, stds, f)
            elif SMILE_INTERPOLATION == "AFI":
                baseSmileSection = ql.LinearInterpolatedSmileSection(t, strikes, stds, f)
                moneyness = strikes / f
                smileSection = ql.KahaleSmileSection(baseSmileSection, f, False, False, True, moneyness)

            df_smile = pd.DataFrame()
            df_smile["ExpiryDate"] = [expiryDate] * len(stds)
            df_smile["FutureExpiryDate"] = [futureExpiryDate] * len(stds)
            df_smile["TTM"] = [t] * len(stds)
            df_smile["Strike"] = strikes
            df_smile["Vol"] = vols
            df_smile["Arbitrage"] = arb_flags
            dfs_smile.append(df_smile)

            df_smile_obj = pd.DataFrame()
            df_smile_obj["TTM"] = [t]
            df_smile_obj["SmileObject"] = [smileSection]
            dfs_smile_obj.append(df_smile_obj)

    df_smile = pd.concat(dfs_smile).reset_index(drop=True)
    df_smile_obj = pd.concat(dfs_smile_obj).sort_values(by="TTM").reset_index(drop=True)

    # calendar arbitrage check
    df_smile_with_obj = df_smile.merge(df_smile_obj, on="TTM", how="left")
    df_smile_with_obj["Arbitrage"] = df_smile_with_obj.apply(lambda x: checkCalendarArbitrageOnVolatility(x, df_smile_with_obj), axis=1)
    df_smile = df_smile_with_obj.drop(columns="SmileObject")

    df_data["Arbitrage"] = df_data.apply(lambda x: checkCalendarArbitrageOnPrice(x, df_data), axis=1)

    df_smile.to_excel(directory + f"/BTCUSDVOLSURFACE_{YYYYMMDD}.xlsx", index=False)
    df_data.to_excel(directory + f"/BTCUSDIMPLIEDVOL{YYYYMMDD}.xlsx", index=False) # just added implied vol to option price input

    market_dict['BTCUSD.VOLSURFACE'] = df_smile
    return market_dict
