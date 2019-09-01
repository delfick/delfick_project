# coding: spec

from option_merge_addons import Register, option_merge_addon_hook

from noseOfYeti.tokeniser.support import noy_sup_setUp
from tests.helpers import TestCase

import mock

describe TestCase, "Register":
    it "takes in an addon_getter and a collector":
        addon_getter = mock.Mock(name="addon_getter")
        collector = mock.Mock(name="collector")
        register = Register(addon_getter, collector)
        self.assertIs(register.addon_getter, addon_getter)
        self.assertIs(register.collector, collector)

    it "initializes known, imported and resolved":
        register = Register(None, None)
        self.assertEqual(register.known, [])
        self.assertEqual(register.imported, {})
        self.assertEqual(register.resolved, {})

    describe "register":
        it "follows the protocol":
            pair1 = mock.Mock(name="pair1")
            pair2 = mock.Mock(name="pair2")
            kw1 = mock.Mock(name="kw1")
            kw2 = mock.Mock(name="kw2")

            info = {"count": -1, "called": []}
            def called(name):
                def caller(*args, **kwargs):
                    info["count"] += 1
                    info["called"].append((args, kwargs, info["count"], name))
                return caller

            fake_add_pairs = mock.Mock(name="add_pairs", side_effect=called("pairs"))
            fake_recursive_import_known = mock.Mock(name="recursive_import_known", side_effect=called("import_known"))
            fake_recursive_resolve_imported = mock.Mock(name="recursive_resolve_imported", side_effect=called("resolve"))
            fake_post_register = mock.Mock(name="post_register", side_effect=called("post"))

            register = Register(None, None)

            with mock.patch.multiple(register
                , add_pairs = fake_add_pairs
                , recursive_import_known = fake_recursive_import_known
                , recursive_resolve_imported = fake_recursive_resolve_imported
                , post_register = fake_post_register
                ):
                self.assertEqual(info["called"], [])
                register.register(pair1, pair2, kw1=kw1, kw2=kw2)
                print(info["called"])

            self.assertEqual(info["called"]
                , [ ((pair1, pair2), {}, 0, "pairs")
                  , ((), {}, 1, "import_known")
                  , ((), {}, 2, "resolve")
                  , ((dict(kw1=kw1, kw2=kw2), ), {}, 3, "post")
                  ]
                )

    describe "add_pairs":
        it "adds to the known list":
            pair1 = ("namespace1", "name1")
            pair2 = ("namespace1", "name2")
            pair3 = ("namespace2", "name1")
            register = Register(None, None)

            self.assertEqual(register.known, [])
            register.add_pairs(pair1, pair2)
            self.assertEqual(register.known, [pair1, pair2])

            register.add_pairs(pair1)
            self.assertEqual(register.known, [pair1, pair2])

            register.add_pairs(pair3)
            self.assertEqual(register.known, [pair1, pair2, pair3])

        it "treats __all__ as special":
            def all_for(ns):
                self.assertEqual(ns, "namespace1")
                return [("namespace1", "one"), ("namespace1", "two")]
            addon_getter = mock.Mock(name="addon_getter")
            addon_getter.all_for.side_effect = all_for

            register = Register(addon_getter, None)
            register.add_pairs(("namespace1", "__all__"))
            self.assertEqual(sorted(register.known), sorted([("namespace1", "one"), ("namespace1", "two")]))

            # Doesn't duplicate in known
            register = Register(addon_getter, None)
            register.add_pairs(("namespace1", "one"), ("namespace1", "__all__"))
            self.assertEqual(sorted(register.known), sorted([("namespace1", "one"), ("namespace1", "two")]))

    describe "recursive_import_known":
        it "keeps calling _import_known till it says False":
            called = []
            fake_import_known = mock.Mock(name="import_known")
            def _import_known():
                if len(called) == 3:
                    return False
                else:
                    called.append(1)
                    return True
            fake_import_known.side_effect = _import_known

            register = Register(None, None)
            with mock.patch.object(register, "_import_known", fake_import_known):
                self.assertEqual(called, [])
                register.recursive_import_known()

            self.assertEqual(called, [1, 1, 1])

    describe "recursive_resolve_imported":
        it "keeps calling _resolve_imported till it says False":
            called = []
            fake_resolve_imported = mock.Mock(name="resolve_imported")
            def _resolve_imported():
                if len(called) == 3:
                    return False
                else:
                    called.append(1)
                    return True
            fake_resolve_imported.side_effect = _resolve_imported

            register = Register(None, None)
            with mock.patch.object(register, "_resolve_imported", fake_resolve_imported):
                self.assertEqual(called, [])
                register.recursive_resolve_imported()

            self.assertEqual(called, [1, 1, 1])

    describe "post_register":
        it "calls post_register with appropriate extra args for each item in the layers":
            called = []

            rs1 = mock.Mock(name="rs1")
            rs2 = mock.Mock(name="rs2")
            rs3 = mock.Mock(name="rs3")

            rs1.post_register.side_effect = lambda **kwargs: called.append((1, kwargs))
            rs2.post_register.side_effect = lambda **kwargs: called.append((2, kwargs))
            rs3.post_register.side_effect = lambda **kwargs: called.append((3, kwargs))

            layer1 = [(("ns1", 'rs1'), rs1)]
            layer2 = [(("ns2", 'rs2'), rs2), (("ns1", 'rs3'), rs3)]
            layered = [layer1, layer2]

            extra_args = {"ns1": dict(a=1, b=2)}

            register = Register(None, None)
            register.resolved = {('ns1', 'rs1'): rs1, ('ns2', 'rs2'): rs2, ('ns1', 'rs3'): rs3}

            with mock.patch.multiple(register.__class__, layered=layered):
                register.post_register(extra_args)

            self.assertEqual(called, [(1, dict(a=1, b=2)), (2, {}), (3, dict(a=1, b=2))])

    describe "layered":
        it "creates layers from what is currently imported":
            layer1 = mock.Mock(name="layer1")
            layer2 = mock.Mock(name="layer2")
            layersInstance = mock.Mock(name="LayersInstance", layered=[layer1, layer2])
            FakeLayers = mock.Mock(name="Layers", return_value=layersInstance)

            with mock.patch("option_merge_addons.Layers", FakeLayers):
                register = Register(None, None)
                register.imported = {("n1", "n1"): True, ("n1", "n2"): True, ("n2", "n1"): True}
                layered = list(register.layered)

            FakeLayers.assert_called_once_with(register.imported)
            self.assertEqual(layered, [layer1, layer2])
            self.assertEqual(layersInstance.add_to_layers.mock_calls
                , [ mock.call(("n1", "n1"))
                  , mock.call(("n1", "n2"))
                  , mock.call(("n2", "n1"))
                  ]
                )

    describe "_import_known":
        before_each:
            self.collector = mock.Mock(name="collector")
            self.addon_getter = mock.Mock(name="addon_getter")

        it "returns false if everything in known is already in imported":
            register = Register(None, None)
            register.known = [(1, 2), (3, 4)]
            register.imported = {(1, 2): True, (3, 4): True}
            assert not register._import_known()

        it "uses addon_getter on anything not already imported and does nothing with the result":
            register = Register(self.addon_getter, self.collector)
            register.add_pairs((1, 3))
            res = type("result", (object, ), {"extras": [(4, 5)]})()
            self.addon_getter.return_value = res

            self.assertEqual(register.imported, {})
            self.assertEqual(register.known, [(1, 3)])
            assert register._import_known()
            self.addon_getter.assert_called_once_with(1, 3, self.collector, known=[(1, 3)])
            self.addon_getter.reset_mock()
            self.assertEqual(register.imported, {(1, 3): res})
            self.assertEqual(register.known, [(1, 3), (4, 5)])

            # And test it imports what it found
            res2 = type("result2", (object, ), {"extras": []})()
            self.addon_getter.return_value = res2
            assert register._import_known()
            self.addon_getter.assert_called_once_with(4, 5, self.collector, known=[(1, 3), (4, 5)])
            self.assertEqual(register.imported, {(1, 3): res, (4, 5): res2})
            self.assertEqual(register.known, [(1, 3), (4, 5)])

            assert not register._import_known()

    describe "_resolve_imported":
        it "resolves the layers and adds the found pairs":
            i1 = mock.Mock(name="i1")
            i2 = mock.Mock(name="i2")
            i3 = mock.Mock(name="i3")

            r1 = mock.Mock(name="r1", extras=[("one", "two")])
            r2 = mock.Mock(name="r2", extras=[("three", "four"), ("three", "five")])
            r3 = mock.Mock(name="r3", extras=[])

            collector = mock.Mock(name="collector")
            called = []

            i1.resolved = [r1]
            i2.resolved = [r2]
            i3.resolved = [r3]

            i1.process.side_effect = lambda c: called.append(1)
            i2.process.side_effect = lambda c: called.append(2)
            i3.process.side_effect = lambda c: called.append(3)

            register = Register(None, collector)
            register.known = [(1, 3), (1, 2), (2, 4)]
            register.imported = {(1, 3): i1, (1, 2): i2, (2, 4): i3}

            layer1 = [((1, 3), i1)]
            layer2 = [((1, 2), i2), ((2, 4), i3)]
            layered = [layer1, layer2]

            import_known_res = mock.Mock(name="import_known_res")
            fake_recursive_import_known = mock.Mock(name="recursive_import_known")
            def import_known():
                called.append(4)
                return import_known_res
            fake_recursive_import_known.side_effect = import_known

            with mock.patch.multiple(register.__class__, layered=layered, recursive_import_known=fake_recursive_import_known):
                self.assertEqual(called, [])
                self.assertEqual(register.known, [(1, 3), (1, 2), (2, 4)])
                self.assertEqual(register.resolved, {})
                self.assertIs(register._resolve_imported(), import_known_res)

            self.assertEqual(called, [1, 2, 3, 4])
            self.assertEqual(register.known, [(1, 3), (1, 2), (2, 4), ("one", "two"), ("three", "four"), ("three", "five")])
            self.assertEqual(register.imported, {(1, 3): i1, (1, 2): i2, (2, 4): i3})
            self.assertEqual(register.resolved, {(1, 3): [r1], (1, 2): [r2], (2, 4): [r3]})

        it "replaces __all__":
            i1 = mock.Mock(name="i1")

            @option_merge_addon_hook(extras=[("one", "__all__"), ("one", "one"), ("two", "one")])
            def r1(*args, **kwargs):
                pass
            i1.resolved = [r1]

            collector = mock.Mock(name="collector")

            register = Register(None, collector)

            layer1 = [((1, 3), i1)]
            layered = [layer1]

            import_known_res = mock.Mock(name="import_known_res")
            fake_recursive_import_known = mock.Mock(name="recursive_import_known", return_value=import_known_res)

            pairs_from_extra = [("one", "one"), ("one", "three"), ("one", "two")]
            add_pairs_from_extras = mock.Mock(name="add_pairs_from_extras", return_value=pairs_from_extra)

            with mock.patch.multiple(register.__class__
                , layered = layered
                , recursive_import_known = fake_recursive_import_known
                , add_pairs_from_extras = add_pairs_from_extras
                ):
                self.assertIs(register._resolve_imported(), import_known_res)

            self.assertEqual(r1.extras, [("one", ("one", "three", "two")), ("two", ("one", ))])

    describe "add_pairs_from_extra":
        it "combines the pairs":
            register = Register(None, None)
            register.known = [("one", "twenty"), ("six", "seven"), ("three", "five")]
            extra = [("one", "two"), ("three", "four"), ("three", "five")]
            register.add_pairs_from_extras(extra)
            self.assertEqual(register.known, [("one", "twenty"), ("six", "seven"), ("three", "five"), ("one", "two"), ("three", "four")])

        it "returns the pairs that were found":
            register = Register(None, None)
            extra = [("one", "__all__"), ("three", "four"), ("three", "five")]
            added = []
            ret = [[("one", "one"), ("one", "two"), ("one", "three")], [("three", "four")], [("three", "five")]]

            def add_pairs(*pairs):
                self.assertEqual(len(pairs), 1)
                added.append(pairs[0])
                return ret.pop(0)

            add_pairs = mock.Mock(name="add_pair", side_effect=add_pairs)
            with mock.patch.object(register, "add_pairs", add_pairs):
                got = register.add_pairs_from_extras(extra)

            self.assertEqual(got
                , [ ("one", "one")
                  , ("one", "three")
                  , ("one", "two")
                  , ("three", "five")
                  , ("three", "four")
                  ]
                )

            self.assertEqual(added, [("one", "__all__"), ("three", "four"), ("three", "five")])
