import json
import os

from yak.formats.meta import meta_format

@meta_format('json')
def meta_json_format(val, meta):
    return json.loads(val)

@meta_format('jsonfile')
def meta_jsonfile_format(val, meta):
    return json.load(open('./'+val))

@meta_format('str')
def meta_str_format(val,meta):
    return val

@meta_format('dir')
def meta_dir_format(val,meta):
    if os.path.isdir('./'+val):
        return os.listdir('./'+val)
    else:
        pattern = os.path.basename(val)
        dirname = './'+os.path.dirname(val)
        return [f for f in os.listdir(dirname) if re.match(pattern,f)]


