# coding: spec

from layerz import Layers

from noseOfYeti.tokeniser.support import noy_sup_setUp, noy_sup_tearDown
from delfick_error import DelfickErrorTestMixin
from unittest import TestCase, mock
from itertools import zip_longest


class TestCase(TestCase, DelfickErrorTestMixin):
    pass


describe TestCase, "Layers":
    before_each:
        self.dep1 = mock.Mock(name="dep1")
        self.dep2 = mock.Mock(name="dep2")
        self.dep3 = mock.Mock(name="dep3")
        self.deps = {"dep1": self.dep1, "dep2": self.dep2, "dep3": self.dep3}
        self.instance = Layers(self.deps)

    def assertCallsSame(self, mock, expected):
        print("Printing calls as <done> || <expected>")
        print("----")

        call_list = mock.call_args_list
        for did, wanted in zip_longest(call_list, expected):
            print("     {0} || {1}".format(did, wanted))
            print("--")

        self.assertEqual(len(call_list), len(expected))
        mock.assert_has_calls(expected)

    it "takes a list of deps":
        deps = mock.Mock(name="deps")
        layers = Layers(deps)
        self.assertIs(layers.deps, deps)

    it "sets all deps to the deps it received if not given one otherwise":
        deps = mock.Mock(name="deps")
        layers = Layers(deps)
        self.assertIs(layers.all_deps, deps)

    it "takes a dictionary for all the deps":
        deps = mock.Mock(name="deps")
        all_deps = mock.Mock(name="all_deps")
        layers = Layers(deps, all_deps=all_deps)
        self.assertIs(layers.deps, deps)
        self.assertIs(layers.all_deps, all_deps)

    describe "Resetting the instance":
        it "resets layered to an empty list":
            self.instance._layered = mock.Mock(name="layered")
            self.instance.reset()
            self.assertEqual(self.instance._layered, [])

        it "resets accounted to an empty dict":
            self.instance.accounted = mock.Mock(name="accounted")
            self.instance.reset()
            self.assertEqual(self.instance.accounted, {})

    describe "Getting layered":
        it "has a property for converting _layered into a list of list of tuples":
            self.instance._layered = [["one"], ["two", "three"], ["four"]]
            self.instance.deps = ["one", "two", "three", "four"]
            self.instance.all_deps = {"one": 1, "two": 2, "three": 3, "four": 4}
            self.assertEqual(
                self.instance.layered, [[("one", 1)], [("two", 2), ("three", 3)], [("four", 4)]]
            )

    describe "Adding layers":
        before_each:
            self.all_deps = {}
            for i in range(1, 10):
                name = "dep{0}".format(i)
                obj = mock.Mock(name=name)
                obj.dependencies = lambda a: []
                setattr(self, name, obj)
                self.all_deps[name] = obj
            self.deps = self.all_deps.keys()
            self.instance = Layers(self.deps, self.all_deps)

        def assertLayeredSame(self, layers, expected):
            if not layers.layered:
                layers.add_all_to_layers()
            created = layers.layered

            print("Printing expected and created as each layer on a new line.")
            print("    the line starting with || is the expected")
            print("    the line starting with >> is the created")
            print("----")

            for expcted, crted in zip_longest(expected, created):
                print("    || {0}".format(sorted(expcted) if expcted else None))
                print("    >> {0}".format(sorted(crted) if crted else None))
                print("--")

            error_msg = "Expected created layered to have {0} layers. Only has {1}".format(
                len(expected), len(created)
            )
            self.assertEqual(len(created), len(expected), error_msg)

            for index, layer in enumerate(created):
                nxt = expected[index]
                self.assertEqual(sorted(layer) if layer else None, sorted(nxt) if nxt else None)

        it "has a method for adding all the deps":
            add_to_layers = mock.Mock(name="add_to_layers")
            with mock.patch.object(self.instance, "add_to_layers", add_to_layers):
                self.instance.add_all_to_layers()
            self.assertCallsSame(add_to_layers, sorted([mock.call(dep) for dep in self.deps]))

        it "does nothing if the dep is already in accounted":
            self.assertEqual(self.instance._layered, [])
            self.instance.accounted["dep1"] = True

            self.dep1.dependencies = []
            self.instance.add_to_layers("dep1")
            self.assertEqual(self.instance._layered, [])
            self.assertEqual(self.instance.accounted, {"dep1": True})

        it "adds dep to accounted if not already there":
            self.assertEqual(self.instance._layered, [])
            self.assertEqual(self.instance.accounted, {})

            self.dep1.dependencies = lambda a: []
            self.instance.add_to_layers("dep1")
            self.assertEqual(self.instance._layered, [["dep1"]])
            self.assertEqual(self.instance.accounted, {"dep1": True})

        it "complains about cyclic dependencies":
            self.dep1.dependencies = lambda a: ["dep2"]
            self.dep2.dependencies = lambda a: ["dep1"]

            with self.fuzzyAssertRaisesError(Layers.DepCycle, chain=["dep1", "dep2", "dep1"]):
                self.instance.add_to_layers("dep1")

            self.instance.reset()
            with self.fuzzyAssertRaisesError(Layers.DepCycle, chain=["dep2", "dep1", "dep2"]):
                self.instance.add_to_layers("dep2")

        describe "Dependencies":
            before_each:
                self.fake_add_to_layers = mock.Mock(name="add_to_layers")
                original = self.instance.add_to_layers
                self.fake_add_to_layers.side_effect = lambda *args, **kwargs: original(
                    *args, **kwargs
                )
                self.patcher = mock.patch.object(
                    self.instance, "add_to_layers", self.fake_add_to_layers
                )
                self.patcher.start()

            after_each:
                self.patcher.stop()

            describe "Simple dependencies":
                it "adds all deps to the first layer if they don't have dependencies":
                    self.assertLayeredSame(self.instance, [self.all_deps.items()])

                it "adds dep after it's dependency if one is specified":
                    self.dep3.dependencies = lambda a: ["dep1"]
                    cpy = dict(self.all_deps.items())
                    del cpy["dep3"]
                    expected = [cpy.items(), [("dep3", self.dep3)]]
                    self.assertLayeredSame(self.instance, expected)

                it "works with deps sharing the same dependency":
                    self.dep3.dependencies = lambda a: ["dep1"]
                    self.dep4.dependencies = lambda a: ["dep1"]
                    self.dep5.dependencies = lambda a: ["dep1"]

                    cpy = dict(self.all_deps.items())
                    del cpy["dep3"]
                    del cpy["dep4"]
                    del cpy["dep5"]
                    expected = [
                        cpy.items(),
                        [("dep3", self.dep3), ("dep4", self.dep4), ("dep5", self.dep5)],
                    ]
                    self.assertLayeredSame(self.instance, expected)

            describe "Complex dependencies":

                it "works with more than one level of dependency":
                    self.dep3.dependencies = lambda a: ["dep1"]
                    self.dep4.dependencies = lambda a: ["dep1"]
                    self.dep5.dependencies = lambda a: ["dep1"]
                    self.dep9.dependencies = lambda a: ["dep4"]

                    #      9
                    #      |
                    # 3    4    5
                    # \    |    |
                    #  \   |   /
                    #   \  |  /
                    #    --1--         2     6     7     8

                    expected_calls = [
                        mock.call("dep1"),
                        mock.call("dep2"),
                        mock.call("dep3"),
                        mock.call("dep1", ["dep3"]),
                        mock.call("dep4"),
                        mock.call("dep1", ["dep4"]),
                        mock.call("dep5"),
                        mock.call("dep1", ["dep5"]),
                        mock.call("dep6"),
                        mock.call("dep7"),
                        mock.call("dep8"),
                        mock.call("dep9"),
                        mock.call("dep4", ["dep9"]),
                    ]

                    expected = [
                        [
                            ("dep1", self.dep1),
                            ("dep2", self.dep2),
                            ("dep6", self.dep6),
                            ("dep7", self.dep7),
                            ("dep8", self.dep8),
                        ],
                        [("dep3", self.dep3), ("dep4", self.dep4), ("dep5", self.dep5)],
                        [("dep9", self.dep9)],
                    ]

                    self.instance.add_all_to_layers()
                    self.assertCallsSame(self.fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(self.instance, expected)

                it "handles more complex dependencies":
                    self.dep1.dependencies = lambda a: ["dep2"]
                    self.dep2.dependencies = lambda a: ["dep3", "dep4"]
                    self.dep4.dependencies = lambda a: ["dep5"]
                    self.dep6.dependencies = lambda a: ["dep9"]
                    self.dep7.dependencies = lambda a: ["dep6"]
                    self.dep9.dependencies = lambda a: ["dep4", "dep8"]

                    #                     7
                    #                     |
                    #     1               6
                    #     |               |
                    #     2               9
                    #   /   \          /     \
                    # /       4   ----        |
                    # |       |               |
                    # 3       5               8

                    expected_calls = [
                        mock.call("dep1"),
                        mock.call("dep2", ["dep1"]),
                        mock.call("dep3", ["dep1", "dep2"]),
                        mock.call("dep4", ["dep1", "dep2"]),
                        mock.call("dep5", ["dep1", "dep2", "dep4"]),
                        mock.call("dep2"),
                        mock.call("dep3"),
                        mock.call("dep4"),
                        mock.call("dep5"),
                        mock.call("dep6"),
                        mock.call("dep9", ["dep6"]),
                        mock.call("dep4", ["dep6", "dep9"]),
                        mock.call("dep8", ["dep6", "dep9"]),
                        mock.call("dep7"),
                        mock.call("dep6", ["dep7"]),
                        mock.call("dep8"),
                        mock.call("dep9"),
                    ]

                    expected = [
                        [("dep3", self.dep3), ("dep5", self.dep5), ("dep8", self.dep8)],
                        [("dep4", self.dep4)],
                        [("dep2", self.dep2), ("dep9", self.dep9)],
                        [("dep1", self.dep1), ("dep6", self.dep6)],
                        [("dep7", self.dep7)],
                    ]

                    self.instance.add_all_to_layers()
                    self.assertCallsSame(self.fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(self.instance, expected)

                it "only gets layers for the deps specified":
                    self.dep1.dependencies = lambda a: ["dep2"]
                    self.dep2.dependencies = lambda a: ["dep3", "dep4"]
                    self.dep4.dependencies = lambda a: ["dep5"]
                    self.dep6.dependencies = lambda a: ["dep9"]
                    self.dep7.dependencies = lambda a: ["dep6"]
                    self.dep9.dependencies = lambda a: ["dep4", "dep8"]

                    #                     7
                    #                     |
                    #     1               6
                    #     |               |
                    #     2               9
                    #   /   \          /     \
                    # /       4   ----        |
                    # |       |               |
                    # 3       5               8

                    # Only care about 3, 4 and 6
                    # So should only get layers for
                    #
                    #                     6
                    #                     |
                    #                     9
                    #                  /     \
                    #         4   ----        |
                    #         |               |
                    # 3       5               8

                    expected_calls = [
                        mock.call("dep3"),
                        mock.call("dep4"),
                        mock.call("dep5", ["dep4"]),
                        mock.call("dep6"),
                        mock.call("dep9", ["dep6"]),
                        mock.call("dep4", ["dep6", "dep9"]),
                        mock.call("dep8", ["dep6", "dep9"]),
                    ]

                    expected = [
                        [("dep3", self.dep3), ("dep5", self.dep5), ("dep8", self.dep8)],
                        [("dep4", self.dep4)],
                        [("dep9", self.dep9)],
                        [("dep6", self.dep6)],
                    ]

                    self.instance.deps = ["dep3", "dep4", "dep6"]
                    self.instance.add_all_to_layers()
                    self.assertCallsSame(self.fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(self.instance, expected)
