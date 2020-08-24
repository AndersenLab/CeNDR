from datetime import datetime


def comma(value):
    return "{:,.0f}".format(value)


def format_release(value):
    return datetime.strptime(str(value), '%Y%m%d').strftime('%Y-%m-%d')
