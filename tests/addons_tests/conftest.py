import importlib
import os
import site

from _venvstarter.questions import determine_if_needs_installation

addons_tests = os.path.dirname(__file__)


locations = []
for name in os.listdir(addons_tests):
    location = os.path.join(addons_tests, name)
    if not name.startswith("_") and not name.startswith(".") and os.path.isdir(location):
        try:
            determine_if_needs_installation([name], [], "23.2")
        except SystemExit:
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
