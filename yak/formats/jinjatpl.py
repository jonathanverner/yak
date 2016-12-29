import functools
import logging
import jinja2
from jinja2.filters import environmentfilter

from yak.meta import meta_format
from yak.content import content_format


logger = logging.getLogger(__name__)

jinja_env = jinja2.Environment(extensions=['jinja2.ext.autoescape'])
template_cache = {}
TEMPLATE_FILTERS = {}


def template_filter(name):
    def wrap(filter):
        jinja_env.filters[name] = filter
        TEMPLATE_FILTERS[name] = filter
        return filter
    return wrap


def template_env_filter(name):
    def wrap(filter):
        filter = environmentfilter(filter)
        jinja_env.filters[name] = filter
        TEMPLATE_FILTERS[name] = filter
        return filter
    return wrap


def find_template(tpl_name):
    parts = tpl_name.split('.')
    tpl_extension = parts[-1]
    for i in range(len(parts)-1, 0, -1):
        test_name = '.'.join(parts[:i]+[tpl_extension])
        try:
            return jinja_env.get_template(test_name)
        except jinja2.TemplateNotFound:
            pass
        except Exception as ex:
            logger.error("Error parsing template: %s (%s)'", test_name, ex)
    logger.critical("Template '%s' could not be loaded, giving up.", tpl_name)
    exit(1)


def render_template(tpl_name, context):
    if tpl_name not in template_cache:
        template_cache[tpl_name] = find_template(tpl_name)
    return template_cache[tpl_name].render(context)


def render_from_string(src, context):
    tpl = jinja_env.from_string(src)
    return tpl.render(context)


def equalto_test(a, b):
    return a == b


def notequalto_test(a, b):
    return not equalto_test(a, b)


jinja_env.tests['equalto'] = equalto_test
jinja_env.tests['not equalto'] = equalto_test


@meta_format('jinja')
def meta_jinja_format(val, meta):
    return render_from_string(val, meta)


@content_format('tpl')
def content_jinja_format(content, context):
    return render_from_string(content, context)


import yak.formats.jinja_plugins
