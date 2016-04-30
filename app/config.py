from pathlib import Path, PurePath

import yaml
from pkg_resources import resource_filename

from .util import filterdict

__all__ = (
    'load',
    'for_context'
)


def load(name, module_name=__name__, paths=None):
    """
    Uses package info magic to find the resource file located in the specs
    submodule.
    """
    if paths is None:
        try:
            paths = __path__
        except NameError:
            paths = [str(Path(__file__).parent)]

    config_path = Path(next(iter(paths)))
    config_path = config_path / PurePath(resource_filename(module_name, name + '.yaml'))

    with config_path.open('rb') as fi:
        file_bytes = fi.read()
        config = yaml.load(file_bytes.decode('utf-8'))

    return config


def for_context(context, filename='defaults'):
    section = load(filename)[context]

    def is_not_none(val):
        return val is not None

    return filterdict(section, is_not_none)
