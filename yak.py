#!/usr/bin/env python2
# -*- coding:utf-8 -*-

from __future__ import print_function

import os
import sys
import sha
import posixpath
import argparse
import logging
import re
import json
import subprocess

logging.basicConfig()
logger = logging.getLogger("wg")


def resolve_attr(obj, attribute):
    path = attribute.split('.')
    for p in path:
        if not hasattr(obj, p):
            try:
                obj = obj[p]
            except:
                return None
        else:
            obj = getattr(obj, p)
    return obj


def deep_copy(d, depth=4):
    if depth <= 0:
        return d
    if hasattr(d, "deep_copy"):
        return d.deep_copy(depth=depth-1)
    elif isinstance(d, dict):
        ret = {}
        for (k, v) in d.items():
            ret[k] = deep_copy(v, depth=depth-1)
        return ret
    elif isinstance(d, list):
        ret = []
        for i in d:
            ret.append(deep_copy(i, depth=depth-1))
        return ret
    else:
        return d


def hash(path):
    data = open(path).read()
    h = sha.sha(data)
    return h.hexdigest()


def pipe(program, input, cwd=None):
    p = subprocess.Popen(program, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True, cwd=cwd)
    return p.communicate(input)[0]

try:
    from scss import Scss
    import os
    compiler = Scss()

    def sass_filter(bytes, cwd):
        os.chdir(cwd)
        return compiler.compile(bytes)
except:
    def sass_filter(bytes, cwd):
        return pipe('sass --scss', bytes, cwd=cwd)

INSTALL_FILTERS = {
    'sass': sass_filter
}


def cp(src, dst, create_parents=False, filters=[]):
    src_dir = os.path.dirname(src)
    if create_parents:
        mkdir_p(os.path.dirname(dst))
    s = open(src).read()
    for f in filters:
        if f in INSTALL_FILTERS:
            s = INSTALL_FILTERS[f](s, cwd=src_dir)
        else:
            s = pipe(f, s, cwd=src_dir)
    open(dst, 'w').write(s)


def mkdir_p(path):
    dirs = path.split(os.sep)
    parent = ''
    for d in dirs:
        path = parent+d
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise BaseException("Path component '"+parent+d+"' is a file")
        else:
            os.mkdir(path)
        parent = parent + d + posixpath.sep


def ls(path, pattern, recursive):
    ret = []
    if not os.path.isdir(path):
        return [path]
    for node in os.listdir(path):
        try:
            if re.match(pattern, node):
                node_path = os.path.join(path, node)
                if os.path.isdir(node_path):
                    if recursive:
                        ret.extend(ls(os.path.join(node_path), pattern, recursive))
                else:
                    ret.append(node_path)
        except Exception as e:
            logger.error("Exception "+str(e)+" when listing assets in '"+path+"' matching pattern '"+pattern+"'")
    return ret


def get_extension(path):
    base = os.path.basename(path)
    n = len(base)-1
    while n >= 0:
        if base[n] == '.':
            return base[n+1:]
        n = n-1
    return base


def strip_extension(path):
    base = os.path.basename(path)
    n = len(base)-1
    while n >= 0:
        if base[n] == '.':
            return base[:n]
        n = n-1
    return base



import jinja2
from jinja2.filters import environmentfilter
jinja_env = jinja2.Environment(extensions=['jinja2.ext.autoescape'])
jinja_env.assets = {}
jinja_env.missing_assets = {}


def json_filter(value):
    return json.dumps(value)


def get_asset_url(env, path):
    if not path in env.assets:
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


@environmentfilter
def asset_filter(env, value, asset_path, **kwargs):
    if len(value) > 0:
        path = asset_path+'/'+value
    else:
        path = asset_path
    if 'cdn' in kwargs:
        return env.config['cdn']+path
    path = get_asset_url(env,path)
    return path


HTML_ASSET_PATTERN = re.compile("""
    (?P<full>(?P<attr>src\s*=\s*)(?P<quote>["'])
    (?P<url>[^'"]*)["'])
""", re.VERBOSE | re.IGNORECASE)


def scan_html_for_assets(env, html):

    def add_url_hash(match):
        match = match.groupdict()
        if match['url'].startswith('/'):
            return match['attr']+match['quote'] + get_asset_url(env,match['url'])+match['quote']
        elif match['url'].startswith('cdn://'):
            return match['attr']+match['quote'] + env.config['cdn'] + match['url'][5:] +match['quote']
        else:
            return match['full']
    return HTML_ASSET_PATTERN.sub(add_url_hash, html)

