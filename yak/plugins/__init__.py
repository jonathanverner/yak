import functools

INSTALL_FILTERS = {}


def install_filter(name):
    def wrap(filter):
        INSTALL_FILTERS[name] = filter
        return filter
    return wrap

import assets
import sass
