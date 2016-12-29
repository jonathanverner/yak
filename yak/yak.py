#!/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import print_function

import os
import sys
import posixpath
import argparse
import logging
import re
import json
import subprocess
import jinja2

from yak.utils import deep_copy, resolve_attr
from yak.shell import get_extension, strip_extension, mkdir_p, cp
from yak.meta import add_key_to_meta, META_FORMATS
from yak.content import render_node
from yak.formats.jinjatpl import jinja_env
from yak.plugins import scan_assets

logging.basicConfig()
logger = logging.getLogger(__name__)


class webnode_list(list):
    def __init__(self, *args, **kwargs):
        super(webnode_list, self).__init__(*args, **kwargs)
        self._map = {}
        for item in self:
            self._map_item__(item)

    def _map_item__(self, item):
        if 'Name' in item:
            self._map[item['Name'].lower()] = item

    def __getattr__(self, attr):
        try:
            super(webnode_list, self).__getattr__(attr)
        except:
            if 'attr' == '_map':
                return self._map
            return self._map[attr.lower()]

    def __getitem__(self, key):
        try:
            super(webnode_list, self).__getitem__(key)
        except Exception as e:
            return self._map[key]

    def deep_copy(self, depth=3):
        if depth <= 0:
            return self
        ret = webnode_list([])
        for item in self:
            ret.append(deep_copy(item, depth=depth-1))
        return ret

    def append(self, item):
        super(webnode_list, self).append(item)
        self._map_item__(item)

    def extend(self, l):
        for i in l:
            self.append(i)


