import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression

from utils.convention import *
PROCESSED_DIR = "./data_processed"

def build_q_probability(market_dict):
    if not market_dict:
        print("Input market is empty")
        return None
    marketDate = ql.Settings.instance().evaluationDate
    pyMarketDate = qlDateToPyDate(marketDate)
    YYYYMMDD = pyMarketDate.strftime("%Y%m%d")

     # use implied vol file which contains option price that is strongly linked to density
    PROCESSED_FILE = f"BTCUSDIMPLIEDVOL_REGULARIZED_{YYYYMMDD}.xlsx"
    directory = PROCESSED_DIR + f"./{YYYYMMDD}"
    full_path = directory + "/" + PROCESSED_FILE
    if not os.path.exists(full_path):
        return None
    
    df_vol_data = pd.read_excel(full_path)
    df_vol_data.dropna(subset=["ImpliedVol"], inplace=True)

    dfs_smile = []
    for expiryDate in df_vol_data['ExpiryDate'].unique():
        qlExpiryDate = YYYYMMDDHyphenToQlDate(expiryDate)
        if qlExpiryDate <= marketDate:
            continue
        df_data_expiry_date = df_vol_data[(df_vol_data['ExpiryDate'] == expiryDate)]
        for futureExpiryDate in df_data_expiry_date['FutureExpiryDate'].unique():
            qlFutureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDate)
            if qlFutureExpiryDate <= marketDate or qlFutureExpiryDate < qlExpiryDate:
                continue
            df_data_f_expiry_date = df_data_expiry_date[
                    (df_data_expiry_date['ExpiryDate'] == expiryDate)
                    & (df_data_expiry_date['FutureExpiryDate'] == futureExpiryDate)
                    # only choose call price. this should be ok because put price contribution is considered in regularization
                    # by taking average of time value of call and put prices
                    & (df_data_expiry_date['OptionType'] == "Call")]
                
            dc = ql.Actual365Fixed()
            t = dc.yearFraction(marketDate, qlExpiryDate)
            f = df_data_f_expiry_date["ImpliedFuture"].values[0]
            dfDomOption = df_data_f_expiry_date["ImpliedDomDF"].values[0]
            strikes = df_data_f_expiry_date["Strike"].values
            vols = df_data_f_expiry_date["ImpliedVol"].values
            prices = df_data_f_expiry_date["Price"].values
            arb_flags = df_data_f_expiry_date["Arbitrage"].values

            mask_non_arb = pd.isna(arb_flags)
            strikes_non_arb = strikes[mask_non_arb]
            vols_non_arb = vols[mask_non_arb]
            prices_non_arb = prices[mask_non_arb]
            stds_non_arb = vols_non_arb * np.sqrt(t)

            undisc_intrinsic = prices_non_arb / dfDomOption
            slopes = np.diff(undisc_intrinsic) / np.diff(strikes_non_arb)
            slopes2 = (undisc_intrinsic[2:] - undisc_intrinsic[:-2]) / (strikes_non_arb[2:] - strikes_non_arb[:-2])
            ave_strikes = 0.5 * (strikes_non_arb[:-1] + strikes_non_arb[1:])
            curvatures = np.diff(slopes) / np.diff(ave_strikes)

            # reformat for cumulative density and density
            slopes_for_cumul = [slopes[0]] + list(slopes2) + [slopes[-1]]
            cumulDensity = 1. + np.array(slopes_for_cumul)
            cumulDensity = np.maximum(np.minimum(cumulDensity, 1.), 0.)
            density = np.array([curvatures[0]] + list(curvatures) + [curvatures[-1]])
            density = np.maximum(density, 0.)
            

            df_smile = pd.DataFrame()
            df_smile["ExpiryDate"] = [expiryDate] * len(strikes_non_arb)
            df_smile["FutureExpiryDate"] = [futureExpiryDate] * len(strikes_non_arb)
            df_smile["TTM"] = [t] * len(strikes_non_arb)
            df_smile["Strike"] = strikes_non_arb
            df_smile["Price"] = prices_non_arb
            df_smile["Vol"] = vols_non_arb
            df_smile["CumulativeDensity"] = cumulDensity
            df_smile["Density"] = density

            dfs_smile.append(df_smile)

    df_smile = pd.concat(dfs_smile).reset_index(drop=True)
    df_smile.to_excel(directory + f"/BTCUSDQPROBABILITY_{YYYYMMDD}.xlsx", index=False)

    market_dict['BTCUSD.QPROBABILITY'] = df_smile
    return market_dict
