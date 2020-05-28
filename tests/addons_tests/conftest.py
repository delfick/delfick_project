import pkg_resources
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
        try:
            pkg_resources.working_set.require("{0}=={1}".format(name, version))
        except pkg_resources.VersionConflict:
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

    if hasattr(pip._internal, "main"):
        _main = pip._internal.main
    else:
        from pip._internal.main import main as _main

    args = ["install", "-e"]
    args.extend(locations)
    _main(args)

    importlib.reload(site)
    importlib.reload(pkg_resources)
