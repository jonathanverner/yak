import functools
import logging

from yak.plugins.assets import scan_html_for_assets
from yak.formats.jinjatpl import jinja_env, render_template

logger = logging.getLogger(__name__)


CONTENT_FORMATS = {}


def content_format(name, fmt):
    fmt = functools.wraps(fmt)
    CONTENT_FORMATS[name] = fmt


@content_format('html')
def content_asis_format(content, context):
    return content


def render_node(node, global_ctx):
    node_context = {}
    node_context.update(global_ctx)
    node_context.update(node)
    formatter = CONTENT_FORMATS.get(node['Format'], content_asis_format)
    try:
        formated_content = formatter(node['Content'], node_context)
        if hasattr(formatter, 'scan_assets'):
            formated_content = scan_html_for_assets(jinja_env, formated_content)
    except Exception as e:
        logger.error("Unable to format content of " + node['Name'] + " Exception:" + str(e))
        logger.warn("Offending content:" + node['Content'])
        formated_content = node['Content']
    if node['Meta']['Template'] == 'None':
        return formated_content
    else:
        node_context['Content'] = formated_content
        return render_template(node['Meta']['Template'], node_context)
