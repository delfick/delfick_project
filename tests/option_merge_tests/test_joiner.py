# coding: spec

from option_merge.joiner import dot_joiner, join
from option_merge.path import Path

import itertools

from delfick_error import DelfickErrorTestMixin
import unittest
import mock


class TestCase(unittest.TestCase, DelfickErrorTestMixin):
    pass


describe TestCase, "dot_joiner":
    it "joins keeping all dots in between":
        blah_possibilities = ["blah", ".blah", "blah.", ".blah.", "blah..", "..blah", "..blah.."]
        stuff_possibilities = [pos.replace("blah", "stuff") for pos in blah_possibilities]

        for pos in blah_possibilities:
            assert dot_joiner([pos]) == pos

        for blahpos, stuffpos in list(itertools.product(blah_possibilities, stuff_possibilities)):
            assert dot_joiner([blahpos, stuffpos]) == "{0}.{1}".format(blahpos, stuffpos)

    it "ignores strings":
        assert dot_joiner("blah") == "blah"

describe TestCase, "join":
    it "Joins as lists":
        assert join(Path([]), Path([])) == []
        assert join(Path([""]), Path([])) == []
        assert join(Path([""]), Path([""])) == []

        assert join(Path(["a", "b", "c"]), Path(["d", "e", "f"])) == ["a", "b", "c", "d", "e", "f"]
        assert join(Path(["a", "b", "c"]), ["d", "e", "f"]) == ["a", "b", "c", "d", "e", "f"]
        assert join(["a", "b", "c"], Path(["d", "e", "f"])) == ["a", "b", "c", "d", "e", "f"]
        assert join(["a", "b", "c"], ["d", "e", "f"]) == ["a", "b", "c", "d", "e", "f"]

    it "Joins as strings":
        assert join(Path(""), Path("")) == []
        assert join(Path("a.b.c"), Path("d.e.f")) == ["a.b.c", "d.e.f"]
        assert join("a.b.c", Path("d.e.f")) == ["a.b.c", "d.e.f"]
        assert join("a.b.c", "d.e.f") == ["a.b.c", "d.e.f"]
        assert join(Path("a.b.c"), "d.e.f") == ["a.b.c", "d.e.f"]
