import functools
import logging
import re

from plugins.assets import scan_html_for_assets
from formats.jinjatpl import jinja_env

logger = logging.getLogger(__name__)

META_FORMATS = {}


def meta_format(name, fmt):
    fmt = functools.wraps(fmt)
    META_FORMATS[name] = fmt


try:
    from dateutil import parser as dateparser

    def parse_date(val):
        return dateparser.parse(val)
except:
    def parse_date(val):
        raise BaseException("Date Parser unavailable")


def default_meta_format(val, meta):
    try:
        return int(val)
    except:
        pass

    try:
        return float(val)
    except:
        pass

    try:
        return parse_date(val)
    except:
        pass

    if re.match('True', val, re.IGNORECASE):
        return True
    if re.match('False', val, re.IGNORECASE):
        return False

    return val


def add_key_to_meta(key, format, val, meta):
    if key is None:
        return
    load_func = META_FORMATS.get(format, default_meta_format)
    try:
        meta[key] = load_func(val, meta)
        if hasattr(load_func, 'scan_assets'):
            meta[key] = scan_html_for_assets(jinja_env, meta[key])
    except Exception as e:
        if load_func is not default_meta_format:
            logger.error("Error parsing key '"+key+"' (format:"+format+"), Exception: "+str(e))
            logger.warn("Unable to parse value '"+val+"'")
        meta[key] = val
