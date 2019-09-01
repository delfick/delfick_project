# coding: spec

from input_algorithms.spec_base import Spec, NotSpecified, pass_through_spec, always_same_spec
from input_algorithms.errors import BadSpec, BadSpecValue, BadDirectory, BadFilename
from input_algorithms import spec_base as sb
from input_algorithms.meta import Meta

from tests.helpers import TestCase

from noseOfYeti.tokeniser.support import noy_sup_setUp
from namedlist import namedlist
import mock

describe TestCase, "Spec":
    it "takes in positional arguments and keyword arguments":
        m1 = mock.Mock("m1")
        m2 = mock.Mock("m2")
        m3 = mock.Mock("m3")
        m4 = mock.Mock("m4")
        spec = Spec(m1, m2, a=m3, b=m4)
        assert spec.pargs == (m1, m2)
        assert spec.kwargs == dict(a=m3, b=m4)

    it "calls setup if one is defined":
        called = []
        m1 = mock.Mock("m1")
        m2 = mock.Mock("m2")
        m3 = mock.Mock("m3")
        m4 = mock.Mock("m4")

        class Specd(Spec):
            def setup(sp, *pargs, **kwargs):
                assert pargs == (m1, m2)
                assert sp.pargs == (m1, m2)

                assert kwargs == dict(a=m3, b=m4)
                assert sp.kwargs == dict(a=m3, b=m4)
                called.append(sp)

        spec = Specd(m1, m2, a=m3, b=m4)
        assert called == [spec]

    describe "fake_filled":
        before_each:
            self.meta = mock.Mock(name="meta", spec=Meta)

        it "returns self.fake if it exists":
            res = mock.Mock(name="res")
            called = []
            with_non_defaulted_value = mock.Mock(name="with_non_defaulted_value")

            class Specd(Spec):
                def fake(specd, meta, with_non_defaulted):
                    assert meta is self.meta
                    assert with_non_defaulted is with_non_defaulted_value
                    called.append(1)
                    return res

            assert (
                Specd().fake_filled(self.meta, with_non_defaulted=with_non_defaulted_value)
            ) is res
            assert called == [1]

        it "returns default if there is no fake defined":
            res = mock.Mock(name="res")
            called = []
            with_non_defaulted_value = mock.Mock(name="with_non_defaulted_value")

            class Specd(Spec):
                def default(specd, meta):
                    assert meta is self.meta
                    called.append(1)
                    return res

            assert (
                Specd().fake_filled(self.meta, with_non_defaulted=with_non_defaulted_value)
            ) is res
            assert called == [1]

        it "returns NotSpecified if no fake or default specified":
            with_non_defaulted_value = mock.Mock(name="with_non_defaulted_value")
            assert (
                Spec().fake_filled(self.meta, with_non_defaulted=with_non_defaulted_value)
            ) is NotSpecified

    describe "normalise":
        describe "When normalise_either is defined":
            it "uses it's value if it returns a non NotSpecified value":
                val = mock.Mock(name="val")
                meta = mock.Mock(name="meta")
                result = mock.Mock(name="result")
                normalise_either = mock.Mock(name="normalise_either", return_value=result)

                Specd = type("Specd", (Spec,), {"normalise_either": normalise_either})
                assert Specd().normalise(meta, val) is result
                normalise_either.assert_called_once_with(meta, val)

        describe "When normalise_either returns NotSpecified":

            it "uses normalise_filled if the value is not NotSpecified":
                val = mock.Mock(name="val")
                meta = mock.Mock(name="meta")
                result = mock.Mock(name="result")
                normalise_either = mock.Mock(name="normalise_either", return_value=NotSpecified)
                normalise_filled = mock.Mock(name="normalise_either", return_value=result)

                Specd = type(
                    "Specd",
                    (Spec,),
                    {"normalise_either": normalise_either, "normalise_filled": normalise_filled},
                )
                assert Specd().normalise(meta, val) is result
                normalise_either.assert_called_once_with(meta, val)
                normalise_filled.assert_called_once_with(meta, val)

            it "uses normalise_empty if val is NotSpecified":
                val = NotSpecified
                meta = mock.Mock(name="meta")
                result = mock.Mock(name="result")
                normalise_either = mock.Mock(name="normalise_either", return_value=NotSpecified)
                normalise_empty = mock.Mock(name="normalise_empty", return_value=result)

                Specd = type(
                    "Specd",
                    (Spec,),
                    {"normalise_either": normalise_either, "normalise_empty": normalise_empty},
                )
                assert Specd().normalise(meta, val) is result
                normalise_either.assert_called_once_with(meta, val)
                normalise_empty.assert_called_once_with(meta)

        describe "When no normalise_either":
            describe "When value is NotSpecified":
                it "Uses normalise_empty if defined":
                    val = NotSpecified
                    meta = mock.Mock(name="meta")
                    result = mock.Mock(name="result")
                    normalise_empty = mock.Mock(name="normalise_empty", return_value=result)

                    Specd = type("Specd", (Spec,), {"normalise_empty": normalise_empty})
                    assert Specd().normalise(meta, val) is result
                    normalise_empty.assert_called_once_with(meta)

                it "uses default if defined and no normalise_empty":
                    val = NotSpecified
                    meta = mock.Mock(name="meta")
                    default = mock.Mock(name="default")
                    default_method = mock.Mock(name="default_method", return_value=default)

                    Specd = type("Specd", (Spec,), {"default": default_method})
                    assert Specd().normalise(meta, val) is default
                    default_method.assert_called_once_with(meta)

                it "returns NotSpecified otherwise":
                    val = NotSpecified
                    meta = mock.Mock(name="meta")
                    Specd = type("Specd", (Spec,), {})
                    assert Specd().normalise(meta, val) is NotSpecified

            describe "When value is not NotSpecified":
                it "Uses normalise_filled if defined":
                    val = mock.Mock(name="val")
                    meta = mock.Mock(name="meta")
                    result = mock.Mock(name="result")
                    normalise_filled = mock.Mock(name="normalise_filled", return_value=result)

                    Specd = type("Specd", (Spec,), {"normalise_filled": normalise_filled})
                    assert Specd().normalise(meta, val) is result
                    normalise_filled.assert_called_once_with(meta, val)

                it "complains if no normalise_filled":
                    val = mock.Mock(name="val")
                    meta = mock.Mock(name="meta")
                    Specd = type("Specd", (Spec,), {})
                    with self.fuzzyAssertRaisesError(
                        BadSpec, "Spec doesn't know how to deal with this value", meta=meta, val=val
                    ):
                        Specd().normalise(meta, val)

describe TestCase, "pass_through_spec":
    it "just returns whatever it is given":
        val = mock.Mock(name="val")
        meta = mock.Mock(name="meta")

        spec = pass_through_spec()
        assert spec.normalise(meta, val) is val
        assert spec.normalise(meta, NotSpecified) is NotSpecified

