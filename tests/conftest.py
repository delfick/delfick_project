import os
import shutil
import tempfile

import pytest


@pytest.fixture()
def temp_file():
    fle = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fle:
            filename = fle.name
        yield filename
    finally:
        if fle and os.path.exists(fle.name):
            os.remove(fle.name)


@pytest.fixture()
def removed_temp_file(temp_file):
    os.remove(temp_file)
    return temp_file


@pytest.fixture()
def temp_dir():
    d = None
    try:
        d = tempfile.mkdtemp()
        yield d
    finally:
        if d and os.path.exists(d):
            shutil.rmtree(d)


@pytest.fixture()
def removed_temp_dir(temp_dir):
    shutil.rmtree(temp_dir)
    return temp_dir