def build_web_tree(path, base_dir='./sources', default_template_base='base', parent=None):
    index_files = ['index.md', 'index.html', 'index.jinja', 'index.tpl', 'index']
    nodes = os.listdir(path)
    tpl_base = path[len(base_dir):].replace('/', '.').strip('.')
    if tpl_base == '':
        tpl_base = default_template_base
    tree = {
        "Content": "",
        "Format": "raw",
        "Meta": {
            "OrderKey": "Position",
            "Template": tpl_base+'.index.tpl',
            "ChildTemplate": tpl_base+'.tpl',
            "ShortName": os.path.basename(path).capitalize()
        },
        "Children": webnode_list([]),
        "OutFile": "index.html",
        "Parent": parent,
        "Name": os.path.basename(path),
        "URL": path[len(base_dir):]+'/',
        "Type": "index"
    }
    position = 0
    have_index = False
    for i in index_files:
        ipath = os.path.join(path, i)
        if os.path.exists(ipath):
            if have_index:
                logger.warn("Multiple index files in " + path)
            position = position + 1
            index = load_file(ipath)
            tree['Meta'].update(index['Meta'])
            tree['Format'] = index['Format']
            tree['Content'] = index['Content']
            have_index = True
    if not have_index:
        logger.warn("No index file in " + path)
    for node in nodes:
        position = position + 1
        npath = os.path.join(path, node)
        if node in index_files:
            position = position - 1
        elif node.startswith('.'):
            position = position - 1
        elif os.path.isdir(npath):
            subtree = build_web_tree(npath, base_dir=base_dir, default_template_base=default_template_base, parent=tree)
            subtree['Position'] = position
            tree['Children'].append(subtree)
        else:
            child = load_file(npath)
            child['Position'] = position
            child['Parent'] = tree
            child['URL'] = tree['URL']+child['Name']+'.html'
            if 'Template' not in child['Meta']:
                child['Meta']['Template'] = tree['Meta']['ChildTemplate']
            if isinstance(child['Meta']['Template'], dict):
                child['URL'] = tree['URL']+child['Name']
                child_copy = deep_copy(child)
                for (subpage, tpl) in child['Meta']['Template'].items():
                    pg = deep_copy(child_copy)
                    pg['Name'] = subpage.lower()
                    if tpl == '':
                        pg['Meta']['Template'] = tree['Meta']['ChildTemplate']
                        if isinstance(pg['Meta']['Template'], dict):
                            pg['Meta']['Template'] = pg['Meta']['Template'][subpage]
                            if pg['Meta']['Template'] == '':
                                pg['Meta']['Template'] = tpl_base+'.tpl'
                    else:
                        pg['Meta']['Template'] = tpl
                    pg['Parent'] = child
                    pg['OutFile'] = pg['Name']+'.html'
                    pg['URL'] = child['URL']+'/'+pg['OutFile']
                    pg['Children'] = webnode_list([])
                    child['Children'].append(pg)
                child['Virtual'] = True
            tree['Children'].append(child)
    if 'GroupBy' in tree['Meta']:
        subtrees = []
        index_page = None
        for (name, grouping) in tree['Meta']['GroupBy'].items():
            group_subtree = {
                'Name': name.lower(),
                'URL': tree['URL']+name.lower()+'/',
                "Type": "index",
                "Parent": tree,
                "Children": webnode_list([]),
                "Content": tree["Content"],
                "Format": tree["Format"],
                "Meta": tree["Meta"],
                "Virtual": True,
                "OutFile": "index.html"
            }
            page_template = {
                "Parent": group_subtree,
                "Children": webnode_list([]),
                "Content": tree["Content"],
                "Format": tree["Format"],
                "Meta": tree["Meta"],
                "Group": {
                    "Parent": tree,
                    "Children": webnode_list([]),
                    "NumPages": 0,
                    "First": False,
                    "Last": False,
                    "FirstURL": "",
                    "LastURL": "",
                    "PrevURL": "",
                    "NextURL": ""
                }
            }
            all = deep_copy(page_template)
            all["Name"] = "all"
            all["URL"] = tree['URL']+name.lower()+'/all.html'
            all["OutFile"] = "all.html"
            for ch in tree['Children']:
                nch = deep_copy(ch)
                nch['Virtual'] = True
                all['Group']['Children'].append(nch)
            group_subtree['Children'].append(all)
            if grouping['Type'] == 'Size':
                if 'SortBy' in grouping:
                    tree['Children'] = sorted(tree['Children'], key=lambda x: x['Meta']['Date'], reverse=True)
                pg_size = grouping['PageSize']
                num_pages = len(tree['Children'])/pg_size
                if len(tree['Children']) % pg_size > 0:
                    num_pages += 1
                page_template["Group"]["NumPages"] = num_pages
                page_template["Group"]["FirstURL"] = tree['URL']+name.lower()+'/1.html'
                page_template["Group"]["LastURL"] = tree['URL']+name.lower()+'/'+str(num_pages)+'.html'
                for pg in range(num_pages):
                    pg_node = deep_copy(page_template)
                    pg_node['Name'] = str(pg+1)
                    pg_node['URL'] = tree['URL']+name.lower()+'/'+str(pg+1)
                    pg_node['OutFile'] = str(pg+1)+'.html'
                    pg_node['Group']['Children'].extend(tree['Children'][pg*pg_size:(pg+1)*pg_size])
                    if pg == 0:
                        if index_page is None:
                            index_page = pg_node
                        pg_node["Group"]["First"] = True
                    if pg == (num_pages-1):
                        pg_node["Group"]["Last"] = True
                    pg_node["Group"]["PrevURL"] = tree['URL']+name.lower()+'/'+str(max(pg, 1))+'.html'
                    pg_node["Group"]["NextURL"] = tree['URL']+name.lower()+'/'+str(min(pg+2, num_pages))+'.html'
                    group_subtree['Children'].append(pg_node)
            elif grouping['Type'] == 'Attribute':
                attr = grouping['Attribute']
                vals = set([])
                if 'SortBy' in grouping:
                    tree['Children'] = sorted(tree['Children'], key=lambda x: x['Meta']['Date'], reverse=True)
                for ch in tree['Children']:
                    val = resolve_attr(ch, attr)
                    if val is not None:
                        if isinstance(val, list):
                            vals.update(val)
                        else:
                            vals.add(val)
                for pg in vals:
                    pg_node = deep_copy(page_template)
                    pg_node['Group']['NoPagination'] = True
                    pg_node['Name'] = unicode(pg).lower()
                    pg_node['OutFile'] = unicode(pg).lower()+'.html'
                    pg_node['URL'] = tree['URL']+name.lower()+'/'+unicode(pg).lower()
                    for ch in tree['Children']:
                        val = resolve_attr(ch, attr)
                        if val is not None:
                            if (isinstance(val, list) and pg in val) or (val == pg):
                                nch = deep_copy(ch)
                                nch['Virtual'] = True
                                pg_node['Group']['Children'].append(nch)
                    group_subtree['Children'].append(pg_node)
            subtrees.append(group_subtree)
        tree['Group'] = {
            'GenerateChildren': tree['Children']
        }
        tree['Group'].update(index_page["Group"])
        tree['Children'] = subtrees

    return tree