def youtube_filter(video, playlist, width='"853"', height='"480"'):
    return '<iframe width={width} height={height} src="https://www.youtube-nocookie.com/embed/{id}?list={playlist_id}&amp;showinfo=0" frameborder="0" allowfullscreen></iframe>'.format(id=video, playlist_id=playlist, width=width, height=height)

def vimeo_filter(video, color=None, width="700px", height="394px", title=False, byline=False, portrait=False, frameborder="0", css_class=""):
    attrs = {
              'width': width,
              'height': height,
              'frameborder': frameborder,
              "class": css_class
              }
    params = {
              'title': '0',
              'byline': '0',
              'portrait': '0'
             }
    if title:
        params['title'] = '1'
    if byline:
        params['byline'] = '1'
    if color:
        params['color'] = color
    if portrait:
        params['portrait'] = portrait
    query_string = '&'.join([str(key)+'='+str(val) for (key, val) in params.items()])
    attr_string = ' '.join([str(key)+'="'+str(val)+'"' for (key, val) in attrs.items()])
    return '<iframe src="https://player.vimeo.com/video/{video_id}?{query_string}" {attr_string} webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>'.format(video_id=video, query_string=query_string, attr_string=attr_string)


def doi_filter(value):
    return 'https://dx.doi.org/'+value

def arxiv_filter(value):
    return 'https://arxiv.org/abs/'+value


def split_filter(value, delimiter=","):
    return value.split(delimiter)


def equalto_test(a, b):
    return a == b


def notequalto_test(a, b):
    return not equalto_test(a, b)


template_cache = {}


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
    if not tpl_name in template_cache:
        template_cache[tpl_name] = find_template(tpl_name)
    return template_cache[tpl_name].render(context)


def render_from_string(src, context):
    tpl = jinja_env.from_string(src)
    return tpl.render(context)


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
                        if isinstance(pg['Meta']['Template'],dict):
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


def meta_json_format(val, meta):
    return json.loads(val)


def meta_jsonfile_format(val, meta):
    return json.load(open('./'+val))


def meta_csv_format(val, meta):
    options = {
        'separator': ',',
        'startline': '1'
    }
    options.update(json.loads(val))
    headers = options.get('headers', None)
    csv = []
    startline = int(options['startline'])
    for l in open('./'+options['file']).readlines():
        l = unicode(l, encoding='utf-8').strip()
        if startline > 1:
            startline = startline - 1
            continue
        raw_row = l.split(options['separator'])
        if headers is None:
            csv.append(raw_row)
        else:
            row = {}
            for n in range(min(len(raw_row), len(headers))):
                row[headers[n]] = raw_row[n]
            csv.append(row)
    return csv


def meta_jinja_format(val,meta):
    return render_from_string(val,meta)

def meta_dir_format(val,meta):
    if os.path.isdir('./'+val):
        return os.listdir('./'+val)
    else:
        pattern = os.path.basename(val)
        dirname = './'+os.path.dirname(val)
        return [f for f in os.listdir(dirname) if re.match(pattern,f)]

def meta_str_format(val,meta):
    return val

META_FORMATS = {
    'dir':meta_dir_format,
    'jinja':meta_jinja_format,
    'csv':meta_csv_format,
    'jsonfile':meta_jsonfile_format,
    'json':meta_json_format,
    'str':meta_str_format
}

try:
    from pybtex.database.input.bibtex import Parser as BibParser
    P = BibParser()
    P.macros['true']=True

    CONVERT_KEYS=['title','pages']
    def fromBTeX(t):
        ret = t.replace('{','').replace('}','').replace("\\'\\i",u'í').replace('\\vc',u'č').replace('---','&mdash;').replace('--','&ndash;')
        return ret.replace('\\textendash','&ndash;')

    def meta_bib_format(val,meta):
        bib = P.parse_file(val)
        ret = []
        for entry in bib.entries.values():
            pub = {'type':entry.type}
            pub.update(entry.fields)
            authors = entry.persons.get('author',[])
            editors = entry.persons.get('editor',[])
            pub['author'] = [ {"first":fromBTeX(a.first()[0]), "last":fromBTeX(a.last()[0])} for a in authors ]
            pub['editor'] = [ {"first":fromBTeX(a.first()[0]), "last":fromBTeX(a.last()[0])} for a in editors ]
            for k in CONVERT_KEYS:
                if k in pub:
                    pub[k] = fromBTeX(pub[k])
            if 'year' not in pub:
                pub['year'] = float('inf')
            else:
                pub['year'] = int(pub['year'])
            ret.append(pub)
        return ret

    META_FORMATS['bib'] = meta_bib_format

except:
    pass

try:
    from dateutil import parser as dateparser
    def parse_date(val):
        return dateparser.parse(val)
