import QuantLib as ql
from datetime import datetime as dt
import pandas as pd
import numpy as np
import math
import os
from sklearn.linear_model import LinearRegression
# from scipy.optimize import bisect
from scipy.optimize import curve_fit
import QuantLib as ql

from utils.convention import *
from utils.config import *
PROCESSED_DIR = "./data_processed"
CUMUL_EPS = 1.e-5

def extrapolateUndiscCallPriceWithPareto(t, f, dfDomOption,
                                         prices_non_arb, undisc_price, strikes_non_arb,
                                         cumulDensity, vols_non_arb, density, isUpper, N_extrap = 20):
    undic_timevalue = undisc_price - np.maximum(f - strikes_non_arb, 0.)
 
    if ((isUpper and (cumulDensity[-1] < 1. - CUMUL_EPS))
        or (not isUpper and (cumulDensity[0] >  CUMUL_EPS))):
        # fit Pareto parameter
        # undisc_call = a*(k+b)**c
        price_mask = undic_timevalue > MIN_TICK_PRICE
        if isUpper:
            mask = (strikes_non_arb > f) & price_mask
            x = strikes_non_arb[mask][-N_extrap:]
            y = undic_timevalue[mask][-N_extrap:]
        else:
            mask = (strikes_non_arb < f) & price_mask
            x = strikes_non_arb[mask][:N_extrap]
            y = undic_timevalue[mask][:N_extrap]
        
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
                # only for upper extrapolation, we consider a shift b
                # for lower extrapolation, set b = 0
                # this is because 
                # undic_timevalue_extend = a*(k + b)**c
                # might be NaN for lower k when b < 0
                # and not converge to 0 when b > 0
                if isUpper:
                    def pareto_tail_ln(x, b):
                        return a_ln + c*np.log(x + b)
                    params, pcov = curve_fit(pareto_tail_ln, x_pos, y_ln, p0=(0.))
                    b = params[0]
                else:
                    b = 0.
                if l > 0:
                    if ((abs(a_ln-a_last) <= a_last*tol) and 
                        (abs(b-b_last) <= b_last*tol) and 
                        (abs(c-c_last) <= c_last*tol)):
                        break
                l += 1
            return a_ln, b, c
        a_ln, b, c = fit_pareto_tail(x, y)
        a = np.exp(a_ln)
        print(f"a, b, c = {a}, {b}, {c}")
        # remove the last point because it was flatly extrapolated
        if isUpper:
            undisc_price = undisc_price[:-1]
            prices_non_arb = prices_non_arb[:-1]
            strikes_non_arb = strikes_non_arb[:-1]
            vols_non_arb = vols_non_arb[:-1]
            cumulDensity = cumulDensity[:-1]
            density = density[:-1]
        else:
            undisc_price = undisc_price[1:]
            prices_non_arb = prices_non_arb[1:]
            strikes_non_arb = strikes_non_arb[1:]
            vols_non_arb = vols_non_arb[1:]
            cumulDensity = cumulDensity[1:]
            density = density[1:]

        # extend strike
        while ((isUpper and (cumulDensity[-1] < 1. - CUMUL_EPS))
            or (not isUpper and (cumulDensity[0] >  CUMUL_EPS))):
            if isUpper:
                exponent10 = math.floor(np.log10(strikes_non_arb[-1]))
                dK = 10**(exponent10)
                k_extend = strikes_non_arb[-1] + dK
            else:
                exponent10 = math.floor(np.log10(strikes_non_arb[0]))
                dK = 10**(exponent10)
                dK = dK if strikes_non_arb[0] >= 2. * dK else (dK / 10)
                k_extend = strikes_non_arb[0] - dK

            pareto_ln = a_ln + c*np.log(k_extend + b)
            undic_timevalue_extend = np.exp(pareto_ln)
            undisc_price_extend = undic_timevalue_extend + np.maximum(f - k_extend, 0.)
            price_extend = undisc_price_extend * dfDomOption
            vol_extend = ql.blackFormulaImpliedStdDev(
                ql.Option.Call, k_extend, f, undisc_price_extend) / np.sqrt(t)
            if isUpper:
                cumul_extend = undic_timevalue_extend * c/(k_extend + b) + 1.
            else:
                cumul_extend = undic_timevalue_extend * c/(k_extend + b)
            density_extend = undic_timevalue_extend * c*(c-1)/(k_extend + b)**2.
            if isUpper:
                strikes_non_arb = np.append(strikes_non_arb, k_extend)
                prices_non_arb = np.append(prices_non_arb, price_extend)
                undisc_price = np.append(undisc_price, price_extend)
                vols_non_arb = np.append(vols_non_arb, vol_extend)
                cumulDensity = np.append(cumulDensity, cumul_extend)
                density = np.append(density, density_extend)
            else:
                strikes_non_arb = np.insert(strikes_non_arb, 0, k_extend)
                prices_non_arb = np.insert(prices_non_arb, 0, price_extend)
                undisc_price = np.insert(undisc_price, 0, price_extend)
                vols_non_arb = np.insert(vols_non_arb, 0, vol_extend)
                cumulDensity = np.insert(cumulDensity, 0, cumul_extend)
                density = np.insert(density, 0, density_extend)
    
    return prices_non_arb, undisc_price, strikes_non_arb, cumulDensity, vols_non_arb, density

