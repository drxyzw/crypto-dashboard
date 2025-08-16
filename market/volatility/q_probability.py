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
EPS_DENSITY = 1.e-4

# SMILE_INTERPOLATION = "CUBIC"
SMILE_INTERPOLATION = "AFI"


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
    dfs_smile_obj = []
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

            # df_smile = pd.DataFrame()
            # df_smile["ExpiryDate"] = [expiryDate] * len(strikes)
            # df_smile["FutureExpiryDate"] = [futureExpiryDate] * len(strikes)
            # df_smile["TTM"] = [t] * len(strikes)
            # df_smile["Strike"] = strikes
            # df_smile["Vol"] = vols

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
            

            # # smoothing based on time value or dCurvature
            # def computeCumulativeAndDensity(callPrices, strikes, domDfOption):
            #     undisc_intrinsic = callPrices / domDfOption
            #     slopes = np.diff(undisc_intrinsic) / np.diff(strikes)
            #     slopes2 = (undisc_intrinsic[2:] - undisc_intrinsic[:-2]) / (strikes[2:] - strikes[:-2])
            #     # diff = (slopes) ** 2
            #     ave_strikes = 0.5 * (strikes[:-1] + strikes[1:])
            #     curvatures = np.diff(slopes) / np.diff(ave_strikes)
            #     # diff = (curvatures) ** 2
            #     ave_ave_strikes = 0.5 * (ave_strikes[:-1] + ave_strikes[1:])
            #     return loss_value

            df_smile = pd.DataFrame()
            df_smile["ExpiryDate"] = [expiryDate] * len(strikes_non_arb)
            df_smile["FutureExpiryDate"] = [futureExpiryDate] * len(strikes_non_arb)
            df_smile["TTM"] = [t] * len(strikes_non_arb)
            df_smile["Strike"] = strikes_non_arb
            df_smile["Price"] = prices_non_arb
            df_smile["Vol"] = vols_non_arb
            df_smile["CumulativeDensity"] = cumulDensity
            df_smile["Density"] = density

            # # volatility smile
            # strikes_non_arb_vec = [float(k) for k in strikes_non_arb]
            # if SMILE_INTERPOLATION == "CUBIC":
            #     smileSection = ql.CubicInterpolatedSmileSection(t, strikes_non_arb_vec, stds_non_arb, f)
            # elif SMILE_INTERPOLATION == "AFI":
            #     # baseSmileSection = ql.CubicInterpolatedSmileSection(t, strikes_non_arb_vec, stds_non_arb, f)
            #     baseSmileSection = ql.LinearInterpolatedSmileSection(t, strikes_non_arb_vec, stds_non_arb, f)
            #     moneyness = strikes_non_arb_vec / f
            #     try:
            #         smileSection = ql.KahaleSmileSection(baseSmileSection, f, True, False, True, moneyness)
            #         # smileSection = ql.KahaleSmileSection(baseSmileSection, f, False, False, True, moneyness)
            #     except Exception as e:
            #         smileSection = None

            # if not smileSection is None:
            #     df_smile['Density'] = df_smile['Strike'].apply(smileSection.density)
            #     df_smile['CumulativeDensity'] = df_smile['Strike'].apply(lambda x: smileSection.digitalOptionPrice(x, ql.Option.Put))
            #     # df_smile['CallPrice'] = df_smile['Strike'].apply(lambda x: smileSection.optionPrice(x, ql.Option.Call))
            #     df_smile['UndiscountedCallPrice'] = df_smile.apply(lambda x: ql.blackFormula(ql.Option.Call, x['Strike'], f, x['Vol'] * np.sqrt(x['TTM'])),
            #                                                        axis=1)
                
            #     df_smile['CumulativeDensityFromCall'] = df_smile['Strike'].apply(lambda x:
            #              (
            #                  smileSection.optionPrice(x*(1.+EPS_DENSITY), ql.Option.Put) -
            #                  smileSection.optionPrice(x*(1.-EPS_DENSITY), ql.Option.Put)
            #              ) * 0.5 / EPS_DENSITY / x
            #          )
            #     df_smile['DensityFromCumulativeDensity'] = df_smile['Strike'].apply(lambda x:
            #             (
            #                 smileSection.digitalOptionPrice(x*(1.+EPS_DENSITY), ql.Option.Put) -
            #                 smileSection.digitalOptionPrice(x*(1.-EPS_DENSITY), ql.Option.Put)
            #             ) * 0.5 / EPS_DENSITY / x
            #     )


            dfs_smile.append(df_smile)

            # df_smile_obj = pd.DataFrame()
            # df_smile_obj["TTM"] = [t]
            # df_smile_obj["SmileObject"] = [smileSection]
            # dfs_smile_obj.append(df_smile_obj)

    df_smile = pd.concat(dfs_smile).reset_index(drop=True)
    # df_smile_obj = pd.concat(dfs_smile_obj).sort_values(by="TTM").reset_index(drop=True)

    # calendar arbitrage check
    # df_smile_with_obj = df_smile.merge(df_smile_obj, on="TTM", how="left")
    # df_smile = df_smile_with_obj.drop(columns="SmileObject")


    df_smile.to_excel(directory + f"/BTCUSDQPROBABILITY_{YYYYMMDD}.xlsx", index=False)

    market_dict['BTCUSD.QPROBABILITY'] = df_smile
    return market_dict