except:
    def parse_date(val):
        raise BaseException("Date Parser unavailable")

def guess_meta_format(val,meta):
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

    if re.match('True',val,re.IGNORECASE):
        return True
    if re.match('False',val,re.IGNORECASE):
        return False

    return val

def add_key_to_meta(key,format,val,meta):
    if key is None:
        return
    load_func = META_FORMATS.get(format,guess_meta_format)
    try:
        meta[key]=load_func(val,meta)
        if hasattr(load_func,'scan_assets'):
            meta[key] = scan_html_for_assets(jinja_env,meta[key])
    except Exception as e:
        if load_func is not guess_meta_format:
            logger.error("Error parsing key '" +key+ "' (format:"+format+"), Exception: "+str(e))
            logger.warn("Unable to parse value '"+val+"'")
        meta[key]=val

SECTION_DELIMITER_PATTERN=re.compile("(----*)|(\*\*\*\**)|(####*)|(%%%%*)")
META_PATTERN=re.compile("""
    \s*^-
    (?P<key>[a-zA-Z]*)\s*               # Key
    (?:\((?P<format>[^)]*)\))*\s*       # Optional format
    :(?P<val>.*)                        # First line of value
    """,re.VERBOSE
)
def load_file(file):
    format = get_extension(file)
    meta={}
    current_key, current_val, current_format = None, '', None
    content, content_before_meta = unicode(""), unicode("")
    section = "before_meta"
    for l in open(file).readlines():
        l = unicode(l,encoding='utf-8',errors='ignore')
        if section == "content":
            content = content + l
        elif section == "meta":
            if SECTION_DELIMITER_PATTERN.match(l):
                add_key_to_meta(current_key,current_format,current_val,meta)
                section = "content"
            else:
                m = META_PATTERN.match(l)
                if m:
                    add_key_to_meta(current_key,current_format,current_val,meta)
                    current_key=m.group('key')
                    current_format=m.group('format')
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


def content_asis_format(content, context):
    return content


def content_jinja_format(content, context):
    return render_from_string(content, context)



CONTENT_FORMATS = {
    'html': content_asis_format,
    'jinja': content_jinja_format,
    'tpl': content_jinja_format
}

try:
    import markdown

    def content_md_format(content, context):
        return markdown.markdown(content, extensions=['markdown.extensions.codehilite', 'markdown.extensions.fenced_code'])

    def content_tmd_format(content, context):
        return content_md_format(content_jinja_format(content, context), context)

    def meta_md_format(val, meta):
        return markdown.markdown(val)

    content_md_format.scan_assets = True
    meta_md_format.scan_assets = True

    CONTENT_FORMATS['md'] = content_md_format
    CONTENT_FORMATS['tmd'] = content_tmd_format
    META_FORMATS['md'] = meta_md_format

except:
    pass


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

def process_tree(tree,global_ctx={},dest_path='./website',dry_run=False):
    ctx = {}
    ctx.update(global_ctx)
    ctx.update(tree)
    index_path = os.path.join(dest_path,tree['OutFile'])
    if not tree.get('Virtual',False):
        index = render_node(tree,ctx)
    if not dry_run and not tree.get('Virtual',False):
        if not os.path.isdir(dest_path):
            mkdir_p(dest_path)
        logger.info("Writing "+index_path)
        open(index_path,'w').write(index.encode('utf-8'))
    for child in tree['Children']:
        if child.get("Type","page") == 'index':
            ch_path = os.path.join(dest_path,child['Name'])
        else:
            ch_path = dest_path
        process_tree(child,global_ctx,ch_path,dry_run)
    if 'Group' in tree and 'GenerateChildren' in tree['Group']:
        for child in tree['Group']['GenerateChildren']:
            process_tree(child,global_ctx,dest_path,dry_run)


def scan_assets(install_list):
    asset_list = {}
    for item in install_list:
        pattern = item.get('pattern','.*')
        recursive = ('recursive' in item and item['recursive']=="true")
        transform_src_pat, transform_dest_repl = item.get('transform',':').split(':')
        filters = item.get('filters',[])
        copy = ('force' in item and item['force'] == "true")
        item_list = ls(item['src'],pattern,recursive)
        rel_start=len(item['src'])
        for i in item_list:
            asset_key = re.sub(transform_src_pat, transform_dest_repl, '/'+item['dst']+i[rel_start:])
            asset_list[asset_key]= {
                'src':i,
                'copy':copy,
                'hash':None,
                'filters':filters
            }
    logger.debug("ASSET LIST")
    logger.debug(asset_list)
    return asset_list