SECTION_DELIMITER_PATTERN = re.compile("(----*)|(\*\*\*\**)|(####*)|(%%%%*)")

META_PATTERN = re.compile("""
    \s*^-
    (?P<key>[a-zA-Z]*)\s*               # Key
    (?:\((?P<format>[^)]*)\))*\s*       # Optional format
    :(?P<val>.*)                        # First line of value
    """, re.VERBOSE
)


def load_file(file):
    format = get_extension(file)
    meta = {}
    current_key, current_val, current_format = None, '', None
    content, content_before_meta = unicode(""), unicode("")
    section = "before_meta"
    for l in open(file).readlines():
        l = unicode(l, encoding='utf-8', errors='ignore')
        if section == "content":
            content = content + l
        elif section == "meta":
            if SECTION_DELIMITER_PATTERN.match(l):
                add_key_to_meta(current_key, current_format, current_val, meta)
                section = "content"
            else:
                m = META_PATTERN.match(l)
                if m:
                    add_key_to_meta(current_key, current_format, current_val, meta)
                    current_key = m.group('key')
                    current_format = m.group('format')
                    current_val = m.group('val').strip()
                else:
                    current_val = current_val + l
        elif SECTION_DELIMITER_PATTERN.match(l):
            section = "meta"
        else:
            content_before_meta = content_before_meta + l

    if len(meta) == 0:
        content = content_before_meta + content

    bname = strip_extension(os.path.basename(file))

    if 'ShortName' not in meta and bname != 'index':
        meta['ShortName'] = bname.capitalize()

    return {
        'Name': bname,
        'OutFile': bname+'.html',
        'Meta': meta,
        'Content': content,
        'Format': format,
        'Children': webnode_list([])
    }


def process_tree(tree, global_ctx={}, dest_path='./website', dry_run=False):
    ctx = {}
    ctx.update(global_ctx)
    ctx.update(tree)
    index_path = os.path.join(dest_path, tree['OutFile'])
    if not tree.get('Virtual', False):
        index = render_node(tree, ctx)
    if not dry_run and not tree.get('Virtual', False):
        if not os.path.isdir(dest_path):
            mkdir_p(dest_path)
        logger.info("Writing "+index_path)
        open(index_path, 'w').write(index.encode('utf-8'))
    for child in tree['Children']:
        if child.get("Type", "page") == 'index':
            ch_path = os.path.join(dest_path, child['Name'])
        else:
            ch_path = dest_path
        process_tree(child, global_ctx, ch_path, dry_run)
    if 'Group' in tree and 'GenerateChildren' in tree['Group']:
        for child in tree['Group']['GenerateChildren']:
            process_tree(child, global_ctx, dest_path, dry_run)