describe TestCase, "dictionary specs":
    __only_run_tests_in_children__ = True

    def make_spec(self):
        raise NotImplementedError()

    before_each:
        self.meta = mock.Mock(name="meta")

    it "has a default value of an empty dictionary":
        assert self.make_spec().default(self.meta) == {}

    it "complains if the value being normalised is not a dict":
        meta = mock.Mock(name="meta")
        for opt in (
            None,
            0,
            1,
            True,
            False,
            [],
            [1],
            lambda: 1,
            "",
            "asdf",
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected a dictionary", meta=meta, got=type(opt)
            ):
                self.make_spec().normalise(meta, opt)

    it "works with a dict":
        meta = mock.Mock(name="meta")
        dictoptions = {"a": 1, "b": 2}
        assert self.make_spec().normalise(meta, dictoptions) == dictoptions

    describe "dictionary_spec":
        make_spec = sb.dictionary_spec

    describe "dictof":

        def make_spec(self, name_spec=NotSpecified, value_spec=NotSpecified, nested=False):
            name_spec = pass_through_spec() if name_spec is NotSpecified else name_spec
            value_spec = pass_through_spec() if value_spec is NotSpecified else value_spec
            return sb.dictof(name_spec, value_spec, nested=nested)

        it "takes in a name_spec and a value_spec":
            name_spec = mock.Mock(name="name_spec")
            value_spec = mock.Mock(name="value_spec")
            do = sb.dictof(name_spec, value_spec)
            assert do.name_spec == name_spec
            assert do.value_spec == value_spec
            assert do.nested == False

        it "complains if a key doesn't match the name_spec":
            meta = mock.Mock(name="meta")
            at_one = mock.Mock(name="at_one")
            at_two = mock.Mock(name="at_two")
            at_three = mock.Mock(name="at_three")

            def at(val):
                if val == "one":
                    return at_one
                elif val == "two":
                    return at_two
                elif val == "three":
                    return at_three
                else:
                    assert False, "Unexpected value into at: {0}".format(val)

            meta.at.side_effect = at

            name_spec = mock.Mock(name="name_spec")
            error_one = BadSpecValue("one")
            error_three = BadSpecValue("three")

            def normalise(meta, val):
                if val == "one":
                    raise error_one
                elif val == "three":
                    raise error_three
                else:
                    return val

            name_spec.normalise.side_effect = normalise

            spec = self.make_spec(name_spec=name_spec)
            with self.fuzzyAssertRaisesError(
                BadSpecValue, meta=meta, _errors=[error_one, error_three]
            ):
                spec.normalise(meta, {"one": 1, "two": 2, "three": 3})

        it "complains if a value doesn't match the value_spec":
            meta = mock.Mock(name="meta")
            value_spec = mock.Mock(name="value_spec")
            error_two = BadSpecValue("two")
            error_four = BadSpecValue("four")

            def normalise(meta, val):
                if val == 2:
                    raise error_two
                elif val == 4:
                    raise error_four
                else:
                    return val

            value_spec.normalise.side_effect = normalise

            spec = self.make_spec(value_spec=value_spec)
            with self.fuzzyAssertRaisesError(
                BadSpecValue, meta=meta, _errors=[error_two, error_four]
            ):
                spec.normalise(meta, {"one": 1, "two": 2, "three": 3, "four": 4})

        it "can worked on nested values":
            meta = mock.Mock(name="meta")
            val = {"one": {"two": "3"}, "four": "4", "five": 5}
            spec = self.make_spec(value_spec=sb.integer_spec(), nested=True)
            assert spec.normalise(meta, val) == {"one": {"two": 3}, "four": 4, "five": 5}

describe TestCase, "tupleof":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = pass_through_spec()
        self.to = sb.tupleof(self.spec)

    it "takes in a spec":
        spec = mock.Mock(name="spec")
        lo = sb.tupleof(spec)
        assert lo.spec == spec

    it "has a default value of an empty tupe":
        assert self.to.default(self.meta) == ()

    it "turns the value into a tuple if not already a list":
        for opt in (
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            lambda: 1,
            "",
            "asdf",
            type("blah", (object,), {})(),
        ):
            assert self.to.normalise(self.meta, opt) == (opt,)

    it "turns lists into tuples of those items":
        assert self.to.normalise(self.meta, [1, 2, 3]) == (1, 2, 3)

    it "doesn't turn a tuple into a tuple of itself":
        assert self.to.normalise(self.meta, ()) == ()
        assert self.to.normalise(self.meta, (1, 2)) == (1, 2)

    it "complains about values that don't match the spec":
        meta = mock.Mock(name="meta")
        spec = mock.Mock(name="spec")
        error_two = BadSpecValue("two")
        error_four = BadSpecValue("four")

        def normalise(meta, val):
            if val == 2:
                raise error_two
            elif val == 4:
                raise error_four
            else:
                return val

        spec.normalise.side_effect = normalise

        self.to.spec = spec
        with self.fuzzyAssertRaisesError(BadSpecValue, meta=meta, _errors=[error_two, error_four]):
            self.to.normalise(meta, [1, 2, 3, 4])

describe TestCase, "listof":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = pass_through_spec()
        self.lo = sb.listof(self.spec)

    it "takes in a spec and possible expect":
        spec = mock.Mock(name="spec")
        expect = mock.Mock(name="expect")
        lo = sb.listof(spec, expect=expect)
        assert lo.spec == spec
        assert lo.expect == expect

        lo = sb.listof(spec)
        assert lo.spec == spec
        assert lo.expect == NotSpecified

    it "has a default value of an empty list":
        assert self.lo.default(self.meta) == []

    it "turns the value into a list if not already a list":
        for opt in (
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            lambda: 1,
            "",
            "asdf",
            type("blah", (object,), {})(),
        ):
            assert self.lo.normalise(self.meta, opt) == [opt]

    it "doesn't turn a list into a list of itself":
        assert self.lo.normalise(self.meta, []) == []
        assert self.lo.normalise(self.meta, [1, 2]) == [1, 2]

    it "returns the value if already the type specified by expect":

        class Value(object):
            pass

        val = Value()
        assert sb.listof(self.spec, expect=Value).normalise(self.meta, val) == [val]

    it "only normalises values not already the expected type":

        class Value(object):
            pass

        val_same = Value()
        spec = always_same_spec(val_same)
        proxied_spec = mock.Mock(name="spec", spec_set=["normalise"])
        proxied_spec.normalise.side_effect = spec.normalise

        indexed_one = mock.Mock(name="indexed_one")
        indexed_three = mock.Mock(name="indexed_three")

        def indexed_at(val):
            if val == 1:
                return indexed_one
            elif val == 3:
                return indexed_three
            else:
                assert False, "Unexpected value into indexed_at: {0}".format(val)

        self.meta.indexed_at.side_effect = indexed_at

        val1 = Value()
        val2 = Value()
        result = sb.listof(proxied_spec, expect=Value).normalise(
            self.meta, [val1, "stuff", val2, "blah"]
        )
        assert proxied_spec.normalise.mock_calls == [
            mock.call(indexed_one, "stuff"),
            mock.call(indexed_three, "blah"),
        ]
        assert result == [val1, val_same, val2, val_same]

    it "complains about values that don't match the spec":
        meta = mock.Mock(name="meta")
        spec = mock.Mock(name="spec")
        error_two = BadSpecValue("two")
        error_four = BadSpecValue("four")

        def normalise(meta, val):
            if val == 2:
                raise error_two
            elif val == 4:
                raise error_four
            else:
                return val

        spec.normalise.side_effect = normalise

        self.lo.spec = spec
        with self.fuzzyAssertRaisesError(BadSpecValue, meta=meta, _errors=[error_two, error_four]):
            self.lo.normalise(meta, [1, 2, 3, 4])

    it "complains about values that aren't instances of expect":
        spec = mock.Mock(name="spec")
        meta_indexed_0 = mock.Mock(name="meta_indexed_0")
        meta_indexed_1 = mock.Mock(name="meta_indexed_1")
        meta_indexed_2 = mock.Mock(name="meta_indexed_2")
        meta_indexed_3 = mock.Mock(name="meta_indexed_3")

        def indexed_at(val):
            if val == 0:
                return meta_indexed_0
            elif val == 1:
                return meta_indexed_1
            elif val == 2:
                return meta_indexed_2
            elif val == 3:
                return meta_indexed_3
            else:
                assert False, "Don't expect indexed_at with value {0}".format(val)

        self.meta.indexed_at.side_effect = indexed_at

        class Value(object):
            pass

        class Other(object):
            def __eq__(self, other):
                return False

            def __lt__(self, other):
                return False

        other_2 = Other()
        other_4 = Other()
        error_two = BadSpecValue(
            "Expected normaliser to create a specific object",
            expected=Value,
            meta=meta_indexed_1,
            got=other_2,
        )
        error_four = BadSpecValue(
            "Expected normaliser to create a specific object",
            expected=Value,
            meta=meta_indexed_3,
            got=other_4,
        )

        def normalise(meta, val):
            if val == 2:
                return other_2
            elif val == 4:
                return other_4
            else:
                return Value()

        spec.normalise.side_effect = normalise

        self.lo.spec = spec
        self.lo.expect = Value
        with self.fuzzyAssertRaisesError(
            BadSpecValue, meta=self.meta, _errors=[error_two, error_four]
        ):
            self.lo.normalise(self.meta, [1, 2, 3, 4])

