# coding: spec

from itertools import zip_longest
from unittest import mock

import pytest

from delfick_project.errors_pytest import assertRaises
from delfick_project.layerz import DepCycle, Layers


@pytest.fixture()
def deps():
    dep1 = mock.Mock(name="dep1")
    dep2 = mock.Mock(name="dep2")
    dep3 = mock.Mock(name="dep3")
    return {"dep1": dep1, "dep2": dep2, "dep3": dep3}


@pytest.fixture()
def instance(deps):
    return Layers(deps)


describe "Layers":

    def assertCallsSame(self, mock, expected):
        print("Printing calls as <done> || <expected>")
        print("----")

        call_list = mock.call_args_list
        for did, wanted in zip_longest(call_list, expected):
            print("     {0} || {1}".format(did, wanted))
            print("--")

        assert len(call_list) == len(expected)
        mock.assert_has_calls(expected)

    it "takes a list of deps":
        deps = mock.Mock(name="deps")
        layers = Layers(deps)
        assert layers.deps is deps

    it "sets all deps to the deps it received if not given one otherwise":
        deps = mock.Mock(name="deps")
        layers = Layers(deps)
        assert layers.all_deps is deps

    it "takes a dictionary for all the deps":
        deps = mock.Mock(name="deps")
        all_deps = mock.Mock(name="all_deps")
        layers = Layers(deps, all_deps=all_deps)
        assert layers.deps is deps
        assert layers.all_deps is all_deps

    describe "Resetting the instance":
        it "resets layered to an empty list", instance:
            instance._layered = mock.Mock(name="layered")
            instance.reset()
            assert instance._layered == []

        it "resets accounted to an empty dict", instance:
            instance.accounted = mock.Mock(name="accounted")
            instance.reset()
            assert instance.accounted == {}

    describe "Getting layered":
        it "has a property for converting _layered into a list of list of tuples", instance:
            instance._layered = [["one"], ["two", "three"], ["four"]]
            instance.deps = ["one", "two", "three", "four"]
            instance.all_deps = {"one": 1, "two": 2, "three": 3, "four": 4}
            assert instance.layered == [[("one", 1)], [("two", 2), ("three", 3)], [("four", 4)]]

    describe "Adding layers":

        @pytest.fixture()
        def deps(self):
            deps = {}
            for i in range(1, 10):
                name = "dep{0}".format(i)
                obj = mock.Mock(name=name)
                obj.dependencies = lambda a: []
                deps[name] = obj
            return deps

        @pytest.fixture()
        def instance(self, deps):
            return Layers(list(deps.keys()), deps)

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
            assert len(created) == len(expected), error_msg

            for index, layer in enumerate(created):
                nxt = expected[index]
                if layer is None:
                    assert nxt is None
                else:
                    assert sorted(layer) == sorted(nxt)

        it "has a method for adding all the deps", instance, deps:
            add_to_layers = mock.Mock(name="add_to_layers")
            with mock.patch.object(instance, "add_to_layers", add_to_layers):
                instance.add_all_to_layers()
            self.assertCallsSame(add_to_layers, sorted([mock.call(dep) for dep in deps]))

        it "does nothing if the dep is already in accounted", instance, deps:
            assert instance._layered == []
            instance.accounted["dep1"] = True

            deps["dep1"].dependencies = []
            instance.add_to_layers("dep1")
            assert instance._layered == []
            assert instance.accounted == {"dep1": True}

        it "adds dep to accounted if not already there", instance, deps:
            assert instance._layered == []
            assert instance.accounted == {}

            deps["dep1"].dependencies = lambda a: []
            instance.add_to_layers("dep1")
            assert instance._layered == [["dep1"]]
            assert instance.accounted == {"dep1": True}

        it "complains about cyclic dependencies", instance, deps:
            deps["dep1"].dependencies = lambda a: ["dep2"]
            deps["dep2"].dependencies = lambda a: ["dep1"]

            with assertRaises(DepCycle, chain=["dep1", "dep2", "dep1"]):
                instance.add_to_layers("dep1")

            instance.reset()
            with assertRaises(DepCycle, chain=["dep2", "dep1", "dep2"]):
                instance.add_to_layers("dep2")

        describe "Dependencies":

            @pytest.fixture(autouse=True)
            def fake_add_to_layers(self, instance):
                original = instance.add_to_layers

                def add_to_layers(*args, **kwargs):
                    return original(*args, **kwargs)

                add_to_layers = mock.Mock(name="add_to_layers", side_effect=add_to_layers)

                with mock.patch.object(instance, "add_to_layers", add_to_layers):
                    yield add_to_layers

            describe "Simple dependencies":
                it "adds all deps to the first layer if they don't have dependencies", instance, deps:
                    self.assertLayeredSame(instance, [deps.items()])

                it "adds dep after it's dependency if one is specified", instance, deps:
                    deps["dep3"].dependencies = lambda a: ["dep1"]
                    cpy = dict(deps.items())
                    del cpy["dep3"]
                    expected = [cpy.items(), [("dep3", deps["dep3"])]]
                    self.assertLayeredSame(instance, expected)

                it "works with deps sharing the same dependency", instance, deps:
                    deps["dep3"].dependencies = lambda a: ["dep1"]
                    deps["dep4"].dependencies = lambda a: ["dep1"]
                    deps["dep5"].dependencies = lambda a: ["dep1"]

                    cpy = dict(deps.items())
                    del cpy["dep3"]
                    del cpy["dep4"]
                    del cpy["dep5"]
                    expected = [
                        cpy.items(),
                        [("dep3", deps["dep3"]), ("dep4", deps["dep4"]), ("dep5", deps["dep5"])],
                    ]
                    self.assertLayeredSame(instance, expected)

            describe "Complex dependencies":

                it "works with more than one level of dependency", instance, deps, fake_add_to_layers:
                    deps["dep3"].dependencies = lambda a: ["dep1"]
                    deps["dep4"].dependencies = lambda a: ["dep1"]
                    deps["dep5"].dependencies = lambda a: ["dep1"]
                    deps["dep9"].dependencies = lambda a: ["dep4"]

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
                            ("dep1", deps["dep1"]),
                            ("dep2", deps["dep2"]),
                            ("dep6", deps["dep6"]),
                            ("dep7", deps["dep7"]),
                            ("dep8", deps["dep8"]),
                        ],
                        [("dep3", deps["dep3"]), ("dep4", deps["dep4"]), ("dep5", deps["dep5"])],
                        [("dep9", deps["dep9"])],
                    ]

                    instance.add_all_to_layers()
                    self.assertCallsSame(fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(instance, expected)

                it "handles more complex dependencies", instance, deps, fake_add_to_layers:
                    deps["dep1"].dependencies = lambda a: ["dep2"]
                    deps["dep2"].dependencies = lambda a: ["dep3", "dep4"]
                    deps["dep4"].dependencies = lambda a: ["dep5"]
                    deps["dep6"].dependencies = lambda a: ["dep9"]
                    deps["dep7"].dependencies = lambda a: ["dep6"]
                    deps["dep9"].dependencies = lambda a: ["dep4", "dep8"]

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
                        [("dep3", deps["dep3"]), ("dep5", deps["dep5"]), ("dep8", deps["dep8"])],
                        [("dep4", deps["dep4"])],
                        [("dep2", deps["dep2"]), ("dep9", deps["dep9"])],
                        [("dep1", deps["dep1"]), ("dep6", deps["dep6"])],
                        [("dep7", deps["dep7"])],
                    ]

                    instance.add_all_to_layers()
                    self.assertCallsSame(fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(instance, expected)

                it "only gets layers for the deps specified", instance, deps, fake_add_to_layers:
                    deps["dep1"].dependencies = lambda a: ["dep2"]
                    deps["dep2"].dependencies = lambda a: ["dep3", "dep4"]
                    deps["dep4"].dependencies = lambda a: ["dep5"]
                    deps["dep6"].dependencies = lambda a: ["dep9"]
                    deps["dep7"].dependencies = lambda a: ["dep6"]
                    deps["dep9"].dependencies = lambda a: ["dep4", "dep8"]

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
                        [("dep3", deps["dep3"]), ("dep5", deps["dep5"]), ("dep8", deps["dep8"])],
                        [("dep4", deps["dep4"])],
                        [("dep9", deps["dep9"])],
                        [("dep6", deps["dep6"])],
                    ]

                    instance.deps = ["dep3", "dep4", "dep6"]
                    instance.add_all_to_layers()
                    self.assertCallsSame(fake_add_to_layers, expected_calls)
                    self.assertLayeredSame(instance, expected)
