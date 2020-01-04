# coding: spec

from delfick_project.option_merge import Collector, MergedOptions

from delfick_project.errors_pytest import assertRaises
from delfick_project.errors import DelfickError
from delfick_project.norms import sb, Meta

from contextlib import contextmanager
from getpass import getpass
from unittest import mock
import tempfile
import shutil
import json
import os


describe "Collector":

    @contextmanager
    def fake_config(self, body="\n{}"):
        root = None
        try:
            root = tempfile.mkdtemp()
            config_file = os.path.join(root, "config.json")
            with open(config_file, "w") as fle:
                fle.write(body)
            yield (root, config_file)
        finally:
            if root and os.path.exists(root):
                shutil.rmtree(root)

    describe "__init__":
        it "calls setup":
            called = []

            class C(Collector):
                def setup(s):
                    called.append(1)

            assert called == []
            C()
            assert called == [1]

    describe "register_converters":
        it "adds converters":
            configuration = MergedOptions.using({"two": {"three.four": 2}, "three": 3})
            meta = Meta(configuration, [])

            spec1 = mock.Mock(name="spec1")
            spec1.normalise.return_value = "ONE"

            spec2 = mock.Mock(name="spec2")
            spec2.normalise.return_value = "TWO"

            specs = {"one": spec1, ("two", "three.four"): spec2}

            collector = Collector()
            collector.configuration = configuration
            collector.register_converters(specs)
            configuration.converters.activate()

            assert configuration["one"] == "ONE"
            assert configuration["two.three.four"] == "TWO"
            assert configuration["three"] == 3

            spec1.normalise.assert_called_once_with(meta.at("one"), sb.NotSpecified)
            spec2.normalise.assert_called_once_with(meta.at("two").at("three.four"), 2)

    describe "Cloning":
        it "returns an instance that has rerun collect_configuration and prepare":
            called = []
            original_args_dict = {"a": 1, "b": 2}
            with self.fake_config() as (config_root, config_file):

                class Col(Collector):
                    def start_configuration(s):
                        return MergedOptions.using({})

                    def read_file(s, location):
                        return json.load(open(location))

                    def add_configuration(
                        s, configuration, collect_another_source, done, result, src
                    ):
                        configuration.update(result)

                    def alter_clone_args_dict(slf, nw_cllctr, nw_args_dict, new_args):
                        nw_args_dict.update(new_args)
                        called.append((1, nw_cllctr, nw_args_dict))
                        return nw_args_dict

                collector = Col()
                collector.prepare(config_file, original_args_dict)
                assert collector.configuration["args_dict"].as_dict() == original_args_dict

            class MockCollectorKls(Col):
                def prepare(slf, config_file, new_args_dict):
                    called.append((2, (config_file, new_args_dict)))

            collector.__class__ = MockCollectorKls

            clone = collector.clone({"c": 3, "b": 4})
            assert type(clone) is MockCollectorKls
            assert called == [
                (1, clone, {"a": 1, "b": 4, "c": 3}),
                (2, (config_file, {"a": 1, "b": 4, "c": 3})),
            ]
            assert original_args_dict == {"a": 1, "b": 2}

    describe "prepare":
        it "find_missing_config, configuration, does extra_prepare, activates converters and extra_prepare_after_activation":
            called = []
            args_dict = {}
            with self.fake_config('{"one": 1}') as (config_root, config_file):

                class Col(Collector):
                    def start_configuration(s):
                        return MergedOptions.using({})

                    def read_file(s, location):
                        return json.load(open(location))

                    def add_configuration(
                        s, configuration, collect_another_source, done, result, src
                    ):
                        configuration.update(result)

                    def find_missing_config(slf, config):
                        called.append((1, config))
                        assert config.as_dict() == {
                            "config_root": config_root,
                            "one": 1,
                            "getpass": getpass,
                            "collector": slf,
                            "args_dict": args_dict,
                        }
                        config.converters = mock.Mock(name="converters")

                    def extra_prepare(slf, config, args_dict):
                        called.append((2, config, args_dict))
                        assert config.as_dict() == {
                            "config_root": config_root,
                            "one": 1,
                            "collector": slf,
                            "args_dict": args_dict,
                            "getpass": getpass,
                        }
                        assert len(config.converters.mock_calls) == 0

                    def extra_prepare_after_activation(slf, config, args_dict):
                        called.append((3, config, args_dict))
                        config.converters.activate.assert_called_once_with()

                collector = Col()

                assert called == []
                collector.prepare(config_file, args_dict)
                assert called == [
                    (1, collector.configuration),
                    (2, collector.configuration, args_dict),
                    (3, collector.configuration, args_dict),
                ]

        it "takes in extra files":
            called = []
            args_dict = {}

            root = self.fake_config('{"one": 1}')
            extra1 = self.fake_config('{"two": 2, "three": 3}')
            extra2 = {"three": 4, "five": 5}

            with root as (config_root, config_file), extra1 as (_, e1):

                class Col(Collector):
                    def start_configuration(s):
                        return MergedOptions.using({})

                    def read_file(s, location):
                        return json.load(open(location))

                    def add_configuration(
                        s, configuration, collect_another_source, done, result, src
                    ):
                        configuration.update(result)

                collector = Col()
                collector.prepare(config_file, args_dict, extra_files=[e1, extra2])

                expected = {"one": 1, "two": 2, "three": 4, "five": 5}
                dct = collector.configuration.as_dict()

                for k, v in expected.items():
                    assert dct[k] == v

    describe "Collecting configuration":
        it "uses start_configuration, read_file, home_dir_configuration, config_file, add_configuration and extra_configuration_collection":
            called = []
            args_dict = {}
            configuration = MergedOptions.using({})

            result_home_dir = mock.MagicMock(name="result_home_dir")
            result_config_file = mock.MagicMock(name="result_config_file")

            with self.fake_config() as (config_root, config_file):
                home_dir = os.path.join(config_root, "home.json")
                with open(home_dir, "w") as fle:
                    fle.write("{}")
                results = {config_file: result_config_file, home_dir: result_home_dir}

                class Col(Collector):
                    def start_configuration(slf):
                        called.append((1,))
                        return configuration

                    def read_file(slf, location):
                        called.append((2, location))
                        return results[location]

                    def add_configuration(slf, config, collect_another_source, done, result, src):
                        called.append((3, config, result, src))

                    def home_dir_configuration_location(slf):
                        return home_dir

                    def extra_configuration_collection(slf, config):
                        assert [c[0] for c in called] == [1, 2, 3, 2, 3]
                        called.append((4, config))

                collector = Col()
                collector.collect_configuration(config_file, args_dict)
                assert called == [
                    (1,),
                    (2, home_dir),
                    (3, configuration, result_home_dir, home_dir),
                    (2, config_file),
                    (3, configuration, result_config_file, config_file),
                    (4, configuration),
                ]

        it "ignores home_dir if it's not specified":
            called = []
            args_dict = {}
            configuration = MergedOptions.using({})

            result_config_file = mock.MagicMock(name="result_config_file")

            with self.fake_config() as (config_root, config_file):
                results = {config_file: result_config_file}

                class Col(Collector):
                    def start_configuration(slf):
                        called.append((1,))
                        return configuration

                    def read_file(slf, location):
                        called.append((2, location))
                        return results[location]

                    def add_configuration(slf, config, collect_another_source, done, result, src):
                        called.append((3, config, result, src))

                    def extra_configuration_collection(slf, config):
                        assert [c[0] for c in called] == [1, 2, 3]
                        called.append((4, config))

                collector = Col()
                collector.collect_configuration(config_file, args_dict)
                assert called == [
                    (1,),
                    (2, config_file),
                    (3, configuration, result_config_file, config_file),
                    (4, configuration),
                ]

        it "gives a function for adding more sources to add_configuration":
            called = []
            args_dict = {}
            configuration = MergedOptions.using({})

            with self.fake_config() as (config_root, config_file):
                another_loc = os.path.join(config_root, "another.json")
                with open(another_loc, "w") as fle:
                    fle.write("{}")

                other_loc = os.path.join(config_root, "other.json")
                with open(other_loc, "w") as fle:
                    fle.write("{}")

                results = {
                    config_file: {"extra": other_loc},
                    other_loc: {"nested": another_loc},
                    another_loc: {"stuff": "a"},
                }

                class Col(Collector):
                    def start_configuration(slf):
                        called.append((1,))
                        return configuration

                    def read_file(slf, location):
                        called.append((2, location))
                        return results[location]

                    def add_configuration(slf, config, collect_another_source, done, result, src):
                        if "extra" in result:
                            collect_another_source(result["extra"])
                        if "nested" in result:
                            collect_another_source(
                                result["nested"], prefix=["once", "twice"], extra={"a": "b"}
                            )
                        called.append((3, config, result, src))

                    def extra_configuration_collection(slf, config):
                        assert [c[0] for c in called] == [1, 2, 2, 2, 3, 3, 3]
                        called.append((4, config))

                collector = Col()
                collector.collect_configuration(config_file, args_dict)
                assert called == [
                    (1,),
                    (2, config_file),
                    (2, other_loc),
                    (2, another_loc),
                    (
                        3,
                        configuration,
                        {"once": {"twice": {"stuff": "a", "a": "b", "config_root": config_root}}},
                        another_loc,
                    ),
                    (
                        3,
                        configuration,
                        {"nested": another_loc, "config_root": config_root},
                        other_loc,
                    ),
                    (
                        3,
                        configuration,
                        {"extra": other_loc, "config_root": config_root},
                        config_file,
                    ),
                    (4, configuration),
                ]

        it "Can't create a circular loop using collect_another_source":
            called = []
            args_dict = {}
            configuration = MergedOptions.using({})

            with self.fake_config() as (config_root, config_file):
                other_loc = os.path.join(config_root, "other.json")
                with open(other_loc, "w") as fle:
                    fle.write("{}")
                results = {config_file: {"extra": other_loc}, other_loc: {"extra": config_file}}

                class Col(Collector):
                    def start_configuration(slf):
                        called.append((1,))
                        return configuration

                    def read_file(slf, location):
                        called.append((2, location))
                        return results[location]

                    def add_configuration(slf, config, collect_another_source, done, result, src):
                        assert result["config_root"] == config_root
                        collect_another_source(result["extra"])
                        called.append((3, config, result, src))

                    def extra_configuration_collection(slf, config):
                        assert [c[0] for c in called] == [1, 2, 2, 3, 3]
                        called.append((4, config))

                collector = Col()
                collector.collect_configuration(config_file, args_dict)
                assert called == [
                    (1,),
                    (2, config_file),
                    (2, other_loc),
                    (
                        3,
                        configuration,
                        {"extra": config_file, "config_root": config_root},
                        other_loc,
                    ),
                    (
                        3,
                        configuration,
                        {"extra": other_loc, "config_root": config_root},
                        config_file,
                    ),
                    (4, configuration),
                ]

        it "collects errors from reading files and raises a mother exception":

            class BadJson(DelfickError):
                pass

            class BadConfiguration(DelfickError):
                pass

            called = []
            args_dict = {}
            with self.fake_config() as (config_root, config_file):
                home_dir = os.path.join(config_root, "home.json")
                with open(home_dir, "w") as fle:
                    fle.write("{}")

                class Col(Collector):
                    BadFileErrorKls = BadJson
                    BadConfigurationErrorKls = BadConfiguration

                    def start_configuration(slf):
                        called.append(0)
                        return MergedOptions.using({})

                    def read_file(slf, location):
                        called.append((1, location))
                        raise BadJson(location=location)

                    def add_configuration(slf, *args, **kwargs):
                        assert False, "This shouldn't get called"

                    def extra_configuration_collection(slf, config):
                        called.append(2)

                    def home_dir_configuration_location(slf):
                        return home_dir

                with assertRaises(
                    BadConfiguration,
                    "Some of the configuration was broken",
                    _errors=[BadJson(location=home_dir), BadJson(location=config_file)],
                ):
                    collector = Col()
                    collector.collect_configuration(config_file, args_dict)
                assert called == [0, (1, home_dir), (1, config_file), 2]