describe TestCase, "set_options":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.so = sb.set_options()

    it "takes in the options":
        m1 = mock.Mock("m1")
        m2 = mock.Mock("m2")
        spec = sb.set_options(a=m1, b=m2)
        assert spec.options == dict(a=m1, b=m2)

    it "defaults to an empty dictionary":
        assert self.so.default(self.meta) == {}

    it "complains if the value being normalised is not a dict":
        meta = mock.Mock(name="meta")
        for opt in (
            0,
            1,
            True,
            False,
            [],
            [1],
            lambda: 1,
            "",
            "asdf",
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected a dictionary", meta=meta, got=type(opt)
            ):
                self.so.normalise(meta, opt)

    it "Ignores options that aren't specified":
        meta = mock.Mock(name="meta")
        dictoptions = {"a": "1", "b": "2"}
        assert self.so.normalise(meta, dictoptions) == {}

        self.so.options = {"a": sb.string_spec()}
        assert self.so.normalise(meta, dictoptions) == {"a": "1"}

        self.so.options = {"a": sb.string_spec(), "b": sb.string_spec()}
        assert self.so.normalise(meta, dictoptions) == {"a": "1", "b": "2"}

    it "checks the value of our known options":
        one_spec_result = mock.Mock(name="one_spec_result")
        one_spec = mock.Mock(name="one_spec", spec_set=["normalise"])
        one_spec.normalise.return_value = one_spec_result

        two_spec_result = mock.Mock(name="two_spec_result")
        two_spec = mock.Mock(name="two_spec", spec_set=["normalise"])
        two_spec.normalise.return_value = two_spec_result

        self.so.options = {"one": one_spec, "two": two_spec}
        assert self.so.normalise(self.meta, {"one": 1, "two": 2}) == {
            "one": one_spec_result,
            "two": two_spec_result,
        }

    it "collects errors":
        one_spec_error = BadSpecValue("Bad one")
        one_spec = mock.Mock(name="one_spec", spec_set=["normalise"])
        one_spec.normalise.side_effect = one_spec_error

        two_spec_error = BadSpecValue("Bad two")
        two_spec = mock.Mock(name="two_spec", spec_set=["normalise"])
        two_spec.normalise.side_effect = two_spec_error

        self.so.options = {"one": one_spec, "two": two_spec}
        with self.fuzzyAssertRaisesError(
            BadSpecValue, meta=self.meta, _errors=[one_spec_error, two_spec_error]
        ):
            self.so.normalise(self.meta, {"one": 1, "two": 2, "three": 3})

    describe "fake_filled":

        it "creates a fake from it's options":
            one_spec_fake = mock.Mock(name="one_spec_fake")
            one_spec = mock.Mock(name="one_spec", spec_set=["fake_filled"])
            one_spec.fake_filled.return_value = one_spec_fake

            two_spec_fake = mock.Mock(name="two_spec_fake")
            two_spec = mock.Mock(name="two_spec", spec_set=["fake_filled"])
            two_spec.fake_filled.return_value = two_spec_fake

            self.so.options = {"one": one_spec, "two": two_spec}
            assert self.so.fake_filled(self.meta) == {"one": one_spec_fake, "two": two_spec_fake}

        it "ignores NotSpecified fakes":
            one_spec_fake = mock.Mock(name="one_spec_fake")
            one_spec = mock.Mock(name="one_spec", spec_set=["fake_filled"])
            one_spec.fake_filled.return_value = one_spec_fake

            two_spec = mock.Mock(name="two_spec", spec_set=["fake_filled"])
            two_spec.fake_filled.return_value = NotSpecified

            self.so.options = {"one": one_spec, "two": two_spec}
            assert self.so.fake_filled(self.meta) == {"one": one_spec_fake}

        it "includes NotSpecified fakes if with_non_defaulted":
            one_spec_fake = mock.Mock(name="one_spec_fake")
            one_spec = mock.Mock(name="one_spec", spec_set=["fake_filled"])
            one_spec.fake_filled.return_value = one_spec_fake

            two_spec = mock.Mock(name="two_spec", spec_set=["fake_filled"])
            two_spec.fake_filled.return_value = NotSpecified

            self.so.options = {"one": one_spec, "two": two_spec}
            assert self.so.fake_filled(self.meta, with_non_defaulted=True) == {
                "one": one_spec_fake,
                "two": NotSpecified,
            }

describe TestCase, "defaulted":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = mock.Mock(name="spec", spec_set=["normalise"])
        self.dflt = mock.Mock(name="dflt")
        self.dfltd = sb.defaulted(self.spec, self.dflt)

    it "takes in a spec and a default":
        dflt = mock.Mock(name="dflt")
        spec = mock.Mock(name="spec")
        dfltd = sb.defaulted(spec, dflt)
        assert dfltd.spec == spec
        assert dfltd.default(self.meta) == dflt

    it "defaults to the dflt":
        assert self.dfltd.default(self.meta) is self.dflt
        assert self.dfltd.normalise(self.meta, NotSpecified) is self.dflt

    it "proxies the spec if a value is provided":
        val = mock.Mock(name="val")
        result = mock.Mock(name="result")
        self.spec.normalise.return_value = result
        assert self.dfltd.normalise(self.meta, val) is result
        self.spec.normalise.assert_called_once_with(self.meta, val)

