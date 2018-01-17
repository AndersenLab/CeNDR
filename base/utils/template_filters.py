from datetime import datetime
from base.application import app

#
# Custom Filters
#


@app.template_filter('comma')
def comma_filter(value):
    return "{:,.0f}".format(value)


@app.template_filter('format_release')
def format_release_filter(value):
    return datetime.strptime(str(value), '%Y%m%d').strftime('%Y-%m-%d')

