# coding: spec

from delfick_project.norms.obj import Fields
from delfick_project.norms import dictobj

from delfick_project.errors_pytest import assertRaises

from unittest import mock
import pytest
import sys

describe "Fields":

    @pytest.fixture()
    def cached_fields(self):
        cache = {}
        with mock.patch("delfick_project.norms.obj._cached_fields", cache):
            yield cache

    describe "make classmethod":
        it "it memoizes Fields", cached_fields:
            FakeFields = mock.Mock(name="Fields")
            instance = mock.Mock(name="instance")
            FakeFields.return_value = instance

            kls = mock.Mock(name="kls")
            fields = mock.Mock(name="fields")

            with mock.patch("delfick_project.norms.obj.Fields", FakeFields):
                i = Fields.make(kls, fields)
                assert i is instance
                assert cached_fields[kls] is instance

                i = Fields.make(kls, fields)
                assert i is instance
                assert cached_fields[kls] is instance

            FakeFields.assert_called_once_with(kls, fields)

        it "returns None if there are no fields", cached_fields:
            for fields in ([], (), {}, None):
                kls = mock.Mock(name="kls")
                i = Fields.make(kls, fields)
                assert i is None
                assert cached_fields[kls] is None

        it "works without mocks":
            from delfick_project.norms.obj import _cached_fields

            try:

                class Thing:
                    fields = ["one"]

                i = Fields.make(Thing, Thing.fields)
                assert isinstance(i, Fields)
                assert _cached_fields[Thing] is i

                i2 = Fields.make(Thing, Thing.fields)
                assert i is i2
                assert _cached_fields[Thing] is i2
            finally:
                if Thing in _cached_fields:
                    del _cached_fields[Thing]

    describe "construction":
        it "complains if fields is neither list/tuple/dict":
            kls = type("Kls", (), {})
            for fields in (0, 1, None, True, False, lambda: 1, kls):
                with assertRaises(
                    TypeError,
                    ".+ should be a list, tuple or dictionary, got {0}".format(type(fields)),
                ):
                    Fields(kls, fields)

        it "complains if we have duplicated fields":
            kls = type("Kls", (), {})
            msg = r"Found duplicated fields in definition of {0}: \['one'\]".format(kls)
            with assertRaises(TypeError, msg):
                Fields(kls, ["one", "one", "two"])

            with assertRaises(TypeError, msg):
                Fields(kls, {("one", 1): "", ("two", 2): "", ("one", 3): ""})

            with assertRaises(TypeError, msg):
                Fields(kls, [("one", 1), ("one", 2)])

        it "complains if a fields is not correct":
            kls = type("Kls", (), {})

            incorrect = [
                0,
                1,
                False,
                True,
                None,
                [],
                ["asdf"],
                ["asdf", True],
                (),
                ("asdf",),
                {},
                {"asdf": True},
                lambda: 1,
            ]

            for bad in incorrect:
                testcases = [(bad,), [bad]]

                try:
                    fs = {bad: "help"}
                except TypeError:
                    pass
                else:
                    testcases.append(fs)

                for fields in testcases:
                    with assertRaises(TypeError, ".+ is not a valid field, .+"):
                        Fields(kls, fields)

        it "sets posargs for list/tuple fields":
            kls = type("kls", (), {})
            fields = ["one", ("two", True), "three", ("four", False)]
            for fs in (Fields(kls, fields), Fields(kls, tuple(fields))):
                assert fs.posargs == [("one",), ("two", True), ("three",), ("four", False)]
                assert fs.kwargs == []

        it "sets posargs for dictionary fields":
            kls = type("kls", (), {})
            fields = {"one": "h1", ("two", True): "h2", "three": "h3", ("four", False): "h4"}
            fs = Fields(kls, fields)
            assert fs.posargs == []
            assert sorted(fs.kwargs) == sorted([("one",), ("two", True), ("three",), ("four", False)])

    describe "resolving with posargs":
        it "complains if we provide more positional arguments than we have":
            fields = Fields(None, [("one", 1)])
            msg = "Expected up to 1 positional arguments, got 2"
            with assertRaises(TypeError, msg):
                fields.resolve((1, 2), {})

        it "complains if providing an argument as both positional and keyword":
            fields = Fields(None, [("one", 1)])
            msg = r"Cannot provide a field \(one\) as both positional and keyword arguments"
            with assertRaises(TypeError, msg):
                fields.resolve((1,), {"one": 2})

        it "works when no defaults and exact number of positional":
            fields = Fields(None, ["one", "two"])
            assert fields.resolve((1, 2), {}) == {"one": 1, "two": 2}

        it "works when we have a default":
            r = mock.NonCallableMock(name="r")
            fields = Fields(None, ["one", ("two", r)])
            assert fields.resolve((1,), {}) == {"one": 1, "two": r}

        it "works when the default is a callable":
            r = mock.NonCallableMock(name="r")
            fields = Fields(None, ["one", ("two", lambda: r)])
            assert fields.resolve((1,), {}) == {"one": 1, "two": r}

        it "does not call defaults if not needed":
            r = mock.Mock(name="r")
            fields = Fields(None, ["one", ("two", r)])
            assert fields.resolve((1,), {"two": 1}) == {"one": 1, "two": 1}
            assert len(r.mock_calls) == 0

            assert fields.resolve((1, 2), {}) == {"one": 1, "two": 2}
            assert len(r.mock_calls) == 0

        it "complains if we don't supply enough and no default":
            fields = Fields(None, ["one", "two"])
            msg = r"No default value set for positional argument 1 \(two\) and no value provided"
            with assertRaises(TypeError, msg):
                fields.resolve((1,), {})

        it "works with a mixture of pos and kw args":
            fields = Fields(None, ["one", ("two", 2), "three", ("four", 4)])

            ags = (3,)
            kw = {"three": "th"}
            assert fields.resolve(ags, kw) == {"one": 3, "two": 2, "three": "th", "four": 4}

            ags = (5, "tw", 11)
            kw = {}
            assert fields.resolve(ags, kw) == {"one": 5, "two": "tw", "three": 11, "four": 4}

            ags = ()
            kw = {"one": 34, "two": 43, "three": 33, "four": 22}
            assert fields.resolve(ags, kw) == kw

        it "complains if we have keyword arguments that aren't defined":
            fields = Fields(None, [("one", 1)])
            msg = r"Received a keyword argument \(wat\) that isn't on the class"
            with assertRaises(TypeError, msg):
                fields.resolve((), {"wat": 2})

    describe "resolving with kwargs":
        it "works":
            fields = Fields(None, {"one": "", "two": ""})
            kw = {"one": 13, "two": 14}
            assert fields.resolve((), kw) == kw

        it "complains if we specify arguments not defined":
            fields = Fields(None, {"one": "", "two": ""})
            kw = {"one": 13, "two": 14, "three": 15}
            msg = r"Received a keyword argument \(three\) that isn't on the class"
            with assertRaises(TypeError, msg):
                fields.resolve((), kw)

        it "complains if we provide any positional arguments":
            fields = Fields(None, {"one": "", "two": ""})
            with assertRaises(TypeError, "Expected only keyword arguments"):
                fields.resolve((1, 2), {})

        it "complains if missing arguments with no defaults":
            fields = Fields(None, {"one": "", "two": ""})
            msg = r"No default value set for keyword argument \(two\) and no value provided"
            with assertRaises(TypeError, msg):
                fields.resolve((), {"one": "wat"})

        it "works if we have defaults":
            fields = Fields(None, {("one", 11): "", ("two", 12): ""})
            assert fields.resolve((), {}) == {"one": 11, "two": 12}

            assert fields.resolve((), {"two": 13}) == {"one": 11, "two": 13}

        it "does not call defaults if not needed":
            r = mock.Mock(name="r")
            fields = Fields(None, {("one", r): "", ("two", 12): ""})
            assert fields.resolve((), {"one": 13}) == {"one": 13, "two": 12}
            assert len(r.mock_calls) == 0