describe TestCase, "required":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = mock.Mock(name="spec", spec_set=["normalise", "fake_filled"])
        self.rqrd = sb.required(self.spec)

    it "takes in a spec":
        spec = mock.Mock(name="spec")
        rqrd = sb.required(spec)
        assert rqrd.spec == spec

    it "Complains if there is no value":
        with self.fuzzyAssertRaisesError(
            BadSpecValue, "Expected a value but got none", meta=self.meta
        ):
            self.rqrd.normalise(self.meta, NotSpecified)

    it "proxies the spec if a value is provided":
        val = mock.Mock(name="val")
        result = mock.Mock(name="result")
        self.spec.normalise.return_value = result
        assert self.rqrd.normalise(self.meta, val) is result
        self.spec.normalise.assert_called_once_with(self.meta, val)

    it "proxies self.spec for fake_filled":
        res = mock.Mock(name="res")
        self.spec.fake_filled.return_value = res
        assert self.rqrd.fake_filled(self.meta) is res

describe TestCase, "boolean":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    it "complains if the value is not a boolean":
        for opt in (
            0,
            1,
            {},
            {1: 1},
            [],
            [1],
            lambda: 1,
            "",
            "asdf",
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected a boolean", meta=self.meta, got=type(opt)
            ):
                sb.boolean().normalise(self.meta, opt)

    it "returns value as is if a boolean":
        assert sb.boolean().normalise(self.meta, True) is True
        assert sb.boolean().normalise(self.meta, False) is False

describe TestCase, "directory_spec":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    it "complains if the value is not a string":
        for opt in (
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            [],
            [1],
            lambda: 1,
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadDirectory, "Didn't even get a string", meta=self.meta, got=type(opt)
            ):
                sb.directory_spec(sb.any_spec()).normalise(self.meta, opt)

    it "complains if the meta doesn't exist":
        with self.a_temp_dir(removed=True) as directory:
            with self.fuzzyAssertRaisesError(
                BadDirectory, "Got something that didn't exist", meta=self.meta, directory=directory
            ):
                sb.directory_spec().normalise(self.meta, directory)

    it "complains if the meta isn't a directory":
        with self.a_temp_file() as filename:
            with self.fuzzyAssertRaisesError(
                BadDirectory,
                "Got something that exists but isn't a directory",
                meta=self.meta,
                directory=filename,
            ):
                sb.directory_spec().normalise(self.meta, filename)

    it "returns directory as is if is a directory":
        with self.a_temp_dir() as directory:
            assert sb.directory_spec().normalise(self.meta, directory) == directory

    it "proxies self.spec for fake_filled":
        res = mock.Mock(name="res")
        spec = mock.Mock(name="spec", spec_set=["fake_filled"])
        spec.fake_filled.return_value = res
        assert sb.directory_spec(spec).fake_filled(self.meta) is res

describe TestCase, "filename_spec":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    it "complains if the value is not a string":
        for opt in (
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            [],
            [1],
            lambda: 1,
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadFilename, "Didn't even get a string", meta=self.meta, got=type(opt)
            ):
                sb.filename_spec().normalise(self.meta, opt)

    it "complains if the value doesn't exist":
        with self.a_temp_file(removed=True) as filename:
            with self.fuzzyAssertRaisesError(
                BadFilename, "Got something that didn't exist", meta=self.meta, filename=filename
            ):
                sb.filename_spec().normalise(self.meta, filename)

    it "doesn't complain if the value doesn't exist if may_not_exist is True":
        with self.a_temp_file(removed=True) as filename:
            assert sb.filename_spec(may_not_exist=True).normalise(self.meta, filename) == filename

    it "complains if the value isn't a file":
        with self.a_temp_dir() as directory:
            with self.fuzzyAssertRaisesError(
                BadFilename,
                "Got something that exists but isn't a file",
                meta=self.meta,
                filename=directory,
            ):
                sb.filename_spec().normalise(self.meta, directory)

    it "returns filename as is if is a filename":
        with self.a_temp_file() as filename:
            assert sb.filename_spec().normalise(self.meta, filename) == filename

describe TestCase, "file_spec":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    it "complains if the object is not a file":
        for opt in (
            "",
            "asdf",
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            [],
            [1],
            lambda: 1,
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Didn't get a file object", meta=self.meta, got=opt
            ):
                sb.file_spec().normalise(self.meta, opt)

    it "lets through a file object":
        with self.a_temp_file() as fle:
            with open(fle) as opened:
                assert sb.file_spec().normalise(self.meta, opened) is opened

describe TestCase, "string_specs":
    __only_run_tests_in_children__ = True

    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    def make_spec(self):
        raise NotImplementedError()

    it "defaults to an empty string":
        assert sb.string_spec().default(self.meta) == ""

    it "complains if the value isn't a string":
        for opt in (
            0,
            1,
            True,
            False,
            {},
            {1: 1},
            [],
            [1],
            lambda: 1,
            type("blah", (object,), {})(),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected a string", meta=self.meta, got=type(opt)
            ):
                self.make_spec().normalise(self.meta, opt)

    it "returns string as is if it is a string":
        for opt in ("", "asdf", u"adsf"):
            assert self.make_spec().normalise(self.meta, opt) == opt

    describe "string_spec":
        make_spec = sb.string_spec

    describe "valid_string_spec":
        make_spec = sb.valid_string_spec

        it "takes in a list of validators":
            validator1 = mock.Mock(name="validator1")
            validator2 = mock.Mock(name="validator2")
            spec = self.make_spec(validator1, validator2)
            assert spec.validators == (validator1, validator2)

        it "uses each validator to get the final value":
            result1 = mock.Mock(name="result1")
            result2 = mock.Mock(name="result2")

            validator1 = mock.Mock(name="validator1", spec_set=["normalise"])
            validator1.normalise.return_value = result1
            validator2 = mock.Mock(name="validator2", spec_set=["normalise"])
            validator2.normalise.return_value = result2

            assert self.make_spec(validator1, validator2).normalise(self.meta, "blah") is result2
            validator1.normalise.assert_called_once_with(self.meta, "blah")
            validator2.normalise.assert_called_once_with(self.meta, result1)

    describe "string_choice_spec":

        def make_spec(self, choices=NotSpecified, reason=NotSpecified):
            choices = ["", "adsf", "asdf"] if choices is NotSpecified else choices
            return sb.string_choice_spec(choices, reason=reason)

        it "takes in a list of choices and a reason":
            choice1 = mock.Mock(name="choice1")
            choice2 = mock.Mock(name="choice2")
            reason = mock.Mock(name="reason")
            spec = self.make_spec([choice1, choice2], reason=reason)
            assert spec.choices == [choice1, choice2]
            assert spec.reason == reason

        it "defaults reason":
            assert self.make_spec([]).reason == "Expected one of the available choices"

        it "complains if the value isn't one of the choices":
            choices = ["one", "two", "three"]
            reason = mock.Mock(name="reason")
            with self.fuzzyAssertRaisesError(
                BadSpecValue, reason, available=choices, got="blah", meta=self.meta
            ):
                self.make_spec(choices, reason=reason).normalise(self.meta, "blah")

describe TestCase, "integer_spec":
    it "converts string integers into integers":
        meta = mock.Mock(name="meta")
        assert sb.integer_spec().normalise(meta, "1333") == 1333

    it "complains if it can't convert the value into an integer":
        meta = mock.Mock(name="meta")
        val = mock.Mock(name="val")
        with self.fuzzyAssertRaisesError(BadSpecValue, "Couldn't transform value into an integer"):
            sb.integer_spec().normalise(meta, val)

    it "keeps integers as integers":
        meta = mock.Mock(name="meta")
        assert sb.integer_spec().normalise(meta, 1337) == 1337

    it "complains about values that aren't integers":
        meta = mock.Mock(name="meta")
        for val, typ in (
            ("", str),
            ("asdf", str),
            ({}, dict),
            ({1: 2}, dict),
            (True, bool),
            (False, bool),
            (None, type(None)),
            ([], list),
            ((), tuple),
            ([1], list),
            ((1,), tuple),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected an integer", meta=meta, got=typ
            ):
                sb.integer_spec().normalise(meta, val)

