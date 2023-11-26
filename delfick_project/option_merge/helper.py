import inspect

from .joiner import dot_joiner
from .merge import MergedOptions


def prefixed_path_list(path, prefix=None):
    """Return the prefixed version of this path as a list"""
    res_type = type(path)
    if prefix:
        res = prefix + path
    else:
        res = list(path)
    return res, dot_joiner(res, res_type)


def prefixed_path_string(path, prefix=""):
    """Return the prefixed version of this string"""
    while path and path[0] == ".":
        path = path[1:]

    while path and path[-1] == ".":
        path = path[:-1]

    while prefix and prefix[0] == ".":
        prefix = prefix[1:]

    while prefix and prefix[-1] == ".":
        prefix = prefix[:-1]

    if not prefix:
        return path, path
    elif not path:
        return prefix, prefix
    else:
        res = "{0}.{1}".format(prefix, path)
        return res, res


def make_dict(first, rest, data):
    """Make a dictionary from a list of keys"""
    last = first
    result = {first: data}
    current = result
    for part in rest:
        current[last] = {}
        current = current[last]
        current[part] = data
        last = part

    return result


def merge_into_dict(target, source, seen=None, ignore=None):
    """Merge source into target"""
    ignores = ignore
    if ignores is None:
        ignores = []

    source = convert_to_dict(source, (), {"seen": seen, "ignore": ignores})

    for key in source.keys():
        if key in ignores:
            continue
        val = source[key]

        is_dict = (
            lambda item: type(item) in (dict, MergedOptions)
            or isinstance(item, dict)
            or hasattr(item, "as_dict")
        )
        if is_dict(val):
            if not is_dict(target.get(key)):
                target[key] = {}
            merge_into_dict(target[key], val, seen=seen, ignore=ignores)
        else:
            target[key] = val


def convert_to_dict(val, args, kwargs):
    """
    Use the val's as_dict method if it exists and return the result from that or
    return val as is.

    We also see if as_dict takes in arguments and if it does, we pass in args
    and kwargs to the as_dict.
    """
    if not hasattr(val, "as_dict"):
        return val

    if hasattr(val, "is_dict") and not val.is_dict:
        return val

    if inspect.signature(val.as_dict).parameters:
        return val.as_dict(*args, **kwargs)
    else:
        return val.as_dict()
