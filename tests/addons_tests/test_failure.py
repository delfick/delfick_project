# coding: spec

from option_merge_addons import AddonGetter, Register, Addon, ProgrammerError

from tests.helpers import TestCase
from tests import global_register

from noseOfYeti.tokeniser.support import noy_sup_setUp
import layerz
import mock
import sys

def expected_import_error(module):
    if sys.version_info[0] == 2:
        return 'No module named {0}'.format(module)
    else:
        return "No module named '{0}'".format(module)

describe TestCase, "Failure":
    before_each:
        self.getter = AddonGetter()
        self.collector = mock.Mock(name="collector")
        self.collector.configuration = {"resolved": []}
        self.getter.add_namespace("failure.addons")

    it 'complains if the addon is unimportable':
        error = AddonGetter.BadImport("Error whilst resolving entry_point", error=expected_import_error('wasdf'), importing="failure.addons.unimportable", module="namespace_failure.unimportable")
        with self.fuzzyAssertRaisesError(AddonGetter.BadImport, "Failed to import some entry points", _errors=[error]):
            self.getter("failure.addons", "unimportable", self.collector)

    it "complains if the addon recursively includes itself via another plugin at import time":
        self.collector.configuration = {"resolved": []}
        register = Register(self.getter, self.collector)
        with self.fuzzyAssertRaisesError(layerz.DepCycle, chain=[('failure.addons', 'recursive1'), ('failure.addons', 'recursive2'), ('failure.addons', 'recursive1')]):
            register.register(("failure.addons", "recursive1"))

    it "complains if the addon recursively includes itself via another plugin at resolve time":
        self.collector.configuration = {"resolved": []}
        register = Register(self.getter, self.collector)
        with self.fuzzyAssertRaisesError(layerz.DepCycle, chain=[('failure.addons', 'recursive1_extra'), ('failure.addons', 'recursive2_extra'), ('failure.addons', 'recursive1_extra')]):
            register.register(("failure.addons", "recursive1_extra"))

    it "complains if the hook doesn't work":
        self.collector.configuration = {"resolved": []}
        register = Register(self.getter, self.collector)
        register.add_pairs(("failure.addons", "bad_hook"))
        register.recursive_import_known()
        error = Addon.BadHook("Failed to resolve a hook", error=expected_import_error('wasdf'), name="bad_hook", namespace="failure.addons")
        with self.fuzzyAssertRaisesError(Addon.BadHook, _errors=[error]):
            register.recursive_resolve_imported()

    it "Only logs a warning if namespace isn't registered":
        fake_log = mock.Mock(name="fake_log")
        with mock.patch("option_merge_addons.log", fake_log):
            Register(self.getter, self.collector).register(("nonexistent", "blah"))
        fake_log.warning.assert_called_once_with('Unknown plugin namespace\tnamespace=%s\tentry_point=%s\tavailable=%s', 'nonexistent', 'blah', sorted(['option_merge.addons', 'failure.addons']))

    it "complains if it can't import an addon from a known namespace":
        register = Register(self.getter, self.collector)
        with self.fuzzyAssertRaisesError(AddonGetter.NoSuchAddon, addon="failure.addons.nonexistent"):
            register.register(("failure.addons", "nonexistent"))

    it "doesn't complain if the addon has no hook":
        register = Register(self.getter, self.collector)
        register.add_pairs(("failure.addons", "nohook"))
        self.assertEqual(global_register["nohook_found"], False)
        register.recursive_import_known()
        self.assertEqual(global_register["nohook_found"], True)

    it "doesn't complain if the hook doesn't have a result":
        self.assertEqual(self.collector.configuration['resolved'], [])
        Register(self.getter, self.collector).register(("failure.addons", "noresult"))
        self.assertEqual(self.collector.configuration['resolved'], [("namespace_failure.noresult", )])

    it "complains if you try to make extra with a post_register hook":
        with self.fuzzyAssertRaisesError(ProgrammerError, "Sorry, can't specify ``extras`` and ``post_register`` at the same time"):
            Register(self.getter, self.collector).register(("failure.addons", "postregister_and_extras"))