describe TestCase, "integer_choice_spec":

    def make_spec(self, choices=NotSpecified, reason=NotSpecified):
        choices = [1, 2, 3] if choices is NotSpecified else choices
        return sb.integer_choice_spec(choices, reason=reason)

    it "takes in a list of choices and a reason":
        choice1 = mock.Mock(name="choice1")
        choice2 = mock.Mock(name="choice2")
        reason = mock.Mock(name="reason")
        spec = self.make_spec([choice1, choice2], reason=reason)
        assert spec.choices == [choice1, choice2]
        assert spec.reason == reason

    it "defaults reason":
        assert self.make_spec([]).reason == "Expected one of the available choices"

    it "complains if the value isn't one of the choices":
        choices = [1, 2, 3]
        meta = mock.Mock(name="meta")
        reason = mock.Mock(name="reason")
        with self.fuzzyAssertRaisesError(BadSpecValue, reason, available=choices, got=4):
            self.make_spec(choices, reason=reason).normalise(meta, 4)

        with self.fuzzyAssertRaisesError(BadSpecValue, "Expected an integer", got=str):
            self.make_spec(choices, reason=reason).normalise(meta, "blah")

describe TestCase, "float_spec":
    it "converts string floats into floats":
        meta = mock.Mock(name="meta")
        assert sb.float_spec().normalise(meta, "13.33") == 13.33

    it "keeps floats as floats":
        meta = mock.Mock(name="meta")
        assert sb.float_spec().normalise(meta, 13.37) == 13.37

    it "complains about values that aren't floats":
        meta = mock.Mock(name="meta")
        for val, typ in (
            ("", str),
            ("asdf", str),
            ("0.1.2", str),
            ({}, dict),
            ({1: 2}, dict),
            (True, bool),
            (False, bool),
            (None, type(None)),
            ([], list),
            ((), tuple),
            ([1], list),
            ((1,), tuple),
        ):
            with self.fuzzyAssertRaisesError(BadSpecValue, "Expected a float", meta=meta, got=typ):
                sb.float_spec().normalise(meta, val)

describe TestCase, "create_spec":
    before_each:
        self.meta = mock.Mock(name="meta", spec_set=Meta)

    it "takes in a kls and specs for options we will instantiate it with":
        kls = mock.Mock(name="kls")
        opt1 = mock.Mock(name="opt1")
        opt2 = mock.Mock(name="opt2")

        set_options = mock.Mock(name="set_options")
        set_options_instance = mock.Mock(name="set_options_instance")
        set_options.return_value = set_options_instance

        with mock.patch.object(sb, "set_options", set_options):
            spec = sb.create_spec(kls, a=opt1, b=opt2)

        assert spec.kls is kls
        assert spec.expected == {"a": opt1, "b": opt2}
        assert spec.expected_spec == set_options_instance
        set_options.assert_called_once_with(a=opt1, b=opt2)

    it "validates using provided validators":
        v1 = mock.Mock(name="v1")
        v2 = mock.Mock(name="v2")
        called = []

        v1.normalise.side_effect = lambda m, v: called.append(1)
        v2.normalise.side_effect = lambda m, v: called.append(2)

        kls = namedlist("kls", "blah")
        val = {"blah": "stuff"}

        spec = sb.create_spec(kls, v1, v2, blah=sb.string_spec())
        assert spec.validators == (v1, v2)

        # Normalising with the create_spec will call validators first
        spec.normalise(self.meta, val)

        v1.normalise.assert_called_once_with(self.meta, val)
        v2.normalise.assert_called_once_with(self.meta, val)
        assert called == [1, 2]

    it "returns value as is if already an instance of our kls":
        kls = type("kls", (object,), {})
        spec = sb.create_spec(kls)
        instance = kls()
        assert spec.normalise(self.meta, instance) is instance

    it "uses expected to normalise the val and passes that in as kwargs to kls constructor":

        class Blah(object):
            pass

        instance = sb.create_spec(Blah).normalise(self.meta, {})
        assert instance.__class__ is Blah

        class Meh(object):
            def __init__(self, a, b):
                self.a = a
                self.b = b

        a_val = mock.Mock(name="a_val")
        b_val = mock.Mock(name="b_val")
        c_val = mock.Mock(name="c_val")
        instance = sb.create_spec(Meh, a=pass_through_spec(), b=pass_through_spec()).normalise(
            self.meta, {"a": a_val, "b": b_val, "c": c_val}
        )
        assert instance.__class__ is Meh
        assert instance.a is a_val
        assert instance.b is b_val

    it "passes through errors from expected_spec":

        class Meh(object):
            def __init__(self, a):
                self.a = a

        a_val = mock.Mock(name="a_val")
        spec_error = BadSpecValue("nope!")
        a_spec = mock.Mock(name="a_spec", spec_set=["normalise"])
        a_spec.normalise.side_effect = spec_error
        with self.fuzzyAssertRaisesError(BadSpecValue, meta=self.meta, _errors=[spec_error]):
            sb.create_spec(Meh, a=a_spec).normalise(self.meta, {"a": a_val})

    it "proxies self.spec for fake_filled and creates the kls from the result":

        class Stuff(object):
            def __init__(self, one, two):
                self.one = one
                self.two = two

        one_spec_fake = mock.Mock(name="one_spec_fake")
        one_spec = mock.Mock(name="one_spec", spec_set=["fake_filled"])
        one_spec.fake_filled.return_value = one_spec_fake

        two_spec_fake = mock.Mock(name="two_spec_fake")
        two_spec = mock.Mock(name="two_spec", spec_set=["fake_filled"])
        two_spec.fake_filled.return_value = two_spec_fake

        spec = sb.create_spec(Stuff, one=one_spec, two=two_spec)
        stuff = spec.fake_filled(self.meta)
        assert isinstance(stuff, Stuff)
        assert stuff.one is one_spec_fake
        assert stuff.two is two_spec_fake

