import importlib
import runpy
import site
import os

addons_tests = os.path.dirname(__file__)


def needs_installation(location):
    name = os.path.basename(location)
    l = os.path.join(location, name, "__init__.py")
    if not os.path.exists(l):
        raise Exception(f"Failed to find __init__.py for {name}")
    version = runpy.run_path(l)["VERSION"]

    try:
        pkg = __import__(name)
        if pkg.VERSION != version:
            print(f"expected {name} VERSION to be {version}, got {pkg.VERSION}")
            pkg = None
    except ImportError:
        print(f"Could not import {name}")
        pkg = None

    return pkg is None


locations = []
for name in os.listdir(addons_tests):
    location = os.path.join(addons_tests, name)
    if not name.startswith("_") and not name.startswith(".") and os.path.isdir(location):
        if needs_installation(location):
            locations.append(location)

if locations:
    import pip._internal

    pip._internal.main(["install", "-e", *locations])

    importlib.reload(site)
