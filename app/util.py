from urllib.parse import ParseResult, urlparse
from enum import Enum
import functools

from flask import jsonify

__all__ = [
    'URL',
    'Scheme',
    'MediaType',
    'MimeType',
    'Header',
    'generic_response',
    'ident',
    'filterdict'
]


@functools.lru_cache(16)
def generic_response(status_code):
    return jsonify(meta=dict(status_code=status_code))


def ident(x):
    """identity function f(x) -> x"""
    return x


def filterdict(d, func=ident):
    """Create a copy of dict d by filtering values based on func"""
    return {k: v for k, v in d.items() if func(v)}


class URL(ParseResult):
    def __new__(cls, scheme='', netloc='', path='', params='', query='', fragment=''):
        return super(URL, cls).__new__(cls, scheme, netloc, path, params, query, fragment)

    @staticmethod
    def parse(url):
        if not isinstance(url, str):
            raise TypeError('Cannot parse non string {}'.format(type(url)))

        return URL(**urlparse(url))


class Scheme(str, Enum):
    http = 'http'

    #: google places photo manager
    app_cache = 'app+cache'


class MediaType(str, Enum):
    application = 'application'
    audio = 'audio'
    image = 'image'
    music = 'music'
    text = 'text'
    video = 'video'


class MimeType(str, Enum):

    def __new__(cls, media_type, subtype):
        value = media_type.value + '/' + subtype
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.media_type = media_type
        obj.subtype = subtype
        return obj

    jpeg = (MediaType.image, 'jpeg')


class Header(str, Enum):
    content_length = 'Content-Length'
