import json
from yak.formats.jinjatpl import template_filter


@template_filter('split')
def split_filter(value, delimiter=","):
    return value.split(delimiter)


@template_filter('json')
def json_filter(value):
    return json.dumps(value)
