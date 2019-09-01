# coding: spec

from delfick_project.option_merge import NotFound, MergedOptions
from delfick_project.option_merge.value_at import value_at
from delfick_project.option_merge.path import Path

from delfick_project.errors_pytest import assertRaises

from unittest import mock


describe "value_at":
    it "returns as is if no path":
        data = mock.Mock(name="data")
        chain = mock.Mock(name="chain")
        assert value_at(data, None) == ([], data)
        assert value_at(data, None, chain=chain) == (chain, data)

    it "raises NotFound if no more path left and still at a dictionary":
        with assertRaises(NotFound):
            value_at({1: 2}, Path("somewhere"))

    it "returns data at path if it's in data":
        value = mock.Mock(name="value")
        path = Path("path")
        data = {path: value}
        assert value_at(data, path) == (Path("path"), value)

        c1 = mock.Mock(name="c1")
        c2 = mock.Mock(name="c2")
        chain = [c1, c2]
        assert value_at(data, path, chain=chain) == ([c1, c2, path], value)

    it "does largest matching first":
        value = mock.Mock(name="value")
        value2 = mock.Mock(name="value2")
        value3 = mock.Mock(name="value3")
        data = {"blah": {"meh": value}}
        assert value_at(data, Path("blah.meh")) == (Path(["blah", "meh"]), value)

        data["blah.meh"] = value2
        assert value_at(data, Path("blah.meh")) == (Path("blah.meh"), value2)

        data["blah.meh"] = {"stuff": value3}
        assert value_at(data, Path("blah.meh.stuff")) == (Path(["blah.meh", "stuff"]), value3)

    it "skips misleading paths":
        value = mock.Mock(name="value")
        data = {"blah": {"meh": {"stuff": value}}, "blah.meh": {"tree": 3}}
        assert value_at(data, Path("blah.meh.stuff")) == (["blah", "meh", "stuff"], value)

    it "skips paths with the same storage":
        data = MergedOptions.using({"a": "blah"})
        assert value_at(data, Path("a")) == (Path("a"), "blah")
        data["a"] = data["a"]
        assert value_at(data, Path("a")) == (Path("a"), "blah")

    it "digs into subclasses of dict":

        class blah(dict):
            is_dict = True

        b = blah({"a": 1})
        data = MergedOptions.using({"one": b})
        assert value_at(data, Path(["one", "a"])) == (Path(["one", "a"]), 1)
