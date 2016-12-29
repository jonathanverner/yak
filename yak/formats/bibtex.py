from .meta import meta_format

try:
    from pybtex.database.input.bibtex import Parser as BibParser
    P = BibParser()
    P.macros['true'] = True

    CONVERT_KEYS = ['title', 'pages']

    def fromBTeX(t):
        ret = t.replace('{', '').replace('}', '').replace("\\'\\i", u'í').replace('\\vc', u'č').replace('---', '&mdash;').replace('--', '&ndash;')
        return ret.replace('\\textendash', '&ndash;')

    @meta_format('bib')
    def meta_bib_format(val, meta):
        bib = P.parse_file(val)
        ret = []
        for entry in bib.entries.values():
            pub = {'type': entry.type}
            pub.update(entry.fields)
            authors = entry.persons.get('author', [])
            editors = entry.persons.get('editor', [])
            pub['author'] = [{"first": fromBTeX(a.first()[0]), "last": fromBTeX(a.last()[0])} for a in authors]
            pub['editor'] = [{"first": fromBTeX(a.first()[0]), "last": fromBTeX(a.last()[0])} for a in editors]
            for k in CONVERT_KEYS:
                if k in pub:
                    pub[k] = fromBTeX(pub[k])
            if 'year' not in pub:
                pub['year'] = float('inf')
            else:
                pub['year'] = int(pub['year'])
            ret.append(pub)
        return ret
except:
    pass