def build_q_probability(market_dict, skipIfExist):
    if not market_dict:
        print("Input market is empty")
        return None
    marketDate = ql.Settings.instance().evaluationDate
    pyMarketDate = qlDateToPyDate(marketDate)
    YYYYMMDD = pyMarketDate.strftime("%Y%m%d")

    directory = PROCESSED_DIR + f"./{YYYYMMDD}"
    qprobability_file = f"BTCUSDQPROBABILITY_{YYYYMMDD}.xlsx"
    qprobability_output = directory + f"/{qprobability_file}"

    # if output file exists already, just skip
    if skipIfExist and os.path.isfile(qprobability_output):
        print(f"Skipped exporting {qprobability_file} because output file exists already.")
        df_smile = pd.read_excel(qprobability_output)
    else:
        # use implied vol file which contains option price that is strongly linked to density
        PROCESSED_FILE = f"BTCUSDIMPLIEDVOL_REGULARIZED_{YYYYMMDD}.xlsx"
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

                undisc_price = prices_non_arb / dfDomOption
                slopes = np.diff(undisc_price) / np.diff(strikes_non_arb)
                slopes2 = (undisc_price[2:] - undisc_price[:-2]) / (strikes_non_arb[2:] - strikes_non_arb[:-2])
                ave_strikes = 0.5 * (strikes_non_arb[:-1] + strikes_non_arb[1:])
                curvatures = np.diff(slopes) / np.diff(ave_strikes)

                # reformat for cumulative density and density
                slopes_for_cumul = [slopes[0]] + list(slopes2) + [slopes[-1]]
                cumulDensity = 1. + np.array(slopes_for_cumul)
                cumulDensity = np.maximum(np.minimum(cumulDensity, 1.), 0.)
                density = np.array([curvatures[0]] + list(curvatures) + [curvatures[-1]])
                density = np.maximum(density, 0.)

                # extrapolation on upper strike side with Pareto tail
                prices_non_arb, undisc_price, strikes_non_arb, cumulDensity, vols_non_arb, density = \
                    extrapolateUndiscCallPriceWithPareto(t, f, dfDomOption,
                                                         prices_non_arb, undisc_price, strikes_non_arb,
                                                         cumulDensity, vols_non_arb, density,
                                                         isUpper = False, N_extrap = 20)
                prices_non_arb, undisc_price, strikes_non_arb, cumulDensity, vols_non_arb, density = \
                    extrapolateUndiscCallPriceWithPareto(t, f, dfDomOption,
                                                         prices_non_arb, undisc_price, strikes_non_arb,
                                                         cumulDensity, vols_non_arb, density,
                                                         isUpper = True, N_extrap = 20)

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
        df_smile.to_excel(qprobability_output, index=False)

    market_dict['BTCUSD.QPROBABILITY'] = df_smile
    return market_dict
