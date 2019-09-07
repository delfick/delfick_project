import tempfile
import pytest
import shutil
import os


@pytest.fixture()
def temp_file():
    fle = None
    try:
        fle = tempfile.NamedTemporaryFile(delete=False)
        yield fle.name
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