describe TestCase, "or_spec":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec1 = mock.Mock(name="spec1")
        self.spec2 = mock.Mock(name="spec2")
        self.spec3 = mock.Mock(name="spec3")

    it "takes in specs as positional arguments":
        spec = sb.or_spec(self.spec1, self.spec3, self.spec2)
        assert spec.specs == (self.spec1, self.spec3, self.spec2)

    it "tries each spec until one succeeds":
        error1 = BadSpecValue("error1")
        error2 = BadSpecValue("error2")
        result = mock.Mock(name="result")
        self.spec1.normalise.side_effect = error1
        self.spec2.normalise.side_effect = error2
        self.spec3.normalise.return_value = result
        assert (
            sb.or_spec(self.spec1, self.spec2, self.spec3).normalise(self.meta, self.val)
        ) is result

        self.spec1.normalise.assert_called_once_with(self.meta, self.val)
        self.spec2.normalise.assert_called_once_with(self.meta, self.val)
        self.spec3.normalise.assert_called_once_with(self.meta, self.val)

    it "doesn't try more specs than it needs to":
        error1 = BadSpecValue("error1")
        result = mock.Mock(name="result")
        self.spec1.normalise.side_effect = error1
        self.spec2.normalise.return_value = result
        assert (
            sb.or_spec(self.spec1, self.spec2, self.spec3).normalise(self.meta, self.val)
        ) is result

        self.spec1.normalise.assert_called_once_with(self.meta, self.val)
        self.spec2.normalise.assert_called_once_with(self.meta, self.val)
        assert len(self.spec3.normalise.mock_calls) == 0

    it "raises all the errors if none of the specs pass":
        error1 = BadSpecValue("error1")
        error2 = BadSpecValue("error2")
        error3 = BadSpecValue("error3")
        self.spec1.normalise.side_effect = error1
        self.spec2.normalise.side_effect = error2
        self.spec3.normalise.side_effect = error3

        with self.fuzzyAssertRaisesError(
            BadSpecValue,
            "Value doesn't match any of the options",
            meta=self.meta,
            val=self.val,
            _errors=[error1, error2, error3],
        ):
            sb.or_spec(self.spec1, self.spec2, self.spec3).normalise(self.meta, self.val)

        self.spec1.normalise.assert_called_once_with(self.meta, self.val)
        self.spec2.normalise.assert_called_once_with(self.meta, self.val)
        self.spec3.normalise.assert_called_once_with(self.meta, self.val)

describe TestCase, "match_spec":
    it "uses the spec that matches the type":
        ret1, ret2, ret3 = (mock.Mock(name="ret1"), mock.Mock(name="ret2"), mock.Mock(name="ret3"))
        spec1 = mock.NonCallableMock(
            name="spec1", normalise=mock.Mock(name="normalise1", return_value=ret1)
        )
        spec2 = mock.NonCallableMock(
            name="spec2", normalise=mock.Mock(name="normalise2", return_value=ret2)
        )
        spec3 = lambda: mock.Mock(
            name="spec3", normalise=mock.Mock(name="normalise3", return_value=ret3)
        )
        specs = [(str, spec1), (list, spec2), (dict, spec3)]

        meta = mock.Mock(name="meta")
        spec = sb.match_spec(*specs)

        assert spec.normalise(meta, "asdf") is ret1
        assert spec.normalise(meta, [1, 2]) is ret2
        assert spec.normalise(meta, "bjlk") is ret1
        assert spec.normalise(meta, {1: 2}) is ret3

    it "complains if it can't find a match":
        spec1 = mock.Mock(name="spec1")
        spec2 = mock.Mock(name="spec2")
        spec3 = mock.Mock(name="spec3")
        specs = [(str, spec1), (list, spec2), (dict, spec3)]

        meta = mock.Mock(name="meta")
        with self.fuzzyAssertRaisesError(
            BadSpecValue,
            "Value doesn't match any of the options",
            meta=meta,
            got=bool,
            expected=[str, list, dict],
        ):
            sb.match_spec(*specs).normalise(meta, True)

    it "allows a fallback":
        meta = mock.Mock(name="meta")
        spec = sb.match_spec((bool, sb.overridden("lolz")), fallback=sb.any_spec())
        assert spec.normalise(meta, True) == "lolz"
        assert spec.normalise(meta, "hahah") == "hahah"

    it "allows fallback to be callable":
        meta = mock.Mock(name="meta")
        spec = sb.match_spec((bool, sb.overridden("lolz")), fallback=lambda: sb.any_spec())
        assert spec.normalise(meta, True) == "lolz"
        assert spec.normalise(meta, "hahah") == "hahah"

describe TestCase, "and_spec":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec1 = mock.Mock(name="spec1")
        self.spec2 = mock.Mock(name="spec2")
        self.spec3 = mock.Mock(name="spec3")

    it "takes in specs as positional arguments":
        spec = sb.or_spec(self.spec1, self.spec3, self.spec2)
        assert spec.specs == (self.spec1, self.spec3, self.spec2)

    it "puts successive values through all specs":
        val1 = mock.Mock(name="val1")
        val2 = mock.Mock(name="val2")
        result = mock.Mock(name="result")
        self.spec1.normalise.return_value = val1
        self.spec2.normalise.return_value = val2
        self.spec3.normalise.return_value = result
        assert (
            sb.and_spec(self.spec1, self.spec2, self.spec3).normalise(self.meta, self.val)
        ) is result

        self.spec1.normalise.assert_called_once_with(self.meta, self.val)
        self.spec2.normalise.assert_called_once_with(self.meta, val1)
        self.spec3.normalise.assert_called_once_with(self.meta, val2)

    it "raises an error with all transformations if one of them fails":
        val1 = mock.Mock(name="val1")
        error = BadSpecValue("error1")
        self.spec1.normalise.return_value = val1
        self.spec2.normalise.side_effect = error

        with self.fuzzyAssertRaisesError(
            BadSpecValue,
            "Value didn't match one of the options",
            meta=self.meta,
            transformations=[self.val, val1],
            _errors=[error],
        ):
            sb.and_spec(self.spec1, self.spec2, self.spec3).normalise(self.meta, self.val)

        self.spec1.normalise.assert_called_once_with(self.meta, self.val)
        self.spec2.normalise.assert_called_once_with(self.meta, val1)
        assert self.spec3.normalise.mock_calls == []

describe TestCase, "optional_spec":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = mock.Mock(name="spec")

    it "takes in a spec":
        spec = sb.optional_spec(self.spec)
        assert spec.spec is self.spec

    it "returns NotSpecified if there is no value":
        assert sb.optional_spec(self.spec).normalise(self.meta, NotSpecified) is NotSpecified

    it "Proxies the spec if there is a value":
        result = mock.Mock(name="result")
        self.spec.normalise.return_value = result
        assert sb.optional_spec(self.spec).normalise(self.meta, self.val) is result
        self.spec.normalise.assert_called_once_with(self.meta, self.val)

    it "proxies self.spec for fake_filled":
        res = mock.Mock(name="res")
        self.spec.fake_filled.return_value = res
        assert sb.optional_spec(self.spec).fake_filled(self.meta) is res

describe TestCase, "dict_from_bool_spec":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = mock.Mock(name="spec")

    it "takes in a dict_maker and a spec":
        dict_maker = mock.Mock(name="dict_maker")
        spec = sb.dict_from_bool_spec(dict_maker, self.spec)
        assert spec.dict_maker is dict_maker
        assert spec.spec is self.spec

    it "proxies to the spec with an empty dictionary if no value":
        result = mock.Mock(name="result")
        self.spec.normalise.return_value = result
        assert (
            sb.dict_from_bool_spec(lambda: 1, self.spec).normalise(self.meta, NotSpecified)
        ) is result
        self.spec.normalise.assert_called_once_with(self.meta, {})

    it "uses dict_maker if the value is a boolean":
        val = mock.Mock(name="val")
        result = mock.Mock(name="result")

        dict_maker = mock.Mock(name="dict_maker")
        dict_maker.return_value = val

        self.spec.normalise.return_value = result
        assert sb.dict_from_bool_spec(dict_maker, self.spec).normalise(self.meta, False) is result
        dict_maker.assert_called_once_with(self.meta, False)
        self.spec.normalise.assert_called_once_with(self.meta, val)

    it "uses the value itself if not a boolean":
        val = mock.Mock(name="val")
        result = mock.Mock(name="result")
        self.spec.normalise.return_value = result
        assert sb.dict_from_bool_spec(lambda: 1, self.spec).normalise(self.meta, val) is result
        self.spec.normalise.assert_called_once_with(self.meta, val)

    it "proxies self.spec for fake_filled":
        res = mock.Mock(name="res")
        self.spec.fake_filled.return_value = res
        assert sb.dict_from_bool_spec(lambda: 1, self.spec).fake_filled(self.meta) is res

