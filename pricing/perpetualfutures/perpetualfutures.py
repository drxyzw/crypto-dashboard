import QuantLib as ql
from datetime import datetime

from market.load_market import loadMarket
from market.assset_index.parse_spot import Spot

if __name__ == "__main__":
    py_date = datetime(2025, 6, 20)
    # py_date = dt(2025, 7, 14)

    market = loadMarket(py_date)
    # domYC = market['USD.SOFR.CSA_USD']
    # forYC = market['BTC.FUNDING.CSA_USD']
    # btcSpot = market['BTCUSD.SPOT']

    dc = ql.ActualActual(ql.ActualActual.ISDA)
    cal = ql.NullCalendar()
    today = ql.Date.todaysDate()

    domYC = ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(0.04)), dc))
    forYC = ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(ql.SimpleQuote(0.02)), dc))
    # btcSpot = Spot(10000.)

    fundingTimes = [0.0]
    fundingRates = [0.01]
    ir_diffs = [0.005]
    # fundingTimes = ql.Array(1, 0.0)
    # fundingRates = ql.Array(1, 0.01)
    # ir_diffs = ql.Array(1, 0.005)
    pf = ql.PerpetualFutures(ql.PerpetualFutures.Linear, ql.PerpetualFutures.AHJ, ql.Period(3, ql.Months), cal, dc)
    engine = ql.DiscountingPerpetualFuturesEngine(domYC, forYC, ql.QuoteHandle(ql.SimpleQuote(10000.)), fundingTimes, fundingRates, ir_diffs,
                                                  ql.DiscountingPerpetualFuturesEngine.PiecewiseConstant)
    # engine = ql.DiscountingPerpetualFuturesEngine(domYC, forYC, btcSpot.spotQuote, fundingTimes, fundingRates, ir_diffs)
    pf.setPricingEngine(engine)
    npv = pf.NPV()
    print(f"npv: {npv}")

    print("load")
