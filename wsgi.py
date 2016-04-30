#!/usr/bin/env python
"""
wsgi.py
==============

This file is the wsgi entry point of the webservice code when
running behind a full webstack. For general development usage, refer
to the `manage` script located in the  source repository.
"""
import eventlet
eventlet.monkey_patch()
import sys
from os import path, environ


def main():
    # Ensure that app is on the python module search path
    # by including the directory that holds this file:
    # /some/path/to/app/
    #                 |
    #                 +---> wsgi.py  <- you are here
    #                 +---> app/     <- the goods
    _root_app_path = path.dirname(path.abspath(__file__))
    sys.path.append(_root_app_path)

    _config_name = environ.get('RUNTIME_CONFIG', 'debug')
    print('RUNTIME_CONFIG={}'.format(_config_name))
    import app
    instance = app.create(_root_app_path, _config_name)
    instance.run('0.0.0.0', port=instance.config.get('BIND_PORT'))

if __name__ == '__main__':
    main()
