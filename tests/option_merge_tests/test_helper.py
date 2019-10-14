# coding: spec

from delfick_project.option_merge import MergedOptions
from delfick_project.option_merge import helper as hp
from delfick_project.option_merge.path import Path

from delfick_project.norms import dictobj

from unittest import mock
import itertools


describe "prefixed_path_list":
    it "returns a clone if there is no prefix":
        path = [1, 2, 3]
        cloned, joined = hp.prefixed_path_list(path)
        assert cloned == [1, 2, 3]
        assert joined == "1.2.3"

        cloned.append(4)
        assert cloned == [1, 2, 3, 4]
        assert path == [1, 2, 3]

    it "returns it prefixed if there is a prefix":
        path = [1, 2, 3]
        prefix = [4, 5, 6]
        prefixed, joined = hp.prefixed_path_list(path, prefix=prefix)
        assert prefixed == [4, 5, 6, 1, 2, 3]
        assert joined == "4.5.6.1.2.3"

        prefixed.append(4)
        assert prefixed == [4, 5, 6, 1, 2, 3, 4]
        assert path == [1, 2, 3]

describe "prefixed_path_string":
    it "removes superfluous dots":
        for blah in ("blah", ".blah", "blah.", ".blah.", "..blah.", ".blah..", "..blah.."):
            assert hp.prefixed_path_string(blah) == ("blah", "blah")

    it "joins together two paths with one dot":
        blah_possibilities = ["blah", ".blah", "blah.", ".blah.", "blah..", "..blah", "..blah.."]
        stuff_possibilities = [pos.replace("blah", "stuff") for pos in blah_possibilities]

        for pos in blah_possibilities:
            assert hp.prefixed_path_string(pos) == ("blah", "blah")

        for blahpos, stuffpos in list(itertools.product(blah_possibilities, stuff_possibilities)):
            assert hp.prefixed_path_string(blahpos, prefix=stuffpos) == (
                "stuff.blah",
                "stuff.blah",
            )  #

describe "make_dict":
    it "returns just with first and data if no rest":
        data = mock.Mock(name="data")
        first = mock.Mock(name="first")
        assert hp.make_dict(first, [], data) == {first: data}

    it "returns with first and sequence of dicts from rest":
        r1 = mock.Mock(name="r1")
        r2 = mock.Mock(name="r2")
        r3 = mock.Mock(name="r3")
        data = mock.Mock(name="data")
        first = mock.Mock(name="first")
        assert hp.make_dict(first, [r1, r2, r3], data) == {first: {r1: {r2: {r3: data}}}}

describe "merge_into_dict":
    describe "with normal dictionaries":
        it "merges empty dicts into another empty dict":
            target = {}
            source = {}
            hp.merge_into_dict(target, source)
            assert target == {}

        it "merges a full dict into an empty dict":
            target = {}
            source = {"a": 1, "b": 2, "c": {"d": 3}}
            hp.merge_into_dict(target, source)
            assert target == {"a": 1, "b": 2, "c": {"d": 3}}

        it "merges a full dict ontop of another full dict":
            target = {"a": 5, "b": 2, "c": {"e": 7}, "f": 9}
            hp.merge_into_dict(target, {})
            assert target == {"a": 5, "b": 2, "c": {"e": 7}, "f": 9}

            source = {"a": 1, "b": 2, "c": {"d": 3}}
            hp.merge_into_dict(target, source)
            assert target == {"a": 1, "b": 2, "c": {"d": 3, "e": 7}, "f": 9}

        it "overrides dictionaries with scalar values":
            target = {"a": 5, "b": 2, "c": {"e": 7}}
            source = {"a": 1, "b": 2, "c": 3}
            hp.merge_into_dict(target, source)
            assert target == {"a": 1, "b": 2, "c": 3}

        it "overrides scalar values with dictionaries":
            target = {"a": 1, "b": 2, "c": 3}
            source = {"a": 5, "b": 2, "c": {"e": 7}}
            hp.merge_into_dict(target, source)
            assert target == {"a": 5, "b": 2, "c": {"e": 7}}

    describe "with MergedOptions":
        it "merges a MergedOptions into an empty dictionary":
            target = {}
            source = MergedOptions.using({"a": 5, "b": 2, "c": {"e": 7}})
            hp.merge_into_dict(target, source)
            assert target == {"a": 5, "b": 2, "c": {"e": 7}}

        it "merges a MergedOptions into a full dictionary":
            target = {"a": 5, "b": 2, "c": {"f": 7}}
            source = MergedOptions.using({"a": 1, "b": 2, "c": {"e": 7}})
            hp.merge_into_dict(target, source)
            assert target == {"a": 1, "b": 2, "c": {"f": 7, "e": 7}}

        it "merges a MergedOptions with prefixed data into an empty dictionary":
            target = {"a": 5, "b": 2, "c": {"f": 7}}
            source = MergedOptions()
            source["c"] = {"e": 7}
            hp.merge_into_dict(target, source)
            assert target == {"a": 5, "b": 2, "c": {"f": 7, "e": 7}}

        it "merges a nested MergedOptions into a dictionary":
            source1 = MergedOptions.using({"one": 1, "two": 2, "three": {"four": 4}})
            source2 = MergedOptions.using({"one": "ONE"})
            source3 = MergedOptions.using({"four": "FOUR"})
            source = MergedOptions.using({"a": 1}, source1, {"cap": source2})
            source["three"] = source3

            assert source.as_dict() == {
                "a": 1,
                "cap": {"one": "ONE"},
                "three": {"four": "FOUR"},
                "one": 1,
                "two": 2,
            }

            target = {"one": "thousand", "and": "fifteen"}
            hp.merge_into_dict(target, source)
            assert target == {
                "and": "fifteen",
                "a": 1,
                "cap": {"one": "ONE"},
                "three": {"four": "FOUR"},
                "one": 1,
                "two": 2,
            }

describe "convert_to_dict":
    it "works if the object's as_dict has no parameters":

        class Thing:
            def as_dict(s):
                return {"a": 1}

        t = hp.convert_to_dict(Thing(), (1,), {"a": 1})
        assert t == {"a": 1}

    it "works with dictobj":
        called = []

        class Other:
            def as_dict(s, *args, **kwargs):
                called.append((args, kwargs))
                return {"b": 2}

        class Thing(dictobj):
            fields = ["one"]

        t = hp.convert_to_dict(Thing(one=Other()), (1,), {"a": 1})
        assert t == {"one": {"b": 2}}
        assert called == [((1,), {"a": 1})]

    it "works with MergedOptions":
        called = []

        class Other:
            def as_dict(s, *args, **kwargs):
                called.append((args, kwargs))
                return {"b": 2}

        class Thing(dictobj):
            fields = ["one"]

        m = MergedOptions.using()
        m["wat"] = Thing(one=Other())

        m2 = MergedOptions.using({"thing": Thing(one="a")}, m)

        t = hp.convert_to_dict(m2, (), {})
        assert t == {"thing": {"one": "a"}, "wat": {"one": {"b": 2}}}
        assert called == [((), {"ignore": [], "seen": mock.ANY})]

    it "works with things that don't have as_dict":

        class Thing:
            pass

        for thing in (0, 1, "", "a", [], [1], {}, {"a": 1}, lambda: 1, Thing, Thing()):
            assert hp.convert_to_dict(thing, (1,), {"a": 1}) is thing

    it "doesn't use as_dict if is_dict is set to False":

        class Thing:
            is_dict = False

            def as_dict(s):
                return {"b": 1}

        thing = Thing()
        assert hp.convert_to_dict(thing, (), {}) is thing