describe TestCase, "formatted":
    before_each:
        self.val = mock.Mock(name="val")
        self.meta = mock.Mock(name="meta", spec_set=Meta)
        self.spec = mock.Mock(name="spec")

    it "takes in spec, formatter and expected_type and after_format":
        spec = mock.Mock(name="spec")
        formatter = mock.Mock(name="formatter")
        after_format = mock.Mock(name="after_format")
        expected_type = mock.Mock(name="expected_type")
        formatted = sb.formatted(spec, formatter, expected_type, after_format)
        assert formatted.spec is spec
        assert formatted.formatter is formatter
        assert formatted.after_format is after_format
        assert formatted.expected_type is expected_type

    it "doesn't use formatter if we have after_format and the spec.normalise result is not a string":
        # Doing anything on the formatter will raise an exception and fail the test
        formatter = mock.NonCallableMock(name="formatter", spec=[])

        val = mock.Mock(name="val")
        result = mock.Mock(name="result")

        spec = sb.any_spec()
        af = mock.NonCallableMock(name="af")
        af.normalise.return_value = result

        formatted_spec = sb.formatted(spec, formatter=formatter, after_format=af)
        assert formatted_spec.normalise(self.meta, val) is result

        af.normalise.assert_called_once_with(self.meta, val)

    it "doesn't use formatter if we have after_format and the spec.normalise result is not a string and after_format needs to be called first":
        # Doing anything on the formatter will raise an exception and fail the test
        formatter = mock.NonCallableMock(name="formatter", spec=[])

        val = mock.Mock(name="val")
        result = mock.Mock(name="result")

        spec = sb.any_spec()
        af = mock.Mock(name="af")
        af.normalise.return_value = result

        afk = mock.Mock(name="afk", return_value=af)

        formatted_spec = sb.formatted(spec, formatter=formatter, after_format=afk)
        assert formatted_spec.normalise(self.meta, val) is result

        af.normalise.assert_called_once_with(self.meta, val)

    it "uses after_format on the formatted value from the formatter if we have after_format":
        spec = sb.string_spec()
        val = "{thing}"
        after_format = sb.integer_spec

        formatter = mock.Mock(name="formatter")
        formatter.format.return_value = "12"

        formatterK = mock.Mock(name="formatterK", return_value=formatter)

        formatted_spec = sb.formatted(spec, formatter=formatterK, after_format=after_format)

        assert formatted_spec.normalise(self.meta, val) is 12

        formatterK.assert_called_once_with(mock.ANY, mock.ANY, value="{thing}")

    it "uses the formatter":
        meta_path = mock.Mock(name="path")
        options = mock.Mock(name="options")
        meta_class = mock.Mock(name="meta_class")
        meta_class.return_value = options

        self.meta.path = meta_path
        self.meta.everything = mock.Mock(name="everything", __class__=meta_class)

        key_names = mock.Mock(name="key_names")
        self.meta.key_names = key_names

        formatter = mock.Mock(name="formatter")
        formatter_instance = mock.Mock(name="formatter_instance")
        formatter.return_value = formatter_instance

        formatted = mock.Mock(name="formatted")
        formatter_instance.format.return_value = formatted

        specd = mock.Mock(name="specd")
        self.spec.normalise.return_value = specd

        assert (
            sb.formatted(self.spec, formatter, expected_type=mock.Mock).normalise(
                self.meta, self.val
            )
        ) is formatted
        formatter_instance.format.assert_called_once_with()
        formatter.assert_called_once_with(options, meta_path, value=specd)

        meta_class.assert_called_once_with(
            converters=self.meta.everything.converters, dont_prefix=self.meta.everything.dont_prefix
        )
        assert len(options.update.mock_calls) == 2

        self.spec.normalise.assert_called_once_with(self.meta, self.val)

    it "complains if formatted value has wrong type":
        formatter = lambda *args, **kwargs: "asdf"
        spec = sb.any_spec()
        self.meta.everything = {}
        self.meta.key_names.return_value = {}
        with self.fuzzyAssertRaisesError(
            BadSpecValue, "Expected a different type", expected=mock.Mock, got=str
        ):
            sb.formatted(spec, formatter, expected_type=mock.Mock).normalise(self.meta, "{blah}")

    it "complains if after_format value has wrong type":
        formatter = lambda *args, **kwargs: "13"
        spec = sb.any_spec()
        after_format = sb.integer_spec
        self.meta.everything = {}
        self.meta.key_names.return_value = {}
        with self.fuzzyAssertRaisesError(
            BadSpecValue, "Expected a different type", expected=mock.Mock, got=int
        ):
            sb.formatted(
                spec, formatter, expected_type=mock.Mock, after_format=after_format
            ).normalise(self.meta, "{yeap}")

    it "works with normal dictionary meta.everything":
        formatter = lambda *args, **kwargs: "asdf"
        spec = sb.any_spec()
        self.meta.everything = {"blah": 1}
        self.meta.key_names.return_value = {}
        res = sb.formatted(spec, formatter).normalise(self.meta, self.val)
        assert res == "asdf"

    describe "fake_filled":
        it "actually formats the value if with_non_defaulted":
            res = mock.Mock(name="res")
            normalise_either = mock.Mock(name="normalise_either", return_value=res)
            spec = sb.formatted(mock.Mock(name="spec"), mock.Mock(name="formatter"))
            with mock.patch.object(spec, "normalise_either", normalise_either):
                assert spec.fake_filled(self.meta, with_non_defaulted=True) is res

        it "returns NotSpecified if not with_non_defaulted":
            assert (
                sb.formatted(mock.Mock(name="spec"), mock.Mock(name="formatter")).fake_filled(
                    self.meta, with_non_defaulted=False
                )
            ) is NotSpecified

describe TestCase, "overridden":
    it "returns the value it's initialised with":
        meta = mock.Mock(name="meta", spec=[])
        value = mock.Mock(name="value", spec=[])
        override = mock.Mock(name="override", spec=[])
        assert sb.overridden(override).normalise(meta, value) is override

    it "returns the specified value when calling fake_filled":
        meta = mock.Mock(name="meta", spec=[])
        override = mock.Mock(name="override", spec=[])
        assert sb.overridden(override).fake_filled(meta) is override

describe TestCase, "any_spec":
    it "returns the value it's given":
        meta = mock.Mock(name="meta", spec=[])
        value = mock.Mock(name="value", spec=[])
        assert sb.any_spec().normalise(meta, value) is value


