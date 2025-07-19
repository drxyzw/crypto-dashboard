from workalendar.usa import UnitedStates
from workalendar.europe import UnitedKingdom
import QuantLib as ql
HOLIDAY_YEARS = list(range(2020, 2080 + 1))

def USCalendar(subType = ql.UnitedStates.SOFR):
    cal = ql.WeekendsOnly()
    us_cal = UnitedStates()
    us_holidays = [us_cal.holidays(y) for y in HOLIDAY_YEARS]
    us_holidays = sum(us_holidays, []) # make it flat
    for d, _ in us_holidays:
        cal.addHoliday(ql.Date(d.day, d.month, d.year))

    if subType == ql.UnitedStates.SOFR:
        # special market closure date on 18 April 2025
        # https://www.newyorkfed.org/markets/opolicy/operating_policy_250328a
        cal.addHoliday(ql.Date(18, 4, 2025))

    return cal

def UKCalendar():
    cal = ql.WeekendsOnly()
    uk_cal = UnitedKingdom()
    uk_holidays = [uk_cal.holidays(y) for y in HOLIDAY_YEARS]
    uk_holidays = sum(uk_holidays, []) # make it flat
    for d, _ in uk_holidays:
        cal.addHoliday(ql.Date(d.day, d.month, d.year))

    return cal

def UKorUSCalendar():
    cal = ql.WeekendsOnly()
    us_cal = UnitedStates()
    us_holidays = [us_cal.holidays(y) for y in HOLIDAY_YEARS]
    us_holidays = sum(us_holidays, []) # make it flat
    us_holidays = [p[0] for p in us_holidays]

    uk_cal = UnitedKingdom()
    uk_holidays = [uk_cal.holidays(y) for y in HOLIDAY_YEARS]
    uk_holidays = sum(uk_holidays, []) # make it flat
    uk_holidays = [p[0] for p in uk_holidays]

    # To have business day of UK OR US, only add common holidays of UK and US
    for d in uk_holidays:
        if d in us_holidays:
            cal.addHoliday(ql.Date(d.day, d.month, d.year))

    return cal

