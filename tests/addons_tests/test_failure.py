# coding: spec

from delfick_project.addons import AddonGetter, Register, Addon

from delfick_project.errors_pytest import assertRaises
from delfick_project.errors import ProgrammerError
from delfick_project.layerz import DepCycle

from unittest import mock
import pytest
import sys


@pytest.fixture()
def global_register():
    from addons_tests_register import global_register

    return global_register


def expected_import_error(module):
    if sys.version_info[0] == 2:
        return "No module named {0}".format(module)
    else:
        return "No module named '{0}'".format(module)


describe "Failure":

    @pytest.fixture()
    def getter(self):
        getter = AddonGetter()
        getter.add_namespace("failure.addons")
        return getter

    @pytest.fixture()
    def collector(self):
        collector = mock.Mock(name="collector")
        collector.configuration = {"resolved": []}
        return collector

    it "complains if the addon is unimportable", getter, collector:
        error = AddonGetter.BadImport(
            "Error whilst resolving entry_point",
            error=expected_import_error("wasdf"),
            importing="failure.addons.unimportable",
            module="namespace_failure.unimportable",
        )
        with assertRaises(
            AddonGetter.BadImport, "Failed to import some entry points", _errors=[error]
        ):
            getter("failure.addons", "unimportable", collector)

    it "complains if the addon recursively includes itself via another plugin at import time", getter, collector:
        collector.configuration = {"resolved": []}
        register = Register(getter, collector)
        with assertRaises(
            DepCycle,
            chain=[
                ("failure.addons", "recursive1"),
                ("failure.addons", "recursive2"),
                ("failure.addons", "recursive1"),
            ],
        ):
            register.register(("failure.addons", "recursive1"))

    it "complains if the addon recursively includes itself via another plugin at resolve time", getter, collector:
        collector.configuration = {"resolved": []}
        register = Register(getter, collector)
        with assertRaises(
            DepCycle,
            chain=[
                ("failure.addons", "recursive1_extra"),
                ("failure.addons", "recursive2_extra"),
                ("failure.addons", "recursive1_extra"),
            ],
        ):
            register.register(("failure.addons", "recursive1_extra"))

    it "complains if the hook doesn't work", getter, collector:
        collector.configuration = {"resolved": []}
        register = Register(getter, collector)
        register.add_pairs(("failure.addons", "bad_hook"))
        register.recursive_import_known()
        error = Addon.BadHook(
            "Failed to resolve a hook",
            error=expected_import_error("wasdf"),
            name="bad_hook",
            namespace="failure.addons",
        )
        with assertRaises(Addon.BadHook, _errors=[error]):
            register.recursive_resolve_imported()

    it "Only logs a warning if namespace isn't registered", getter, collector:
        fake_log = mock.Mock(name="fake_log")
        with mock.patch("delfick_project.addons.log", fake_log):
            Register(getter, collector).register(("nonexistent", "blah"))
        fake_log.warning.assert_called_once_with(
            "Unknown plugin namespace\tnamespace=%s\tentry_point=%s\tavailable=%s",
            "nonexistent",
            "blah",
            sorted(["delfick_project.addons", "failure.addons"]),
        )

    it "complains if it can't import an addon from a known namespace", getter, collector:
        register = Register(getter, collector)
        with assertRaises(AddonGetter.NoSuchAddon, addon="failure.addons.nonexistent"):
            register.register(("failure.addons", "nonexistent"))

    it "doesn't complain if the addon has no hook", getter, collector, global_register:
        register = Register(getter, collector)
        register.add_pairs(("failure.addons", "nohook"))
        assert global_register["nohook_found"] == False
        register.recursive_import_known()
        assert global_register["nohook_found"] == True

    it "doesn't complain if the hook doesn't have a result", getter, collector:
        assert collector.configuration["resolved"] == []
        Register(getter, collector).register(("failure.addons", "noresult"))
        assert collector.configuration["resolved"] == [("namespace_failure.noresult",)]

    it "complains if you try to make extra with a post_register hook", getter, collector:
        with assertRaises(
            ProgrammerError,
            "Sorry, can't specify ``extras`` and ``post_register`` at the same time",
        ):
            Register(getter, collector).register(("failure.addons", "postregister_and_extras"))
