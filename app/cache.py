import logging
from io import BytesIO
from collections import defaultdict

__all__ = [
    'BufferCacheEntry',
    'BufferStream',
    'MissingCacheEntryError',
]

LOG = logging.getLogger(__name__)
KiB = 2 ** 10


class SimpleCache:
    """In memory cache in place of redis for this example"""

    def __init__(self):
        self._cache = defaultdict(lambda: None)

    def get(self, key):
        return self._cache[key]

    def set(self, key, value):
        self._cache[key] = value

    def expire(self, key, time):
        # Noop for example
        pass

class MissingCacheEntryError(Exception):
    pass


class BufferCacheEntry(object):
    """Primitive that represents a load once managed cache entry"""

    def __init__(self, cache_conn, key, buffer_bytes=None):
        self.cache = cache_conn
        self.key = key
        self.buffer_bytes = buffer_bytes

    def get_buffer(self):
        if self.buffer_bytes is None:
            self.buffer_bytes = self.cache.get(self.key)
            LOG.debug('Retrieved - key: {}'.format(self.key))

        if self.buffer_bytes is None:
            raise MissingCacheEntryError()

        return self.buffer_bytes

    def set_buffer(self):
        if self.buffer_bytes is None:
            raise RuntimeError('Cannot save None buffer')

        LOG.debug('Saving buffer - key: {}; size: {}'.format(self.key, len(self.buffer_bytes)))
        return self.cache.set(self.key, self.buffer_bytes)


class BufferStream(object):
    """Utility class that wraps a byte array in order to chunk n' stream"""

    CHUNK_SIZE = 4 * KiB

    def __init__(self, raw_bytes, chunk_size=CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.buffer_bytes = raw_bytes

    @property
    def bytes(self):
        return self.buffer_bytes

    def stream(self):
        buf = BytesIO(self.buffer_bytes)

        eof = False

        while not eof:
            rv = buf.read(self.chunk_size)
            yield rv

            if len(rv) < self.chunk_size:
                eof = True