describe "dictobj":

    @pytest.fixture(autouse=True)
    def cached_fields(self):
        cache = {}
        with mock.patch("delfick_project.norms.obj._cached_fields", cache):
            yield cache

    it "says is_dict":

        class D(dictobj):
            pass

        assert D.is_dict
        assert D().is_dict

    it "defines Fields for classes at definition", cached_fields:
        if sys.version_info.major == 3 and sys.version_info.minor < 6:
            pytest.skip("No subclass hook before python3.6")

        class D(dictobj):
            fields = ["one"]

        fields = cached_fields[D]
        assert isinstance(fields, Fields)
        assert fields.kls is D
        assert fields.posargs == [("one",)]
        assert fields.kwargs == []

    it "complains on definition if fields are nonsensical":
        if sys.version_info.major == 3 and sys.version_info.minor < 6:
            pytest.skip("No subclass hook before python3.6")

        msg = "Found duplicated fields in definition .+"
        with assertRaises(TypeError, msg):

            class D(dictobj):
                fields = ["one", "one"]

    it "calls setup with args and kwargs":
        called = []

        class D(dictobj):
            fields = ["one", "two"]

            def setup(self, *args, **kwargs):
                called.append((args, kwargs))

        d = D(1, two=3)
        assert called == [((1,), {"two": 3})]

    it "complains if no fields but specified positional arguments":
        for fs in (None, [], {}, ()):

            class D(dictobj):
                fields = fs

            msg = "Expected 0 positional arguments, got 2"
            with assertRaises(TypeError, msg):
                D(1, 2)

    it "complains if no fields but specified keyword arguments":
        for fs in (None, [], {}, ()):

            class D(dictobj):
                fields = fs

            msg = "Expected 0 keyword arguments, got 2"
            with assertRaises(TypeError, msg):
                D(one=1, two=2)

    it "sets value on the instance":

        class D(dictobj):
            fields = ["one", ("two", lambda: 11), ("three", 3), "four"]

        d = D(1, four=20)

        assert d.one == 1
        assert d.two == 11
        assert d.three == 3
        assert d.four == 20

        class E(dictobj):
            fields = {"one": "", ("two", lambda: 12): "", ("three", 4): "", "four": ""}

        e = E(one=5, four=90)

        assert e.one == 5
        assert e.two == 12
        assert e.three == 4
        assert e.four == 90

    it "says empty dictobj are truthy":

        class D(dictobj):
            pass

        d = D()
        assert d
        assert d.as_dict() == {}

    describe "property access":

        @pytest.fixture()
        def instance(self):
            class D(dictobj):
                fields = ["one", "two"]

                @property
                def three(s):
                    return 3

                def four(s):
                    return 4

                @property
                def five(s):
                    return s._five

                @five.setter
                def five(s, v):
                    s._five = v

            return D(1, 2)

        describe "object notation":

            it "can access properties", instance:
                assert instance.one == 1
                assert instance.two == 2
                assert instance.three == 3
                assert instance.four() == 4

            it "complains with attribute error on properties that don't exist", instance:
                with assertRaises(AttributeError, "nonexistant"):
                    instance.nonexistant

            it "can't override non settable properties", instance:
                with assertRaises(AttributeError, "can't set attribute"):
                    instance.three = 6

                instance.five = 7
                assert instance.five == 7
                assert instance["five"] == 7

            it "can override properties on the class", instance:
                instance.four = 4
                assert instance.four == 4
                assert instance["four"] == 4

            it "can override properties", instance:
                instance.one = 100
                assert instance.one == 100
                assert instance["one"] == 100

            it "can delete properties", instance:
                del instance.one

                with assertRaises(AttributeError, "'D' object has no attribute 'one'"):
                    instance.one

                with assertRaises(KeyError, "one"):
                    instance["one"]

                with assertRaises(AttributeError, "one"):
                    del instance.one

        describe "dictioanry notation":

            it "can access properties", instance:
                assert instance["one"] == 1
                assert instance["two"] == 2
                assert instance["three"] == 3
                assert instance["four"]() == 4

            it "complains with attribute error on properties that don't exist", instance:
                with assertRaises(KeyError, "nonexistant"):
                    instance["nonexistant"]

            it "can't override non settable properties", instance:
                with assertRaises(AttributeError, "can't set attribute"):
                    instance["three"] = 6

                instance["five"] = 7
                assert instance["five"] == 7
                assert instance.five == 7

            it "can override properties on the class", instance:
                instance["four"] = 4
                assert instance["four"] == 4
                assert instance.four == 4

            it "can override properties", instance:
                instance["one"] = 100
                assert instance["one"] == 100
                assert instance.one == 100

            it "can delete properties", instance:
                del instance["one"]

                with assertRaises(AttributeError, "'D' object has no attribute 'one'"):
                    instance.one

                with assertRaises(KeyError, "one"):
                    instance["one"]

                with assertRaises(KeyError, "one"):
                    del instance["one"]

    describe "cloning":
        it "works":
            three = mock.Mock(name="three")
            r = mock.Mock(name="r", return_value=three)

            class D(dictobj):
                five = 20
                fields = ["one", ("two", 3), ("three", r)]

                @property
                def six(s):
                    return 6

            d = D(1, two=4)
            assert d.one == 1
            assert d.two == 4
            assert d.three is three
            r.assert_called_once_with()

            e = d.clone()
            assert e is not d
            assert e.one == 1
            assert e.two == 4
            assert e.three is three
            r.assert_called_once_with()

            d.one = 20
            assert d.one == 20
            assert e.one == 1

    describe "as_dict":
        it "works when we have no fields":
            for fs in (None, (), [], {}):

                class D(dictobj):
                    one = 1
                    fields = fs

                assert D().as_dict() == {}

        it "works with fields":
            for fs in (["one", "two"], ("one", "two"), {"one": "", "two": ""}):

                class D(dictobj):
                    fields = fs

                d = D(one=1, two={"a": "b"})

                assert d.as_dict() == {"one": 1, "two": {"a": "b"}}

        it "propagates as_dict to children":
            a = mock.Mock(name="a")
            b = mock.Mock(name="b")
            n = mock.Mock(name="n")

            m = mock.Mock(name="m")
            m.as_dict.return_value = n

            class E(dictobj):
                fields = ["three"]

            class D(dictobj):
                fields = ["one", "two"]

            d = D(one=m, two=E(three=5))
            assert d.as_dict(a=a, b=b) == {"one": n, "two": {"three": 5}}
            m.as_dict.assert_called_once_with(a=a, b=b)
