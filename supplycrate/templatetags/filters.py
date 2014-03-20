import urllib
from jinja2.ext import Extension

__author__ = 'Mattia'


class Url(object):
    def __init__(self, kwargs):
        self.__kwargs = kwargs
    @property
    def kwargs(self):
        return dict(self.__kwargs)
    def __str__(self):
        rv = urllib.urlencode(self.kwargs, True)
        return rv


class PartialUrl(object):
    def __init__(self, url, removed_field):
        self.url = url
        self.removed_field = removed_field
    def __str__(self):
        return str(set_in_url(self, None))


def remove_from_url(url, removed_field):
    # duck typing? no, sir, django must check that I'm giving it a function,
    # thus I can't just "register.filter('remove_from_url', PartialUrl)".
    return PartialUrl(url, removed_field)


def set_in_url(partial_url, field_value):
    kwargs = partial_url.url.kwargs
    if field_value is None:
        if partial_url.removed_field in kwargs:
            del kwargs[partial_url.removed_field]
    else:
        kwargs[partial_url.removed_field] = field_value
    url = Url(kwargs)
    return url


def index(obj, index):
    rv = obj[index]
    return rv


def attr(obj, attrname):
    rv = getattr(obj, attrname)
    return rv


def wikilink(name):
    return 'http://wiki.guildwars2.com/wiki/%s' % name.replace(' ', '_')


def default_if_none(value, default):
    return value if value is not None else default


class Filters(Extension):
    def __init__(self, environment):
        environment.filters["remove_from_url"] = remove_from_url
        environment.filters["set_in_url"] = set_in_url
        environment.filters["index"] = index
        environment.filters["attr"] = attr
        environment.filters["wikilink"] = wikilink
        environment.filters["default_if_none"] = default_if_none