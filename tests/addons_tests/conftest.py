import importlib
import runpy
import site
import os

addons_tests = os.path.dirname(__file__)


def needs_installation(location):
    name = os.path.basename(location)
    l = os.path.join(location, name, "__init__.py")
    if not os.path.exists(l):
        raise Exception("Failed to find __init__.py for {0}".format(name))
    version = runpy.run_path(l)["VERSION"]

    try:
        pkg = __import__(name)
        if pkg.VERSION != version:
            print("expected {0} VERSION to be {1}, got {2}".format(name, version, pkg.VERSION))
            pkg = None
    except ImportError:
        print("Could not import {0}".format(name))
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

    args = ["install", "-e"]
    args.extend(locations)
    pip._internal.main(args)

    importlib.reload(site)
