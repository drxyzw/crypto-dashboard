import QuantLib as ql

from utils.calendar import *
from utils.convention import *

def create_rate_helper(row, yc_raw, parsed_market_objects = None, days=0):
    marketDate = yc_raw['Date']
    marketDate = YYYYMMDDHyphenToQlDate(marketDate)
    rate_type = row['Type'].upper()
    ticker = row['Ticker'].upper()
    tenor = row['Tenor'].upper()
    rate = row["Rate"]
    if rate_type == "DEPOSIT":
        if ticker == "SOFRRATE":
            index = SOFR_index()
        else:
            raise ValueError(f"Unsupported ticker {ticker} for DEPOSIT rate helper")
        helper = ql.DepositRateHelper(rate, index)
    elif rate_type == "FUTURE":
        if ticker.startswith("SL") or ticker.startswith("SQ") or ticker.startswith("SR"):
            helper = SOFR_FUTURE_rate_helper(rate, ticker)
        else:
            raise ValueError(f"Unsupported ticker {ticker} for future rate helper")
    elif rate_type == "OIS":
        if ticker.startswith("SOFR"):
            index = SOFR_index()
            rateQuote = ql.QuoteHandle(ql.SimpleQuote(rate))
            helper = ql.OISRateHelper(2, ql.Period(tenor), rateQuote, index)
        else:
            raise ValueError(f"Unsupported ticker {ticker} for OIS rate helper")
    elif rate_type == "FXFUTURE":
        if ticker.startswith("BTC"):
            settleLag = 0
            maturityDate = YYYYMMDDHyphenToQlDate(tenor)
            cal = UKorUSCalendar()
            settlementDate = cal.advance(maturityDate, settleLag, ql.Days, ql.Following)
            nbDays = cal.businessDaysBetween(marketDate, settlementDate)
            # nbDays = settlementDate - marketDate
            baseDiscountingCurveName = yc_raw['BaseDiscountingCurve'].upper()
            baseDiscountingCurve = parsed_market_objects[baseDiscountingCurveName]
            spotName = yc_raw['Spot'].upper()
            spotObj = parsed_market_objects[spotName]
            spotRate = spotObj.spotRate
            forCcy = spotName[:3]
            baseCcy = baseDiscountingCurveName.split(".")[0]
            fwdPts = rate - spotRate
            # df_base = baseDiscountingCurve.discount(settlementDate)
            isFxBaseCurrencyCollateralCurrency = forCcy == baseCcy
            if days == 0:
                helper = ql.FxSwapRateHelper(
                    ql.QuoteHandle(ql.SimpleQuote(fwdPts)), 
                    # spotObj.spotQuote, ql.Period(settlementDate - marketDate), settleLag, cal, ql.Following, False, 
                    spotObj.spotQuote, ql.Period(nbDays, ql.Days), settleLag, cal, ql.Following, False, 
                    isFxBaseCurrencyCollateralCurrency, baseDiscountingCurve, cal)
            else:
                helper = ql.FxSwapRateHelper(
                    ql.QuoteHandle(ql.SimpleQuote(fwdPts)), 
                    spotObj.spotQuote, ql.Period(days, ql.Days), settleLag, cal, ql.Following, False, 
                    isFxBaseCurrencyCollateralCurrency, baseDiscountingCurve, cal)
        else:
            raise ValueError(f"Unsupported ticker {ticker} for OIS rate helper")


    return helper

# https://stackoverflow.com/questions/78810877/sofr-swap-npv-and-cashflow-different-from-bbg-results-using-python-quantlib
def parse_yield_curve(yc_raw, parsed_market_objects):
    cal = USCalendar()
    name = yc_raw['Name']
    curve_type = name.split('.')[1].upper()
    data = yc_raw['Data']
    marketDate = YYYYMMDDHyphenToQlDate(yc_raw['Date'])
    ql.Settings.instance().evaluationDate = marketDate
    rateHelpers = data.apply(lambda x: create_rate_helper(x, yc_raw, parsed_market_objects), axis=1)
    yc = ql.PiecewiseLogLinearDiscount(marketDate, rateHelpers, ql.Actual365Fixed())
    # yc = ql.PiecewiseLogCubicDiscount(marketDate, rateHelpers, ql.Actual365Fixed())
    yc.enableExtrapolation()
    yc_handler = ql.YieldTermStructureHandle(yc)
    return yc_handler

def SOFR_index(yc = None):
    if yc:
        return ql.OvernightIndex("SOFR", 0, ql.USDCurrency(), USCalendar(), ql.Actual360(), yc)
    else:
        return ql.OvernightIndex("SOFR", 0, ql.USDCurrency(), USCalendar(), ql.Actual360())

def SOFR_FUTURE_rate_helper(price, ticker, convexityAdjustment = 0.):
    priceQuote = ql.QuoteHandle(ql.SimpleQuote(price))
    convexQuote = ql.QuoteHandle(ql.SimpleQuote(convexityAdjustment))

    startDate, maturityDate = SOFR_futures_reference_peiord(ticker)
    periodMonths = sofr_expiry_months[ticker[:2]]
    ave = ql.RateAveraging.Compound if periodMonths == 3 else ql.RateAveraging.Simple
    return ql.OvernightIndexFutureRateHelper(priceQuote, pyDateToQlDate(startDate), pyDateToQlDate(maturityDate), SOFR_index(), convexQuote, ave)
