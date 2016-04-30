import concurrent.futures
import logging
import sys
from datetime import timedelta
from enum import Enum
from functools import partial
from urllib.parse import urlunparse

from geopy.distance import great_circle
from rekt_googlecore.client import paginate_responses
from rekt_googlecore.errors import InvalidRequestError, ZeroResultsError

from .photo import PHOTO_MAX_WIDTH
from .util import URL, Scheme

LOG = logging.getLogger(__name__)
SEARCH_LIMIT = 10
DEFAULT_PHOTO_URL = None #https://s3.amazonaws.com/###-multimedia-artifact-repo/generic.jpg'
PHOTO_CACHE_ENTRY_EXPIRE_SECS = timedelta(days=7).seconds


def _sort_alphabetically(v):
    return v['name'].lower()


def _sort_by_distance(location, v):
    try:
        lat = v['latitude']
        lon = v['longitude']
        destination = (lat, lon)
    except KeyError:
        # we do not know how far away so make it the maximum distance away
        return sys.maxsize

    distance = int(great_circle(location, destination).meters)
    LOG.debug('Location: {} Venue: {} - {} Distance: {}m'.format(location, v['name'], destination, distance))
    return distance


class VenueSort(Enum):
    """Standard response sorting types"""
    def __new__(cls, value, sorter):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.sorter = sorter
        return obj

    alphabetic = ('alphabetic', _sort_alphabetically)
    distance = ('distance', _sort_by_distance)


def generate_results(call, max_results=SEARCH_LIMIT):

    responses = paginate_responses(call)
    result_count = 0
    for response in responses:
        LOG.debug('Google Places results - results_count: {}'.format(len(response.results)))

        for result in response.results:
            result_count += 1
            yield result

            if result_count >= max_results:
                return


def format_location(lat, lon):
    return '{},{}'.format(lat, lon)


def add_details_to_place(place, details_by_place_id):
    """
    Add details to a place response given the dictionary of details keyed by the place ids
    """
    try:
        place.update(details_by_place_id[place.place_id])
    except KeyError:
        LOG.exception('Error retrieving google places details for {}'.format(place.place_id))
    return place


def place_to_venue_response(place):
    venue_data = {
        'name': place.get('name', ''),
        'uuid': place.get('place_id', ''),
        'address': place.get('formatted_address', None),
        'latitude': place.get('geometry', {}).get('location', {}).get('lat', None),
        'longitude': place.get('geometry', {}).get('location', {}).get('lng', None),
        'website': place.get('website', ''),
        'phone_number': place.get('phone_number', None),
        'hours': place.get('opening_hours', {}),
        'open_now': place.get('opening_hours', {}).get('open_now', None),
        'photos': place.get('photos', []),
    }

    return venue_data


class SearchEngine(object):
    """The Places Search Engine"""

    def __init__(self, hostname, port, loc, googleplaces, cache):
        self.hostname = hostname
        self.port = port
        self.loc = loc
        self.googleplaces = googleplaces
        self.cache = cache

    def photo_url_for_venue(self, venue, default_url=None):

        photo_url_key = venue['uuid']
        photo_url = self.cache.get(photo_url_key)

        if photo_url:
            return photo_url

        photo_url = None
        photos = venue.get('photos', [])
        photos = [p for p in photos if p.get('width', 0) >= PHOTO_MAX_WIDTH]

        for photo in photos:

            photo_ref = photo.get('photo_reference', None)

            if photo_ref:
                photo_url = urlunparse(URL(
                    scheme=Scheme.http,
                    netloc='{}:{}'.format(self.hostname, self.port),
                    path=self.loc + '/photo',
                    query='uuid=' + photo_ref)
                )

        if photo_url:
            self.cache.set(photo_url_key, photo_url)
            self.cache.expire(photo_url_key, PHOTO_CACHE_ENTRY_EXPIRE_SECS)

        elif default_url is not None:
            photo_url = default_url
        else:
            photo_url = DEFAULT_PHOTO_URL

        return photo_url

    def _get_places(self, latitude, longitude, radius, max_results):
        """Manage getting the aggregated places based on geographic search criteria"""

        get_places_call = partial(self.googleplaces.get_places,
                                  location=format_location(latitude, longitude),
                                  radius=radius)

        places = []

        try:
            for place in generate_results(get_places_call, max_results):
                places.append(place)

        except InvalidRequestError as e:
            # Generally this means the token did not become valid
            # quickly enough.
            LOG.exception("Invalid request, possibly the token is not yet active?")
        except ZeroResultsError as e:
            # Sometimes it happens and in this case there isn't much
            # we can do about it.
            LOG.exception("No Results for search")

        return places

    def _get_details_for_places(self, places):
        """
        """

        details_by_place_id = {}
        futures = []

        for place in places:
            future = self.googleplaces.async_get_details(placeid=place.place_id)
            futures.append(future)

        for details_response in concurrent.futures.as_completed(futures):
            if details_response.exception() is not None:
                LOG.error('Exception in getting details. exception: {}'.format(details_response.exception()))
                continue

            details = details_response.result().result
            details_by_place_id[details.place_id] = details

        return details_by_place_id

    def _new_venues_with_details(self, places_missing_details):

        details_by_place_id = self._get_details_for_places(places_missing_details)

        # Curry some functions to make comprehensions more clear
        add_details_to = partial(add_details_to_place, details_by_place_id=details_by_place_id)
        places_with_details = [add_details_to(place) for place in places_missing_details]
        new_venues = [place_to_venue_response(place) for place in places_with_details]

        return new_venues

    def _places_to_response_venues(self, places_by_uuid):

        details_by_place_id = {}
        futures = []

        for uuid, place in places_by_uuid.items():
            # Use the async call functionality on the Rekt GooglePlacesClient
            # to fetch all of the details in parallel.
            future = self.googleplaces.async_get_details(placeid=uuid)
            futures.append(future)

        for details_response in concurrent.futures.as_completed(futures):
            if details_response.exception() is not None:
                LOG.error('Exception in getting details. exception: {}'.format(details_response.exception()))
                continue

            details = details_response.result().result
            details_by_place_id[details.place_id] = details

        add_details_to = partial(add_details_to_place, details_by_place_id=details_by_place_id)
        places_with_details = [add_details_to(place) for place in places_by_uuid.values()]
        new_venues = [place_to_venue_response(place) for place in places_with_details]

        photo_url_for = partial(self.photo_url_for_venue, default_url=DEFAULT_PHOTO_URL)

        for venue in new_venues:
            venue.update({'photo_url' : photo_url_for(venue) })

        return new_venues

    @staticmethod
    def _get_sorter(latitude, longitude, sort_by):
        sort_type = VenueSort[sort_by]

        if sort_type == VenueSort.distance:
            sorter = partial(sort_type.sorter, (latitude, longitude))
        else:
            sorter = sort_type.sorter

        return sorter

    def search(self, latitude, longitude, radius, sort_by='distance'):
        """Search by distance, no name"""

        places = self._get_places(latitude, longitude, radius, max_results=SEARCH_LIMIT)
        places_by_uuid = {p.place_id: p for p in places}

        venues = self._places_to_response_venues(places_by_uuid)

        sorter = self._get_sorter(latitude, longitude, sort_by)
        response_venues = sorted(venues, key=sorter)[:SEARCH_LIMIT]

        return response_venues

