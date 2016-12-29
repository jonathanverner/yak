import json

from .meta import meta_format


@meta_format('csv')
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

