import logging
from urllib.parse import urlunparse

from flask import abort, Response
from flask.ext import restful
from flask.ext.restful import Resource, marshal_with, reqparse
from flask.ext.restful.fields import String, Boolean, List
from rekt.httputils import HTTPStatus
from rekt_googleplaces import GooglePlacesClient

from .auth import auth_token_required
from .cache import SimpleCache
from .photo import GooglePlacesPhotoManager, GooglePlacesPhotoResourceLoader
from .photo import NoSuchPhotoError
from .resource import resource_loader
from .search import SearchEngine
from .util import MimeType, Header, URL
from .util import Scheme

LOG = logging.getLogger(__name__)

_rest = restful.Api(default_mediatype='application/json')
_ENDPOINT = '/api'


__all__ = (
    'PlacesResource',
    'PhotoResource',
)


class _RestAPIState(object):
    def __init__(self, hostname, port, location, engine, googleplaces, cache):
        self.hostname = hostname
        self.port = port
        self.location = location
        self.engine = engine
        self.googleplaces = googleplaces
        self.cache = cache


def init(app):
    """blueprint factory method that initializes the restapi object
    with the flask app context"""

    #: Weird scoping context that requies the module level attribute
    #: to be locally aliased for reasons I have not fully discovered. My best guess
    #: is that there is some flask thread local context
    #: funkiness.
    rest = _rest

    #: Init the rest service dependencies
    rest.cache = SimpleCache()
    rest.googleplaces = GooglePlacesClient(api_key=app.config['GOOGLE_PLACES_API_KEY'])
    rest.photo_manager = GooglePlacesPhotoManager(rest.googleplaces, rest.cache)
    rest.photo_loader = GooglePlacesPhotoResourceLoader(rest.photo_manager)
    resource_loader.register_callback(Scheme.app_cache, rest.photo_loader)

    rest.hostname = app.config['HOSTNAME']
    rest.port = app.config.get('EXPOSE_PORT', app.config['BIND_PORT'])
    rest.engine = SearchEngine(rest.hostname, rest.port, _ENDPOINT, rest.googleplaces, rest.cache)

    #: Service API Endpoints
    rest.add_resource(PlacesResource, _ENDPOINT + '/place')
    app.add_url_rule(_ENDPOINT + '/photo', view_func=PhotoResource.as_view('venue_photo_api'))
    rest.init_app(app)

    if not hasattr(app, 'extensions'):
        app.extensions = {}

    app.extensions['MyRestService'] = _RestAPIState(rest.hostname, rest.port, _ENDPOINT, rest.engine, rest.googleplaces,
                                                    rest.cache)


class PlacesResource(Resource):
    #: Auth
    method_decorators = [auth_token_required]

    #: Request
    request_model = reqparse.RequestParser()
    request_model.add_argument('latitude', required=True, type=float, location='args')
    request_model.add_argument('longitude', required=True, type=float, location='args')
    request_model.add_argument('search_radius_meters', required=True, type=float, location='args')

    #: Response
    response_model = {
        'name': String,
        'address': String,
        'website': String,
        'open_now': Boolean,
        'phone_number': String,
        'photo_url': String,
        'latitude': String,
        'longitude': String,
    }

    @marshal_with(response_model)
    def get(self, **kwargs):

        #: Throws 400 on missing args
        args = self.request_model.parse_args()
        radius = args.search_radius_meters

        venues = _rest.engine.search(args.latitude, args.longitude, radius)
        LOG.debug('{}'.format(venues))
        return venues


class PhotoResource(Resource):
    #: Auth
    method_decorators = [auth_token_required]

    #: Request
    request_model = reqparse.RequestParser()
    request_model.add_argument('uuid', required=True, type=str, location='args')

    #: Response - just bytes of type image/jpeg

    def get(self):

        #: Throws 400 on missing args
        args = self.request_model.parse_args()
        photo_uuid = args.uuid

        photo = None
        try:
            url = urlunparse(URL(scheme=Scheme.app_cache,  path='/' + photo_uuid))
            photo = resource_loader.load(url)

        except NoSuchPhotoError:
            abort(HTTPStatus.BAD_REQUEST)

        response = Response(photo.stream(), content_type=MimeType.jpeg.value)
        response.headers[Header.content_length.value] = len(photo.bytes)

        return response
