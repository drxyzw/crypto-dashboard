import QuantLib as ql
from utils.file import *

class Spot:
    spotRate = None
    spotRateQuote = None
    ccy = None
    name = None
    domesticDiscountingCurveName = None
    foreignDiscountingCurveName = None

    def __init__(self, spot_raw):
        data = convertDataframeToDictionary(spot_raw['Data'])
        
        self.spotRate = data['Spot']
        self.spotQuote = ql.QuoteHandle(ql.SimpleQuote(self.spotRate))
        self.ccy = spot_raw['CCY']
        self.name = spot_raw['Name']
        self.domesticDiscountingCurveName = spot_raw['DomesticDiscountingCurve']
        self.foreignDiscountingCurveName = spot_raw['ForeignDiscountingCurve']

def parse_spot(spot_raw, parsed_market_objects):
    spotObj = Spot(spot_raw)
    return spotObj