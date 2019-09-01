"""
Helpers for joining together things
"""

Path = None
list_types = (list, tuple)


def dot_joiner(item, item_type=None):
    """Join lists of list of strings with a single dot in between each"""
    if item_type is str:
        return item
    else:
        return dot_join_item(item, item_type or type(item))


def dot_join_item(item, item_type):
    """
    Join list of strings with a single dot in between each

    Note that if the items have dots in them, then it's possible to have multiple dots.

    This is fine, as long as we are consistent
    """
    if item_type not in list_types:
        return str(item)

    result = []
    for part in item:
        part_type = type(part)
        global Path
        if Path is None:
            from .path import Path

        if part_type is Path:
            joined = part.joined()
            if joined:
                result.append(joined)
            continue

        if part_type in list_types:
            part = "".join(part)

        if part:
            result.append(part)

    return ".".join(str(part) for part in result)


def join(one, two):
    """
    Join two paths together

    Where either path is either string, list of strings or Path
    """
    global Path
    if Path is None:
        from .path import Path

    if isinstance(one, Path):
        one = one.path
    if isinstance(two, Path):
        two = two.path

    if isinstance(one, str):
        if isinstance(two, str):
            joined = [one] + [two]
        else:
            joined = [one] + two
    else:
        if isinstance(two, str):
            joined = one + [two]
        else:
            joined = one + two

    return [item for item in joined if item]
