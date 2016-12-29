def missing_feature(feat_type, message):
    pass

def resolve_attr(obj, attribute):
    """
        Recursively resolves attribute access on :param:`obj`.
        If the attribute is not present, __getitem__ is tried.

        >>> a = { 'b':{'c':10} }
        >>> resolve_attr(a,'b.c')
        10
        >>>
    """
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
    """
        Make a deep copy of a :class:`list`, :class:`dict` or
        an object with a :method:`deep_copy` method. The depth
        of the copy is controlled via the optional :param:`depth`
        parameter.
    """
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
