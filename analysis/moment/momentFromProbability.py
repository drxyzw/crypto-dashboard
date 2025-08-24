import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression

from utils.convention import *
PROCESSED_DIR = "./data_processed"
RAW_DIR = "./data_raw"
CUMUL_EPS = 1.e-4
# CUMUL_EPS = 0.0 # 1.e-4

def compute_moment(market_dict):
    marketDate = ql.Settings.instance().evaluationDate
    pyMarketDate = qlDateToPyDate(marketDate)
    YYYYMMDD = pyMarketDate.strftime("%Y%m%d")

    # get spot rates from raw data not from processd data
    # because a row data contains all dates
    # while processed data only contains one date
    RAW_SPOT_FILE = "CME_BRR_latest.xlsx"
    spot_file_path = RAW_DIR + "/" + RAW_SPOT_FILE
    if not os.path.exists(spot_file_path):
        return None
    df_historicalSpotPrice = pd.read_excel(spot_file_path)
    df_historicalSpotPrice = df_historicalSpotPrice[["Date", "BRR"]]
    df_historicalSpotPrice["Date"] = pd.to_datetime(df_historicalSpotPrice["Date"])
    df_historicalSpotPrice = df_historicalSpotPrice.copy()
    
    if not "BTCUSD.SPOT" in market_dict.keys():
        return None
    asset_spot = market_dict["BTCUSD.SPOT"]
    spotPrice = asset_spot.spotRate

    # use cumulative density under risk neutral measure file
    PROCESSED_FILE = f"BTCUSDQPROBABILITY_{YYYYMMDD}.xlsx"
    directory = PROCESSED_DIR + f"/{YYYYMMDD}"
    full_path = directory + "/" + PROCESSED_FILE
    if not os.path.exists(full_path):
        return None
    
    df_qprobability = pd.read_excel(full_path)
    df_qprobability.dropna(subset=["CumulativeDensity"], inplace=True)
    df_qprobability["k_return"] = np.log(df_qprobability["Strike"] / spotPrice)

    dfs_moment = []
    for expiryDate in df_qprobability['ExpiryDate'].unique():
        qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
        pyExpiryDate = pd.to_datetime(expiryDate)
        if qlExpiryDate <= marketDate:
            continue
        df_data_expiry_date = df_qprobability[(df_qprobability['ExpiryDate'] == expiryDate)]
        for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            # pyFutureExpiryDate = pd.to_datetime(futureExpiryDate)
            if qlFutureExpiryDate <= marketDate or qlFutureExpiryDate < qlExpiryDate:
                continue
            df_data_f_expiry_date = df_data_expiry_date[
                    (df_data_expiry_date['ExpiryDate'] == expiryDate)
                    & (df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)]
                
            df_to_integrate = df_data_f_expiry_date[
                (df_data_f_expiry_date["CumulativeDensity"] >= CUMUL_EPS) &
                (df_data_f_expiry_date["CumulativeDensity"] <= 1. - CUMUL_EPS)
                ]
            
            # Risk-Neutral Probability
            cumul_densities = df_to_integrate["CumulativeDensity"].values
            k_values = df_to_integrate["Strike"].values
            k_returns = df_to_integrate["k_return"].values
            normalize = cumul_densities[-1] - cumul_densities[0]
            dCumul = cumul_densities[1:] - cumul_densities[:-1]
            aveRetAbs = 0.5 * (k_values[1:] + k_values[:-1])
            aveRet = 0.5 * (k_returns[1:] + k_returns[:-1])
            # moment 1: meean
            ABSM1_RN = np.dot(dCumul, aveRetAbs) / normalize
            M1_RN = np.dot(dCumul, aveRet) / normalize
            # center moment 2: variance
            cRet = aveRet - M1_RN
            CM2_RN = np.dot(dCumul, cRet**2) / normalize
            # center normalized moment 3: skewness
            CM3_RN = np.dot(dCumul, cRet**3) / normalize
            CMN3_RN = CM3_RN / CM2_RN**(3./2)
            # center normalized moment 4: kurtosis
            CM4_RN = np.dot(dCumul, cRet**4) / normalize
            CMN4_RN = CM4_RN / CM2_RN**(4./2)

            # Physical Probability
            if(df_historicalSpotPrice["Date"].values[-1] >= pyExpiryDate):
                df_historicalSpotPrice_select = df_historicalSpotPrice[(df_historicalSpotPrice["Date"] > pyMarketDate) &
                                                                       (df_historicalSpotPrice["Date"] <= pyExpiryDate)]
                retSpot = np.log(df_historicalSpotPrice_select["BRR"].values / spotPrice)
            else:
                retSpot = np.array([np.nan])
            # moment 1: meean
            M1_PH = np.mean(retSpot)
            # center moment 2: variance
            cRetSpot = retSpot - M1_PH
            CM2_PH = np.mean(cRetSpot**2)
            # center normalized moment 3: skewness
            CM3_PH = np.mean(cRetSpot**3)
            CMN3_PH = CM3_PH / CM2_PH**(3./2)
            # center normalized moment 4: kurtosis
            CM4_PH = np.mean(cRetSpot**4)
            CMN4_PH = CM4_PH / CM2_PH**(4./2)

            df = pd.DataFrame(
                {
                    "ExpiryDate": [df_to_integrate["ExpiryDate"].values[0]],
                    "FutureExpiryDate": [df_to_integrate["FutureExpiryDate"].values[0]],
                    "TTM": [df_to_integrate["TTM"].values[0]],
                    "ABSM1_RN": [ABSM1_RN],
                    "M1_RN": [M1_RN],
                    "CM2_RN": [CM2_RN],
                    "CMN3_RN": [CMN3_RN],
                    "CMN4_RN": [CMN4_RN],
                    "M1_PH": [M1_PH],
                    "CM2_PH": [CM2_PH],
                    "CMN3_PH": [CMN3_PH],
                    "CMN4_PH": [CMN4_PH],
                }
            )

            dfs_moment.append(df)

    df_moment = pd.concat(dfs_moment).reset_index(drop=True)
    df_moment.to_excel(directory + f"/BTCUSDQMOMENT_{YYYYMMDD}.xlsx", index=False)

    return df_moment
