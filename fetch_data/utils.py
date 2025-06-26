from datetime import datetime

def timestampToDatetime(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000)

def datetimeToTimestamp(dt):
    return int(dt.timestamp() * 1000)