def parse_args():
    parser = argparse.ArgumentParser(description='A static website generator')
    parser.add_argument('command', choices=['compile', 'serve', 'list-assets', 'list-formats'])
    parser.add_argument('--verbose', '-v', action='count', help='be verbose', default=0)
    parser.add_argument('--sources', '-s', help='the directory with source files', default=None)
    parser.add_argument('--templates', '-t', help='the directory with template files', default=None)
    parser.add_argument('--filters', help='the directory containing custom filters', default=None)
    parser.add_argument('--website', '-w', help='the directory with the website', default=None)
    parser.add_argument('--config', help='the JSON file containing site configuration', default='./config.json')
    parser.add_argument('--context', '-c', type=argparse.FileType('r'), help='additional global context')
    parser.add_argument('--port', type=int, help='the port to run the devel server on', default='8080')
    parser.add_argument('--profile', help='the profile to choose', default=None)
    parser.add_argument('--theme', help='use a theme', default=None)
    parser.add_argument('--skipassets', help='do not copy assets', default=False)

    return parser.parse_args()


def main():
    args = parse_args()
    logger.setLevel(logging.ERROR-args.verbose*10)
    cfg = json.load(open(args.config))
    if args.profile is None:
        profile_name = cfg.get('default_profile', None)
    else:
        profile_name = args.profile

    if profile_name is not None:
        try:
            profile = cfg.get('profiles', {})[profile_name]
            cfg.update(profile)
        except KeyError as e:
            logger.fatal('No such profile '+profile_name)
            logger.fatal('Available profiles:'+' '.join(cfg.get('profiles', {}).keys()))
            exit(1)

    if args.sources is None:
        args.sources = cfg.get('sources', 'source')
    if args.templates is None:
        args.templates = cfg.get('templates', 'templates')
    if args.website is None:
        args.website = cfg.get('website', 'website')
    if args.filters is None:
        args.filters = cfg.get('filters', 'filters')

    if args.command == 'compile' or args.command == 'list-assets':

        jinja_env.config = cfg

        try:
            custom_filters = __import__(args.filters)
            for f_name in custom_filters.__all__:
                logger.info("Loading filter %s", f_name)
                jinja_env.filters[f_name] = getattr(custom_filters, f_name)
        except Exception as ex:
            logger.error("Could not load custom filters: %s", repr(ex))

        jinja_env.loader = jinja2.FileSystemLoader([args.templates])
        if 'assets' in cfg:
            jinja_env.assets = scan_assets(cfg['assets'])
        else:
            jinja_env.assets = {}
        jinja_env.missing_assets = {}

        default_template_base = strip_extension(cfg.get('default_template', 'base.tpl'))
        tree = build_web_tree(args.sources, base_dir=args.sources, default_template_base=default_template_base)

        global_ctx = {'type': type}
        global_ctx['website'] = tree
        global_ctx['config'] = cfg

        process_tree(tree, global_ctx, args.website, dry_run=(args.command == 'list-assets'))

        if args.command == 'list-assets':
            for asset, data in jinja_env.assets.items():
                if data['copy']:
                    print(data['src'], '->', asset, data['hash'])
            if len(jinja_env.missing_assets) > 0:
                print("MISSING:")
                print("\t\n".join(jinja_env.missing_assets.keys()))
        else:
            if not args.skipassets:
                for (asset, data) in jinja_env.assets.items():
                    if data['copy']:
                        dest = args.website+'/'+asset
                        logger.info("Copying '"+data['src']+''" to '"+dest+"'")
                        cp(data['src'], dest, create_parents=True, filters=data['filters'])
                    else:
                        logger.info("Skipping '"+data['src']+"'")
            if len(jinja_env.missing_assets) > 0:
                logger.error("The following assets were not found:")
                logger.error(';'.join(jinja_env.missing_assets.keys()))

    elif args.command == 'serve':
        sys.argv = ['yak.py', str(args.port)]
        os.chdir(args.website)
        try:
            import SimpleHTTPServer
            SimpleHTTPServer.test()
        except:
            import http
            http.server.test()

    elif args.command == 'list-formats':
        print("Metadata Formats:", META_FORMATS.keys())
        print("Content Formats:", CONTENT_FORMATS.keys())

if __name__ == "__main__":
    main()
