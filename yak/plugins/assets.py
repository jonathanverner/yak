import logging
import re

from yak.formats.jinjatpl import template_env_filter
from yak.formats.jinjatpl import jinja_env

jinja_env.assets = {}
jinja_env.missing_assets = {}

logger = logging.getLogger(__name__)


def get_asset_url(env, path):
    if path not in env.assets:
        logger.error("Asset '"+path+"' not found")
        env.missing_assets[path] = True
        return path
    elif env.assets[path]['hash'] is None:
        h = hash(env.assets[path]['src'])
        env.assets[path]['hash'] = h
        env.assets[path]['copy'] = True
        return path + '?' + h
    else:
        return path + '?' + env.assets[path]['hash']


HTML_ASSET_PATTERN = re.compile("""
    (?P<full>(?P<attr>src\s*=\s*)(?P<quote>["'])
    (?P<url>[^'"]*)["'])
""", re.VERBOSE | re.IGNORECASE)


def scan_html_for_assets(env, html):
    def add_url_hash(match):
        match = match.groupdict()
        if match['url'].startswith('/'):
            return match['attr']+match['quote'] + get_asset_url(env, match['url'])+match['quote']
        elif match['url'].startswith('cdn://'):
            return match['attr']+match['quote'] + env.config['cdn'] + match['url'][5:]+match['quote']
        else:
            return match['full']
    return HTML_ASSET_PATTERN.sub(add_url_hash, html)


@template_env_filter('asset')
def asset_filter(env, value, asset_path, **kwargs):
    if len(value) > 0:
        path = asset_path+'/'+value
    else:
        path = asset_path
    if 'cdn' in kwargs:
        return env.config['cdn']+path
    path = get_asset_url(env, path)
    return path


def scan_assets(install_list):
    asset_list = {}
    for item in install_list:
        pattern = item.get('pattern', '.*')
        recursive = ('recursive' in item and item['recursive'] == "true")
        transform_src_pat, transform_dest_repl = item.get('transform', ':').split(':')
        filters = item.get('filters', [])
        copy = ('force' in item and item['force'] == "true")
        item_list = ls(item['src'], pattern, recursive)
        rel_start = len(item['src'])
        for i in item_list:
            asset_key = re.sub(transform_src_pat, transform_dest_repl, '/'+item['dst']+i[rel_start:])
            asset_list[asset_key] = {
                'src': i,
                'copy': copy,
                'hash': None,
                'filters': filters
            }
    logger.debug("ASSET LIST")
    logger.debug(asset_list)
    return asset_list
