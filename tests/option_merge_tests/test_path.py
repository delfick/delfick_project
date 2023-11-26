# coding: spec

from unittest import mock

import pytest

from delfick_project.errors_pytest import assertRaises
from delfick_project.option_merge import Converters, NotFound
from delfick_project.option_merge.joiner import dot_joiner
from delfick_project.option_merge.path import Path

describe "Path":
    it "takes in path, configuration, converters and ignore_converters":
        path = mock.Mock(name="path")
        converters = mock.Mock(name="converters")
        configuration = mock.Mock(name="configuration")
        ignore_converters = mock.Mock(name="ignore_converters")
        path_obj = Path(path, configuration, converters, ignore_converters)

        assert path_obj.path == path
        assert path_obj.converters is converters
        assert path_obj.configuration is configuration
        assert path_obj.ignore_converters is ignore_converters

    describe "Convert factory method":
        it "returns the same object if already a Path object":
            path = mock.Mock(name="path")
            converters = mock.Mock(name="converters")
            configuration = mock.Mock(name="configuration")
            ignore_converters = mock.Mock(name="ignore_converters")
            path_obj = Path(path, configuration, converters, ignore_converters)
            converted = Path.convert(path_obj)
            assert converted is path_obj

    describe "Special methods":
        it "dot joins the path for __unicode__":
            assert str(Path("a.b.c.d")) == "a.b.c.d"
            assert str(Path(["a.b", "c", "d"])) == "a.b.c.d"
            assert str(Path(["a", "b", "c", "d"])) == "a.b.c.d"
            assert str(Path([["a", "b"], "c", "d"])) == "ab.c.d"

        it "returns boolean status of path for __nonzero__":
            assert Path("asdf")
            assert Path(["a", "b"])
            assert not Path("")
            assert not Path([])

        it "returns the length of path parts for __len__":
            assert len(Path("adsf")) == 1
            assert len(Path("")) == 0
            assert len(Path(["a.b", "c", "d"])) == 3

        it "yields each part of path parts for __iter__":
            assert list(Path("adsf")) == ["adsf"]
            assert list(Path("")) == []
            assert list(Path(["a.b", "c", "d"])) == ["a.b", "c", "d"]

        it "includes str of Path for repr":
            assert repr(Path("asdf.asdf.1")) == "<Path(asdf.asdf.1)>"
            assert repr(Path(["asdf", "asdf", "1"])) == "<Path(asdf.asdf.1)>"

        it "converts dot_joined of paths to determine equality":
            assert Path("asdf.adsf.1") == "asdf.adsf.1"
            assert Path(["asdf", "adsf", "1"]) == "asdf.adsf.1"

            assert Path("asdf.adsf.1") == ["asdf", "adsf", "1"]
            assert Path(["asdf", "adsf", "1"]) == ["asdf", "adsf", "1"]

            assert Path("asdf.adsf.1") == Path("asdf.adsf.1")
            assert Path(["asdf", "adsf", "1"]) == Path(["asdf", "adsf", "1"])

        it "converts dot_joined of paths to determine inequality":
            assert Path("asdf.adsf.1") == "asdf.adsf.1"

            assert Path("asdf.adsf.2") != "asdf.adsf.1"
            assert Path(["asdf", "adsf", "3"]) != "asdf.adsf.1"

            assert Path("asdf.adsf.4") != ["asdf", "adsf", "1"]
            assert Path(["asdf", "adsf", "5"]) != ["asdf", "adsf", "1"]

            assert Path("asdf.adsf.6") != Path("asdf.adsf.1")
            assert Path(["asdf", "adsf", "7"]) != Path(["asdf", "adsf", "1"])

        it "joins self to other and creates a clone using the result for __add__":
            path = mock.Mock(name="path")
            other = mock.Mock(name="other")
            clone = mock.Mock(name="clone")
            joined = mock.Mock(name="joined")

            join = mock.Mock(name="join", return_value=joined)
            using = mock.Mock(name="using", return_value=clone)

            path_obj = Path(path)
            with mock.patch("delfick_project.option_merge.path.join", join):
                with mock.patch.multiple(path_obj, using=using):
                    assert path_obj + other is clone

            using.assert_called_once_with(joined)
            join.assert_called_once_with(path_obj, other)

        it "uses the dot_join of the path for hashing the path":
            path = mock.Mock(name="path")
            assert hash(Path(path)) == hash(dot_joiner(path))
            assert hash(Path(["1", "2", "3"])) == hash("1.2.3")
            assert hash(Path("1.2.3")) == hash("1.2.3")

    describe "without":
        it "uses string_slicing if path is a string":
            assert Path("1.2.3").without("1.2") == Path("3")
            assert Path("1.2.3").without(Path("1.2")) == Path("3")
            assert Path("1.2.3").without(Path(["1", "2"])) == Path("3")

        it "works with string base against list path":
            assert Path(["1", "2", "3"]).without("1.2") == Path("3")
            assert Path(["1", "2", "3"]).without(Path("1.2")) == Path("3")

        it "raises NotFound if the prefix is not in the path":
            with assertRaises(NotFound):
                Path(["1", "2", "3"]).without("1.2.3.4")

            with assertRaises(NotFound):
                Path(["1", "2", "3"]).without("5.2")

        it "returns the path if base is empty":
            assert Path("a.b").without("") == Path("a.b")
            assert Path("a.b").without([]) == Path("a.b")
            assert Path("a.b").without(Path("")) == Path("a.b")

            assert Path(["a", "b"]).without("") == Path("a.b")
            assert Path(["a", "b"]).without([]) == Path("a.b")
            assert Path(["a", "b"]).without(Path("")) == Path("a.b")

    describe "Prefixed":
        it "returns a clone with the prefix joined to the path":
            path = mock.Mock(name="path")
            clone = mock.Mock(name="clone")
            prefix = mock.Mock(name="prefix")
            joined = mock.Mock(name="joined")

            join = mock.Mock(name="join", return_value=joined)
            using = mock.Mock(name="using", return_value=clone)

            path_obj = Path(path)
            with mock.patch("delfick_project.option_merge.path.join", join):
                with mock.patch.multiple(path_obj, using=using):
                    assert path_obj.prefixed(prefix) is clone

            using.assert_called_once_with(joined)
            join.assert_called_once_with(prefix, path_obj)

    describe "startswith":
        it "says whether the dot join of the path startswith the base":
            assert Path(["a.b", "c.d"]).startswith("a.b.c") is True
            assert Path("a.b.c.d").startswith("a.b.c") is True

            assert Path(["a.b", "c.d"]).startswith("b.c.d") is False
            assert Path("a.b.c.d").startswith("b.c.d") is False

    describe "endswith":
        it "says whether the dot join of the path endswith the suffix":
            assert Path(["a.b", "c.d"]).endswith("b.c.d") is True
            assert Path("a.b.c.d").endswith("b.c.d") is True

            assert Path(["a.b", "c.d"]).endswith("a.b.c") is False
            assert Path("a.b.c.d").endswith("a.b.c") is False

    describe "using":
        it "returns the same class with the new path and other same values and ignore_converters as True":
            p1 = mock.Mock(name="p1")
            p2 = mock.Mock(name="p2")
            conf = mock.Mock(name="conf")
            converters = mock.Mock(name="converters")
            ignore_converters = mock.Mock(name="ignore_converters")

            class Path2(Path):
                pass

            path = Path2(p1, conf, converters, ignore_converters=ignore_converters)
            new_path = path.using(p2)

            assert type(new_path) == Path2
            assert new_path.path is p2
            assert new_path.configuration is conf
            assert new_path.converters is converters
            assert new_path.ignore_converters is False

        it "returns the same class with the new path and other overrides":
            p1 = mock.Mock(name="p1")
            p2 = mock.Mock(name="p2")
            conf = mock.Mock(name="conf")
            conf2 = mock.Mock(name="conf2")
            converters = mock.Mock(name="converters")
            converters2 = mock.Mock(name="converters2")
            ignore_converters = mock.Mock(name="ignore_converters")
            ignore_converters2 = mock.Mock(name="ignore_converters2")

            class Path2(Path):
                pass

            path = Path2(p1, conf, converters, ignore_converters=ignore_converters)
            new_path = path.using(p2, conf2, converters2, ignore_converters2)

            assert type(new_path) == Path2
            assert new_path.path is p2
            assert new_path.configuration is conf2
            assert new_path.converters is converters2
            assert new_path.ignore_converters is ignore_converters2

    describe "Clone":
        it "Returns a new path with same everything":
            p1 = mock.Mock(name="p1")
            conf = mock.Mock(name="conf")
            converters = mock.Mock(name="converters")
            ignore_converters = mock.Mock(name="ignore_converters")

            path = Path(p1, conf, converters, ignore_converters=ignore_converters)
            new_path = path.clone()
            assert path.path is new_path.path
            assert path.converters is new_path.converters
            assert path.configuration is new_path.configuration
            assert path.ignore_converters is new_path.ignore_converters

    describe "ignoring_converters":
        it "returns a clone with the same path and ignore_converters default to True":
            p1 = mock.Mock(name="p1")
            conf = mock.Mock(name="conf")
            converters = mock.Mock(name="converters")
            path = Path(p1, conf, converters, False)

            new_path = path.ignoring_converters()
            assert new_path is not path
            assert new_path.path is p1
            assert new_path.configuration is conf
            assert new_path.converters is converters
            assert new_path.ignore_converters is True

        it "can be given an ignore_converters to use":
            p1 = mock.Mock(name="p1")
            conf = mock.Mock(name="conf")
            converters = mock.Mock(name="converters")
            path = Path(p1, conf, converters, False)

            ignore_converters2 = mock.Mock(name="ignore_converters2")
            new_path = path.ignoring_converters(ignore_converters=ignore_converters2)
            assert new_path is not path
            assert new_path.path is p1
            assert new_path.configuration is conf
            assert new_path.converters is converters
            assert new_path.ignore_converters is ignore_converters2

    describe "Doing a conversion":
        it "returns value as is if there are no converters":
            p1 = mock.Mock(name="p1")
            value = mock.Mock(name="value")

            find_converter = mock.Mock(name="find_converter")
            find_converter.return_value = (None, False)

            path = Path(p1)
            with mock.patch.object(path, "find_converter", find_converter):
                assert path.do_conversion(value) == (value, False)

        it "uses found converter and marks path as done with converters":
            p1 = mock.Mock(name="p1")
            value = mock.Mock(name="value")
            converters = Converters()
            converters.activate()

            path = Path(p1, converters=converters)
            assert converters.converted(path) is False

            converted = mock.Mock(name="converted")
            converter = mock.Mock(name="converter")
            converter.return_value = converted

            find_converter = mock.Mock(name="find_converter")
            find_converter.return_value = (converter, True)

            with mock.patch.object(path, "find_converter", find_converter):
                assert path.do_conversion(value) == (converted, True)

            # Converters should now have converted value
            assert converters.converted(path) is True
            assert converters.converted_val(path) is converted

            converter.assert_called_once_with(path, value)
            converted.post_setup.assert_called_once_with()

    describe "finding a converter":

        @pytest.fixture()
        def convm(self):
            class ConverterMocks:
                converter1 = mock.Mock(name="converter1")
                converter2 = mock.Mock(name="converter2")
                converter3 = mock.Mock(name="converter3")

            return ConverterMocks

        @pytest.fixture()
        def converters(self, convm):
            converters = Converters()
            converters.append(convm.converter1)
            converters.append(convm.converter2)
            converters.append(convm.converter3)

            converters.activate()
            return converters

        @pytest.fixture()
        def path(self, converters):
            p1 = mock.Mock(name="p1")
            return Path(p1, converters=converters)

        it "returns None if set to ignore_converters", path:
            assert path.ignoring_converters().find_converter() == (None, False)

        it "returns the first converter that has no matches attribute", convm, path:
            assert path.find_converter() == (convm.converter1, True)

        it "returns the first converter that matches the path", convm, path:
            convm.converter1.matches.return_value = False
            convm.converter2.matches.return_value = True
            assert path.find_converter() == (convm.converter2, True)

            convm.converter1.matches.assert_called_once_with(path)
            convm.converter2.matches.assert_called_once_with(path)

        it "returns None if no converter matches", convm, path:
            convm.converter1.matches.return_value = False
            convm.converter2.matches.return_value = False
            convm.converter3.matches.return_value = False
            assert path.find_converter() == (None, False)

            convm.converter1.matches.assert_called_once_with(path)
            convm.converter2.matches.assert_called_once_with(path)
            convm.converter3.matches.assert_called_once_with(path)

    describe "Finding converted value":
        it "returns False if there are no converters":
            p1 = mock.Mock(name="p1")
            path = Path(p1, converters=None)
            assert path.converted() is False

        it "returns what converters returns":
            p1 = mock.Mock(name="p1")
            result = mock.Mock(name="result")
            converters = mock.Mock(name="converters")
            converters.converted.return_value = result

            path = Path(p1, converters=converters)
            assert path.converted() is result

    describe "Finding a converted value":
        it "returns what converters returns":
            p1 = mock.Mock(name="p1")
            result = mock.Mock(name="result")
            converters = mock.Mock(name="converters")
            converters.converted_val.return_value = result

            path = Path(p1, converters=converters)
            assert path.converted_val() is result
