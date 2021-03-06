# This is a special file imported by pytest for any test file.
# Fixtures and stuff go here.

import logging
import os
import pytest
import shutil

pytest.register_assert_rewrite('utils')
pytest.register_assert_rewrite('validation')

shutil.rmtree('logs', ignore_errors=True)
os.mkdir('logs')
logging.basicConfig(filename='logs/python-logging', level=logging.DEBUG)


@pytest.fixture
def log_dir(request):
    """ Fixture directory for storing arbitrary test logs. """
    path = os.path.join(
        'logs',
        request.module.__name__,
        request.node.name.replace('/', '_')
    )
    os.makedirs(path)
    return path
