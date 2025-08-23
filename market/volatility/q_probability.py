import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
import os
from sklearn.linear_model import LinearRegression
# from scipy.optimize import bisect
from scipy.optimize import curve_fit
import QuantLib as ql

from utils.convention import *
PROCESSED_DIR = "./data_processed"
CUMUL_EPS = 1.e-7

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
            strikes = df_data_f_expiry_date["Strike"].values.astype('float')
            vols = df_data_f_expiry_date["ImpliedVol"].values
            prices = df_data_f_expiry_date["Price"].values
            arb_flags = df_data_f_expiry_date["Arbitrage"].values

            mask_non_arb = pd.isna(arb_flags)
            strikes_non_arb = strikes[mask_non_arb]
            vols_non_arb = vols[mask_non_arb]
            prices_non_arb = prices[mask_non_arb]

            # # extrapolate if cumulative density does not cover enough
            # undisc_price = prices_non_arb / dfDomOption
            # slopes = np.diff(undisc_price) / np.diff(strikes_non_arb)
            # if all(df_data_f_expiry_date['OptionType'] == "Call"):
            #     if slopes[-1] < 1. - CUMUL_EPS:
            #         # fit Pareto distribution to last 3 points
            #         # call(ki) = a * (ki+b)**c   (i=1,2,3), extraporate from k1
            #         undisc_extrap = np.flip(undisc_price[-3:])
            #         k_extrap = np.flip(strikes_non_arb[-3:])
            #         undic_timevalue_extrap = undisc_extrap - np.maximum(f - k_extrap, 0.)
            #         # ln[ (k2+b) / (k3 + b)] / ln(c3/c2) = ln[ (k1+b) / (k2 + b)] / ln(c2/c1)
            #         def extrap_b(b):
            #             ret = (
            #                 np.log(undic_timevalue_extrap[2]/undic_timevalue_extrap[0])
            #                     / np.log(undic_timevalue_extrap[1]/undic_timevalue_extrap[0])
            #               - np.log( (k_extrap[0]+b) / (k_extrap[2] + b))
            #                     / np.log( (k_extrap[0]+b) / (k_extrap[1] + b))
            #             )
            #             return ret
            #         for i in range(15):
            #             minb = k_extrap[2] * (-1. + np.power(0.1, i))
            #             f_minb = extrap_b(minb)
            #             if f_minb < 0.:
            #                 break

            #         maxb = k_extrap[0]
            #         f_maxb = extrap_b(maxb)
            #         for i in range(100):
            #             maxb = k_extrap[0] * i
            #             f_maxb = extrap_b(maxb)
            #             if f_maxb > 0.:
            #                 break
            #         b = bisect(extrap_b, minb, maxb)
            #         print(b)
            # else:
            #     raise NotImplementedError("Unimplemented for put price case") 

            undisc_price = prices_non_arb / dfDomOption
            slopes = np.diff(undisc_price) / np.diff(strikes_non_arb)
            slopes2 = (undisc_price[2:] - undisc_price[:-2]) / (strikes_non_arb[2:] - strikes_non_arb[:-2])
            ave_strikes = 0.5 * (strikes_non_arb[:-1] + strikes_non_arb[1:])
            curvatures = np.diff(slopes) / np.diff(ave_strikes)

            # reformat for cumulative density and density
            # slopes_for_cumul = list(slopes) + [0.]
            # slopes_for_cumul = list(slopes) + [slopes[-1]]
            slopes_for_cumul = [slopes[0]] + list(slopes2) + [slopes[-1]]
            cumulDensity = 1. + np.array(slopes_for_cumul)
            cumulDensity = np.maximum(np.minimum(cumulDensity, 1.), 0.)
            density = np.array([curvatures[0]] + list(curvatures) + [curvatures[-1]])
            density = np.maximum(density, 0.)
            
            # extrapolation on upper strike side
            if cumulDensity[-1] < 1. - CUMUL_EPS:
                # Extrapolate with Pareto distribution
                # # undisc_call = a*(k+b)**c
                # # -1 + cumulDensity = a*c*(k+b)**(c-1)
                # # density = a*c*(c-1)*(k+b)**(c-2)
                # # so
                # # 1/(k+b) = (-1 + cumulDensity)/undisc_call - density/(-1 + cumulDensity)
                # # c = (-1 + cumulDensity)/undisc_call * (k+b)
                # # a = undisc_call / (k+b)**c
                # inv_k_plus_b = (
                #     (-1 + cumulDensity[-1])/undisc_price[-1] - density[-1]/(-1 + cumulDensity[-1])
                # )
                # k_plus_b = 1./inv_k_plus_b
                # b = k_plus_b - strikes_non_arb[-1]
                # c = (-1 + cumulDensity[-1])/undisc_price[-1] * k_plus_b
                # a = undisc_price[-1] * inv_k_plus_b**c

                N_upper = 20
                x = strikes_non_arb[-N_upper:]
                y = undisc_price[-N_upper:]
                def fit_pareto_tail(x, y, max_iter = 100, tol = 1.e-4):
                    l = 0

                    while l < max_iter:
                        if l > 0:
                            a_last = a_ln
                            b_last = b
                            c_last = c
                        # first, rough estimate by log-log OLS
                        x_pos = np.array([x[i] for i in range(len(x)) if y[i] > 0])
                        if l > 0:
                            x_pos += b
                        y_pos = np.array([y[i] for i in range(len(x)) if y[i] > 0])
                        x_ln = np.log(x_pos).reshape([-1, 1])
                        y_ln = np.log(y_pos)
                        model = LinearRegression()
                        model.fit(x_ln, y_ln)
                        c = model.coef_[0]
                        a_ln = model.intercept_
                        def pareto_tail_ln(x, b):
                            return a_ln + c*np.log(x + b)
                        params, pcov = curve_fit(pareto_tail_ln, x_pos, y_ln, p0=(0.))
                        b = params[0]
                        if l > 0:
                            if ((abs(a_ln-a_last) < a_last*tol) and 
                                (abs(b-b_last) < b_last*tol) and 
                                (abs(c-c_last) < c_last*tol)):
                                break
                        l += 1
                    return a_ln, b, c
                a_ln, b, c = fit_pareto_tail(x, y)
                a = np.exp(a_ln)
                print(f"a, b, c = {a}, {b}, {c}")
                # remove the last point because it was flatly extrapolated
                undisc_price = undisc_price[:-1]
                prices_non_arb = prices_non_arb[:-1]
                strikes_non_arb = strikes_non_arb[:-1]
                vols_non_arb = vols_non_arb[:-1]
                cumulDensity = cumulDensity[:-1]
                density = density[:-1]

                # extend strike
                exponent10 = int(np.log10(strikes_non_arb[-1]))
                dK = 10**(exponent10-1)
                while cumulDensity[-1] < 1. - CUMUL_EPS:
                    k_extend = strikes_non_arb[-1] + dK
                    undisc_price_extend = a*(k_extend + b)**c
                    price_extend = undisc_price_extend * dfDomOption
                    vol_extend = ql.blackFormulaImpliedStdDev(
                        ql.Option.Call, k_extend, f, undisc_price_extend) / np.sqrt(t)
                    cumul_extend = a*c*(k_extend + b)**(c-1) + 1.
                    density_extend = a*c*(c-1)*(k_extend + b)**(c-2)

                    strikes_non_arb = np.append(strikes_non_arb, k_extend)
                    prices_non_arb = np.append(prices_non_arb, price_extend)
                    vols_non_arb = np.append(vols_non_arb, vol_extend)
                    cumulDensity = np.append(cumulDensity, cumul_extend)
                    density = np.append(density, density_extend)

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

    market_dict['BTCUSD.QPROBABIL  ITY'] = df_smile
    return market_dict
