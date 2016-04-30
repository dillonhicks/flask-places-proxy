import logging

from rekt_googleplaces.errors import GoogleAPIError

from .cache import BufferCacheEntry, BufferStream, MissingCacheEntryError

__all__ = [
    'NoSuchPhotoError',
    'GooglePlacesPhotoManager',
    'PhotoCacheEntry',
    'Photo',
    'GooglePlacesPhotoResourceLoader',
]

LOG = logging.getLogger(__name__)
PHOTO_MAX_WIDTH = 1920


class NoSuchPhotoError(Exception):
    pass


class GooglePlacesPhotoManager(object):
    def __init__(self, googleplaces, cache_conn):
        self.gp = googleplaces
        self.cache = cache_conn

    def retrieve(self, key):
        try:
            photo = self._retrieve_from_cache(key)
            LOG.debug('Retrieved photo from cache - key: {}'.format(key))

        except NoSuchPhotoError as e:
            photo = self._retrieve_from_googleplaces(key)
            if photo is None:
                raise
            LOG.debug('Retrieved photo from google places - key: {}'.format(key))

        return photo

    def _retrieve_from_cache(self, key):
        return PhotoCacheEntry(self.cache, key).photo

    def _retrieve_from_googleplaces(self, key):
        try:
            response = self.gp.get_photo2(photoreference=key, maxwidth=PHOTO_MAX_WIDTH)
        except GoogleAPIError as e:
            LOG.exception('Could not get photo from google place - '
                          'photoreference: {}; exception: {}'.format(key, e))
            return None

        cache_entry = PhotoCacheEntry(self.cache, key, response.content)
        cache_entry.save()
        return cache_entry.photo


class PhotoCacheEntry(BufferCacheEntry):
    def __init__(self, cache_conn, key, buffer_bytes=None):
        BufferCacheEntry.__init__(self, cache_conn, key, buffer_bytes)

    @property
    def photo(self):
        try:
            return Photo(self.get_buffer())
        except MissingCacheEntryError as e:
            raise NoSuchPhotoError() from e

    def save(self):
        return self.set_buffer()


class Photo(BufferStream):
    def __init__(self, raw_bytes):
        BufferStream.__init__(self, raw_bytes)


class GooglePlacesPhotoResourceLoader(object):
    def __init__(self, gppm):
        self.gppm = gppm

    def __call__(self, parsed_url):
        path_parts = parsed_url.path.split('/')
        photo_ref = path_parts[-1]
        return self.gppm.retrieve(photo_ref)
