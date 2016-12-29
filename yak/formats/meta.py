META_FORMATS = {}


def meta_format(name):
    def wrap(fmt):
        META_FORMATS[name] = fmt
        return fmt
    return wrap


try:
    from dateutil import parser as dateparser

    def parse_date(val):
        return dateparser.parse(val)
except:
    def parse_date(val):
        raise BaseException("Date Parser unavailable")
