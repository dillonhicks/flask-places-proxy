from urllib.parse import urlparse
from enum import Enum

from .util import Scheme

__all__ = [
    'resource_loader',
    'ResourceType',
    'UnsupportedContentSchemeError',
]


class UnsupportedContentSchemeError(Exception):
    pass


class ResourceType(str, Enum):
    image = 'image'


class ResourceLoader(object):
    """Just a class which registers and dispatches callbacks based on the
    scheme found in the url."""

    def __init__(self):
        self.callbacks = {}

    def register_callback(self, scheme, cb):
        self.callbacks[scheme] = cb

    def load(self, rsrc):
        """At minimum rsrc should have a url attribute"""
        
        try:
            if type(rsrc) is str:
                url = urlparse(rsrc)
            else:
                url = urlparse(rsrc.url)

            scheme = Scheme(url.scheme)
        except (KeyError, AttributeError) as e:
            raise UnsupportedContentSchemeError() from e

        return self.callbacks[scheme](url)

#: "Singleton" instance against which we will register callbacks for
#: schemes to load datatypes.
resource_loader = ResourceLoader()