def parse_args():
  parser = argparse.ArgumentParser(description='A static website generator')
  parser.add_argument('command', choices=['compile','serve','list-assets','list-formats'])
  parser.add_argument('--verbose', '-v', action='count',help='be verbose',default=0)
  parser.add_argument('--sources', '-s', help='the directory with source files', default=None)
  parser.add_argument('--templates', '-t', help='the directory with template files',default=None)
  parser.add_argument('--filters', help='the directory containing custom filters',default=None)
  parser.add_argument('--website', '-w', help='the directory with the website',default=None)
  parser.add_argument('--config',help='the JSON file containing site configuration',default='./config.json')
  parser.add_argument('--context','-c',type=argparse.FileType('r'),help='additional global context')
  parser.add_argument('--port',type=int,help='the port to run the devel server on',default='8080')
  parser.add_argument('--profile',help='the profile to choose',default=None)
  parser.add_argument('--theme',help='use a theme',default=None)
  parser.add_argument('--skipassets',help='do not copy assets',default=False)

  return parser.parse_args()

def main():
    args = parse_args()
    logger.setLevel(logging.ERROR-args.verbose*10)
    cfg = json.load(open(args.config))
    if args.profile is None:
        profile_name = cfg.get('default_profile',None)
    else:
        profile_name = args.profile

    if profile_name is not None:
        try:
            profile = cfg.get('profiles',{})[profile_name]
            cfg.update(profile)
        except KeyError as e:
            logger.fatal('No such profile '+ profile_name)
            logger.fatal('Available profiles:'+' '.join(cfg.get('profiles',{}).keys()))
            exit(1)

    if args.sources is None:
        args.sources=cfg.get('sources','source')
    if args.templates is None:
        args.templates=cfg.get('templates','templates')
    if args.website is None:
        args.website=cfg.get('website','website')
    if args.filters is None:
        args.filters=cfg.get('filters','filters')

    if args.command == 'compile' or args.command == 'list-assets':

        jinja_env.config = cfg
        jinja_env.filters['json']=json_filter
        jinja_env.filters['asset']=asset_filter
        jinja_env.filters['DOI']=doi_filter
        jinja_env.filters['ARXIV']=arxiv_filter
        jinja_env.filters['VIMEO']=vimeo_filter
        jinja_env.filters['YOUTUBE']=youtube_filter
        jinja_env.filters['split']=split_filter

        try:
            custom_filters = __import__(args.filters)
            for f_name in custom_filters.__all__:
                logger.info("Loading filter %s",f_name)
                jinja_env.filters[f_name] = getattr(custom_filters,f_name)
        except Exception as ex:
            logger.error("Could not load custom filters: %s",repr(ex))

        jinja_env.tests['equalto']=equalto_test
        jinja_env.tests['not equalto']=equalto_test
        jinja_env.loader=jinja2.FileSystemLoader([args.templates])
        if 'assets' in cfg:
            jinja_env.assets = scan_assets(cfg['assets'])
        else:
            jinja_env.assets = {}
        jinja_env.missing_assets={}

        default_template_base = strip_extension(cfg.get('default_template','base.tpl'))
        tree = build_web_tree(args.sources,base_dir=args.sources,default_template_base=default_template_base)

        global_ctx={'type':type}
        global_ctx['website']=tree
        global_ctx['config']=cfg

        process_tree(tree,global_ctx,args.website,dry_run=(args.command =='list-assets'))

        if args.command == 'list-assets':
            for asset,data in jinja_env.assets.items():
                if data['copy']:
                    print(data['src'],'->',asset, data['hash'])
            if len(jinja_env.missing_assets) > 0:
                print("MISSING:")
                print("\t\n".join(jinja_env.missing_assets.keys()))
        else:
            if not args.skipassets:
                for (asset,data) in jinja_env.assets.items():
                    if data['copy']:
                        dest=args.website+'/'+asset
                        logger.info("Copying '"+data['src']+''" to '"+dest+"'")
                        cp(data['src'],dest,create_parents=True,filters=data['filters'])
                    else:
                        logger.info("Skipping '"+data['src']+"'")
            if len(jinja_env.missing_assets) > 0:
                logger.error("The following assets were not found:")
                logger.error(';'.join(jinja_env.missing_assets.keys()))


    elif args.command == 'serve':
        import SimpleHTTPServer
        sys.argv=['wg.py',str(args.port)]
        os.chdir(args.website)
        SimpleHTTPServer.test()

    elif args.command == 'list-formats':
        print("Metadata Formats:", META_FORMATS.keys())
        print("Content Formats:", CONTENT_FORMATS.keys())

if __name__ == "__main__":
  main()
