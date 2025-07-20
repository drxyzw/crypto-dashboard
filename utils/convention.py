from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from utils.config import * 
from utils.calendar import *

def IMM_date(year, month, must_be_business_day = True):
    d = dt(year=year, month=month, day=15)
    while d.weekday() != 2: # 0=Monday, 1=Tuesday, 2=Wednesday
        d += relativedelta(days=1)
    if must_be_business_day:
        cal = USCalendar(ql.UnitedStates.SOFR)
        ql_date = ql.Date(d.day, d.month, d.year)
        ql_date = cal.adjust(ql_date, ql.Preceding)
        d = ql_date.to_date()

    return d

def nbMonths(tenorStr):
    tenorStrStrip = tenorStr.strip()
    unit = tenorStrStrip[-1].upper()
    nb = int(tenorStrStrip[:-1])
    if unit == "M":
        return nb
    elif unit == "Y":
        return nb * 12
    else:
        raise ValueError(f"nbMonths function does not support a unit: {unit}")

def SOFR_futures_reference_peiord(ticker):
    periodMonths = sofr_expiry_months[ticker[:2]]
    expiry_year = int("20" + ticker[-2:])
    month_flag_dict_reverse = {v: k for k, v in month_flag_dict.items()}
    expiry_month = month_flag_dict_reverse[ticker[2:3]]

    deliveryDate = IMM_date(expiry_year, expiry_month, must_be_business_day=True)
    startDate = deliveryDate - relativedelta(months=periodMonths)
    startDate = IMM_date(startDate.year, startDate.month, must_be_business_day=False)

    return startDate, deliveryDate

def delta_months(datetime1, datetime2):
    delta = relativedelta(datetime2, datetime1)
    return delta.years * 12 + delta.months

def parseToRelativeDelta(tenorStr):
    tenorStrStrip = tenorStr.strip()
    unit = tenorStrStrip[-1].upper()
    nb = int(tenorStrStrip[:-1])
    if unit == "D":
        return relativedelta(days=nb)
    elif unit == "W":
        return relativedelta(days=nb * 7)
    elif unit == "M":
        return relativedelta(months=nb)
    elif unit == "Y":
        return relativedelta(years=nb)
    else:
        raise ValueError(f"nbMonths function does not support a unit: {unit}")


def YYYYMMDDHyphenToQlDate(YYYYMMDDHyphen):
    year, month, day = map(int, YYYYMMDDHyphen.split('-'))
    return ql.Date(day, month, year)

def pyDateToQlDate(pyDate):
    return ql.Date(pyDate.day, pyDate.month, pyDate.year)

def qlDateToPyDate(pyDate):
    return dt(pyDate.year(), pyDate.month(), pyDate.dayOfMonth())

def processBtcFutureExpiryToTicker(expiry_str):
    expiry_str_strip = expiry_str.strip().replace(" ", "")
    year_str = expiry_str_strip[3:]
    month_str = expiry_str_strip[:3]
    month_number = month_name_flag_reverse_dict[month_str]
    month_flag = month_flag_dict[month_number]
    flag = "BTC" + month_flag + year_str
    return flag

def processBtcFutureExpiryToExpiryDate(expiry_str):
    expiry_str_strip = expiry_str.strip().replace(" ", "")
    year_str = "20" + expiry_str_strip[3:]
    month_str = expiry_str_strip[:3]
    month_number = month_name_flag_reverse_dict[month_str]
    cal = UKorUSCalendar()
    ql_date = ql.Date.endOfMonth(ql.Date(1, month_number, int(year_str)))
    ql_date = cal.adjust(ql_date, ql.Preceding)
    # first, check last Friday
    while ql_date.weekday() != ql.Friday:
        ql_date -= 1
    # then adjust
    ql_date = cal.adjust(ql_date, ql.Preceding)
    py_date = ql_date.to_date()
    py_date_str = datetime.strftime(py_date, "%Y-%m-%d")
    return py_date_str
        
def processBtcOptionExpiryToExpiryDate(option_type_str, expiry_str):
    expiry_str_strip = expiry_str.strip().replace(" ", "")
    cal = UKorUSCalendar()
    if option_type_str == "European Options":
        year_str = expiry_str_strip[3:]
        month_str = expiry_str_strip[:3].upper()
        month_number = month_name_flag_reverse_dict[month_str]
        ql_date = ql.Date.endOfMonth(ql.Date(1, month_number, int(year_str)))
        ql_date = cal.adjust(ql_date, ql.Preceding)
        while ql_date.weekday() != ql.Friday:
            ql_date = cal.advance(ql_date, -1, ql.Days, ql.Preceding)
    elif "Weekly " in option_type_str:
        option_types = option_type_str.split(" ")
        dayOfWeek = weekday_flag[option_types[1]]
        expiry_strs = expiry_str.split(" ") # expiry_str is "Week n-MMM YYYY"
        nth_week = int(expiry_strs[1][0])
        expiry_month = month_name_flag_reverse_dict[expiry_strs[1][2:].upper()]
        expiry_year = int(expiry_strs[2])
        ql_date = ql.Date.nthWeekday(nth_week, dayOfWeek, expiry_month, expiry_year)
        while not cal.isBusinessDay(ql_date):
            nth_week += 1
            ql_date = ql.Date.nthWeekday(nth_week, dayOfWeek, expiry_month, expiry_year)
    py_date = ql_date.to_date()
    py_date_str = datetime.strftime(py_date, "%Y-%m-%d")
    return py_date_str


def processBtcOptionNearestFutureExpiryDate(optionExpiryDateStr):
    optionExpiryDate = YYYYMMDDHyphenToQlDate(optionExpiryDateStr)
    year = optionExpiryDate.year()
    month = optionExpiryDate.month()

    while True:
        month_flag = month_name_flag_dict[month]
        expiry_str = month_flag + " " + str(year)[2:]
        futureExpiryDateStr = processBtcFutureExpiryToExpiryDate(expiry_str)
        futureExpiryDate = YYYYMMDDHyphenToQlDate(futureExpiryDateStr)
        # Picking up next available future
        # https://www.cmegroup.com/content/dam/cmegroup/rulebook/CME/IV/350/350A.pdf
        # https://www.cmegroup.com/articles/faqs/frequently-asked-questions-options-on-cryptocurrency-futures.html#underlying   
        if optionExpiryDate <= futureExpiryDate:
            break
        else:
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
    pyFutureExpiryDate = qlDateToPyDate(futureExpiryDate)
    futureExpiryDateStr = pyFutureExpiryDate.strftime("%Y-%m-%d")
    return futureExpiryDateStr


