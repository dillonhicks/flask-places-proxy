import logging
import os
import sys
from os import path

from flask import (Flask)

from . import config as app_config
from .util import generic_response

__version__ = '1.0'
__all__ = ['create_application']

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def create(root_path, config_name):
    """
    Initialize app object that represents the app,
    requisite extensions, and application modules.
    """

    app = Flask(__name__)
    config = app_config.for_context(config_name)

    app.config.update(config)
    app.config['BASE_DIR'] = root_path
    app.config['CONFIG_NAME'] = config_name
    initialize_logging(app)

    with app.app_context():
        register_application_modules(app)
        register_error_handlers(app)

    return app


def initialize_logging(app):

    loggers = [logging.getLogger(name) for name in ('app', 'rekt')]
    for l in loggers: l.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s')

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    for l in loggers: l.addHandler(console_handler)

    LOG.debug('Initialized logging')


def register_error_handlers(app):
    """Global HTTP errorcode handlers"""

    app.error_handler_spec[None][404] = lambda *args, **kwargs: generic_response(404)
    app.error_handler_spec[None][400] = lambda *args, **kwargs: generic_response(400)


def register_application_modules(app):
    """
    Register the requisite application submodules/blueprints with the app.
    """

    from . import api
    api.init(app)

    @app.route('/ping')
    def ping():
        """Health ping for load balancers and to see if server is up"""
        return generic_response(200)