describe TestCase, "string_or_int_as_string_spec":
    it "returns an empty string for the default":
        meta = mock.Mock(name="meta")
        assert sb.string_or_int_as_string_spec().normalise(meta, NotSpecified) == ""

    it "complains if the value is neither string or integer":
        meta = mock.Mock(name="meta")
        for val, typ in (
            ({}, dict),
            ({1: 2}, dict),
            (True, bool),
            (False, bool),
            (None, type(None)),
            ([], list),
            ((), tuple),
            ([1], list),
            ((1,), tuple),
        ):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Expected a string or integer", meta=meta, got=typ
            ):
                sb.string_or_int_as_string_spec().normalise(meta, val)

    it "returns strings as strings":
        meta = mock.Mock(name="meta")
        assert sb.string_or_int_as_string_spec().normalise(meta, "blah") == "blah"

    it "returns integers as strings":
        meta = mock.Mock(name="meta")
        assert sb.string_or_int_as_string_spec().normalise(meta, 1) == "1"

describe TestCase, "container_spec":
    it "returns an instance of the class with normalised value from the specified spec":
        meta = mock.Mock(name="meta")
        normalised = mock.Mock(name="normalised")
        normalise = mock.Mock(name="normalise", return_value=normalised)
        spec = mock.Mock(name="spec", normalise=normalise)
        alright = mock.Mock(name="alright")

        class kls(object):
            def __init__(self, contents):
                if contents is not alright:
                    assert False, "Shouldn't have instantiated a new kls: Got {0}".format(contents)

        assert type(sb.container_spec(kls, spec).normalise(meta, kls(alright))) is kls
        assert len(normalise.mock_calls) is 0

    it "returns the kls instantiated with the fake val of the spec on fake_filled":
        meta = mock.Mock(name="meta")
        spec = mock.Mock(name="spec")
        spec_fake = mock.Mock(name="spec_fake")
        spec.fake_filled.return_value = spec_fake

        class Meh(object):
            def __init__(self, val):
                self.val = val

        meh = sb.container_spec(Meh, spec).fake_filled(meta)
        assert isinstance(meh, Meh)
        assert meh.val is spec_fake

describe TestCase, "delayed":
    it "returns a function that will do the normalisation":
        called = []
        normalise = mock.Mock(name="normalise", side_effect=lambda *args: called.append(1))
        spec = mock.Mock(name="spec", normalise=normalise)

        meta = mock.Mock(name="meta")
        val = mock.Mock(name="val")
        result = sb.delayed(spec).normalise(meta, val)
        assert called == []

        result()
        assert called == [1]
        normalise.assert_called_once_with(meta, val)

    it "returns a function that returns the fake_filled of the spec":
        called = []
        fake_filled = mock.Mock(
            name="fake_filled", side_effect=lambda *args, **kwargs: called.append(1)
        )
        spec = mock.Mock(name="spec", fake_filled=fake_filled)

        meta = mock.Mock(name="meta")
        result = sb.delayed(spec).fake_filled(meta)
        assert called == []

        result()
        assert called == [1]
        fake_filled.assert_called_once_with(meta, with_non_defaulted=False)

describe TestCase, "typed":
    it "complains if the value is the wrong type":

        class Wanted(object):
            pass

        class AnotherType(object):
            pass

        meta = mock.Mock(name="meta")
        for val in (0, 1, "", "1", [], [1], {}, {1: 1}, lambda: 1, AnotherType()):
            with self.fuzzyAssertRaisesError(
                BadSpecValue, "Got the wrong type of value", expected=Wanted, got=type(val)
            ):
                sb.typed(Wanted).normalise(meta, val)

    it "returns the instance if it's the same type of class":

        class Wanted(object):
            pass

        wanted = Wanted()
        meta = mock.Mock(name="meta")
        assert sb.typed(Wanted).normalise(meta, wanted) is wanted

describe TestCase, "has":
    it "takes in the properties to check":
        prop1 = mock.Mock(name="prop1")
        prop2 = mock.Mock(name="prop2")
        assert sb.has(prop1, prop2).properties == (prop1, prop2)

    it "complains if the value doesn't have one of the properties":

        class Wanted(object):
            one = 1

        meta = mock.Mock(name="meta")
        with self.fuzzyAssertRaisesError(
            BadSpecValue,
            "Value is missing required properties",
            required=("one", "two"),
            missing=["two"],
            meta=meta,
        ):
            sb.has("one", "two").normalise(meta, Wanted())

    it "returns the instance if has all the specified properties":

        class Wanted(object):
            one = 1
            two = 2
            three = 3

        wanted = Wanted()
        meta = mock.Mock(name="meta")
        assert sb.has("one", "two").normalise(meta, wanted) is wanted

describe TestCase, "tuple_spec":
    it "takes in the specs to match against":
        spec1 = mock.Mock(name="spec1")
        spec2 = mock.Mock(name="spec2")
        assert sb.tuple_spec(spec1, spec2).specs == (spec1, spec2)

    describe "normalise_filled":
        before_each:
            self.spec1 = sb.pass_through_spec()
            self.spec2 = sb.pass_through_spec()
            self.meta = Meta({}, [])
            self.ts = sb.tuple_spec(self.spec1, self.spec2)

        it "complains if the value is not a tuple":
            for val in (
                0,
                1,
                "",
                "1",
                [],
                [1],
                {},
                {1: 1},
                lambda: 1,
                type("thing", (object,), {}),
            ):
                with self.fuzzyAssertRaisesError(BadSpecValue, "Expected a tuple", got=type(val)):
                    self.ts.normalise(self.meta, val)

        it "complains if the tuple doesn't have the same number of values as specs passed into setup":
            with self.fuzzyAssertRaisesError(
                BadSpecValue,
                "Expected tuple to be of a particular length",
                expected=2,
                got=1,
                meta=self.meta,
            ):
                self.ts.normalise(self.meta, (1,))

            with self.fuzzyAssertRaisesError(
                BadSpecValue,
                "Expected tuple to be of a particular length",
                expected=2,
                got=3,
                meta=self.meta,
            ):
                self.ts.normalise(self.meta, (1, 2, 3))

        it "raises errors if any of the specs don't match":
            error1 = BadSpecValue("error1")
            error3 = BadSpecValue("error3")

            spec1 = mock.Mock(name="spec1")
            spec2 = mock.Mock(name="spec2")
            spec3 = mock.Mock(name="spec3")

            spec1.normalise.side_effect = error1
            spec2.normalise.return_value = 4
            spec3.normalise.side_effect = error3

            with self.fuzzyAssertRaisesError(
                BadSpecValue,
                "Value failed some specifications",
                _errors=[error1, error3],
                meta=self.meta,
            ):
                sb.tuple_spec(spec1, spec2, spec3).normalise(self.meta, (1, 2, 3))

        it "returns the normalised value if all is good":

            def normalise(m, v):
                return v + 1

            spec1 = mock.Mock(name="spec1")
            spec1.normalise.side_effect = normalise

            assert sb.tuple_spec(spec1, spec1).normalise(self.meta, (1, 3)) == (2, 4)

describe TestCase, "none_spec":
    it "defaults to None":
        assert sb.none_spec().normalise(Meta.empty(), NotSpecified) is None

    it "likes the None Value":
        assert sb.none_spec().normalise(Meta.empty(), None) is None

    it "dislikes anything other than None":
        meta = Meta.empty()
        for v in (0, 1, True, False, {}, {1: 2}, [], [1], lambda: None):
            with self.fuzzyAssertRaisesError(BadSpecValue, "Expected None", got=v, meta=meta):
                sb.none_spec().normalise(meta, v)
