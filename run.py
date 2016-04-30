#!/usr/bin/env python
import sys
from os import path
import timeit

import requests
from flask.ext.script import Manager


root_app_path = path.dirname(path.abspath(__file__))
sys.path.append(root_app_path)

try:
    # manage <config> <cmd> <args>
    _ = sys.argv[2] # Assert that there is a 3rd element
    config_name = sys.argv.pop(1)
except IndexError:
    config_name = 'debug'

import app
instance = app.create(root_app_path, config_name=config_name)

manager = Manager(instance)

@manager.command
def server():
    instance.run(port=instance.config.get('BIND_PORT'))

@manager.command
def example():
    resp = requests.get('http://127.0.0.1:8000/api/place?latitude=47.6&longitude=-122.3&search_radius_meters=1000')
    entries = resp.json()
    print(resp.text)

    photo_url = next(e['photo_url'] for e in entries if e['photo_url'] is not None)
    print('Photo URL:', photo_url)
    code = 'requests.get({})'.format(repr(photo_url))
    print('To test:', code)
    print()

    print('GET 1 (not cached):', end=' ')
    time_1 = timeit.timeit(code, number=1, setup="import requests")
    print(time_1)

    print('GET 2 (cached):', end=' ')
    time_2 = timeit.timeit(code, number=1, setup="import requests")
    print(time_2)

    print('Difference: {:.2f}%'.format(100.0 * (time_1 - time_2) / time_1))


if __name__ == "__main__":
    manager.run()
