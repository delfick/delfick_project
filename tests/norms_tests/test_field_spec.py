# coding: spec

from delfick_project.norms import sb, dictobj, Meta, BadSpec

from delfick_project.norms.field_spec import (
    FieldSpec,
    Field,
    NullableField,
    FieldSpecMixin,
    FieldSpecMetakls,
)
from delfick_project.errors_pytest import assertRaises
from delfick_project.errors import ProgrammerError

from unittest import mock
import pytest


@pytest.fixture()
def meta():
    return Meta.empty()


describe "FieldSpec":
    describe "inheritance":
        it "works":

            class MyKls(dictobj.Spec):
                one = dictobj.Field(sb.string_spec())
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.NullableField(sb.integer_spec)

            res = MyKls.FieldSpec().normalise(Meta.empty(), {"one": "1", "two": "2"})
            assert type(res) == MyKls
            assert res.one == "1"
            assert res.two == 2
            assert res.three == None

            class MyChildKls(MyKls):
                four = dictobj.Field(sb.boolean)
                five = dictobj.Field(sb.dictionary_spec)

            child = MyChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "four": False, "five": {}}
            )
            assert type(child) == MyChildKls
            assert child.one == "1"
            assert child.two == 2
            assert child.three == None
            assert child.four == False
            assert child.five == {}

            class MyGrandChildKls(MyChildKls):
                six = dictobj.Field(sb.boolean)

            child = MyGrandChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "four": False, "five": {}, "six": True}
            )
            assert type(child) == MyGrandChildKls
            assert child.one == "1"
            assert child.two == 2
            assert child.three == None
            assert child.four == False
            assert child.five == {}
            assert child.six == True

        it "works with mixin classes":

            class Mixin:
                @property
                def thing(s):
                    return "blah"

            class MyKls(dictobj.Spec, Mixin):
                one = dictobj.Field(sb.string_spec())
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.NullableField(sb.integer_spec)

            res = MyKls.FieldSpec().normalise(Meta.empty(), {"one": "1", "two": "2"})
            assert type(res) == MyKls
            assert res.thing == "blah"

            class MyChildKls(MyKls, Mixin):
                four = dictobj.Field(sb.boolean)
                five = dictobj.Field(sb.dictionary_spec)

            child = MyChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "four": False, "five": {}}
            )
            assert type(child) == MyChildKls
            assert child.thing == "blah"

            class MyGrandChildKls(MyChildKls):
                six = dictobj.Field(sb.boolean)

            child = MyGrandChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "four": False, "five": {}, "six": True}
            )
            assert type(child) == MyGrandChildKls
            assert child.thing == "blah"

            class AnotherMixin:
                @property
                def other(s):
                    return "meh"

            class MyGrandChildKls(MyChildKls, AnotherMixin):
                six = dictobj.Field(sb.boolean)

            child = MyGrandChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "four": False, "five": {}, "six": True}
            )
            assert type(child) == MyGrandChildKls
            assert child.thing == "blah"
            assert child.other == "meh"

        it "can take fields from a normal dictobj with a list fields":

            class MyKls(dictobj):
                fields = ["one", "two", "three"]

            res = MyKls(1, 2, 3)
            assert type(res) == MyKls
            assert res.one == 1
            assert res.two == 2
            assert res.three == 3

            class MyChildKls(MyKls, metaclass=FieldSpecMetakls):
                four = dictobj.Field(sb.boolean)
                five = dictobj.Field(sb.dictionary_spec)

            child = MyChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "three": "3", "four": False, "five": {}}
            )
            assert type(child) == MyChildKls
            assert child.one == "1"
            assert child.two == "2"
            assert child.three == "3"
            assert child.four == False
            assert child.five == {}

        it "can take fields from a normal dictobj with a dict fields":

            class MyKls(dictobj):
                fields = {"one": "the one", "two": "the two", "three": "the three"}

            res = MyKls(one=1, two=2, three=3)
            assert type(res) == MyKls
            assert res.one == 1
            assert res.two == 2
            assert res.three == 3

            class MyChildKls(MyKls, metaclass=FieldSpecMetakls):
                four = dictobj.Field(sb.boolean)
                five = dictobj.Field(sb.dictionary_spec)

            child = MyChildKls.FieldSpec().normalise(
                Meta.empty(), {"one": "1", "two": "2", "three": "3", "four": False, "five": {}}
            )
            assert type(child) == MyChildKls
            assert child.one == "1"
            assert child.two == "2"
            assert child.three == "3"
            assert child.four == False
            assert child.five == {}

    describe "usage":
        it "works":

            class MyKls(dictobj.Spec):
                one = dictobj.Field(sb.string_spec())
                two = dictobj.Field(sb.integer_spec)
                three = dictobj.NullableField(sb.integer_spec)

            res = MyKls.FieldSpec().normalise(Meta.empty(), {"one": "1", "two": "2"})
            assert type(res) == MyKls
            assert res.one == "1"
            assert res.two == 2
            assert res.three == None

        it "works with a seperate create_kls":

            class MyKls(dictobj.Spec):
                one = dictobj.Field(sb.string_spec())
                two = dictobj.Field(sb.integer_spec())

            called = []

            class CreateKls(object):
                def __init__(s, **kwargs):
                    called.append(kwargs)
                    s.kwargs = kwargs

            res = MyKls.FieldSpec(create_kls=CreateKls).normalise(
                Meta.empty(), {"one": "1", "two": "2"}
            )

            assert res.kwargs == {"one": "1", "two": 2}
            assert type(res) == CreateKls
            assert called == [{"one": "1", "two": 2}]

    describe "make_spec":

        @pytest.fixture()
        def ms(self):
            class Mocks:
                ret = mock.Mock(name="spec")
                inp = mock.Mock(name="inp")
                spec = mock.NonCallableMock(name="spec")

            Mocks.spec.normalise.return_value = Mocks.ret
            return Mocks

        it "handles field that is a callable to a spec", meta, ms:

            class MyKls(dictobj):
                fields = {"one": lambda: ms.spec}

            spec = FieldSpec(MyKls).make_spec(meta)
            assert spec.normalise(meta, {"one": ms.inp}) == {"one": ms.ret}

        it "handles field that is a callable to a Field", meta, ms:

            class MyKls(dictobj):
                fields = {"one": lambda: Field(lambda: ms.spec)}

            spec = FieldSpec(MyKls).make_spec(meta)
            assert spec.normalise(meta, {"one": ms.inp}) == {"one": ms.ret}

        it "handles field that is a callable with a description", meta, ms:

            class MyKls(dictobj):
                fields = {"one": ("description", lambda: Field(lambda: ms.spec))}

            spec = FieldSpec(MyKls).make_spec(meta)
            assert spec.normalise(meta, {"one": ms.inp}) == {"one": ms.ret}

            class MyKls2(dictobj):
                fields = {"two": ("description", lambda: ms.spec)}

            spec = FieldSpec(MyKls2).make_spec(meta)
            assert spec.normalise(meta, {"two": ms.inp}) == {"two": ms.ret}

        it "handles a field that is not callable with a description", meta, ms:

            class MyKls(dictobj):
                fields = {"one": ("description", Field(lambda: ms.spec))}

            spec = FieldSpec(MyKls).make_spec(meta)
            assert spec.normalise(meta, {"one": ms.inp}) == {"one": ms.ret}

            class MyKls2(dictobj):
                fields = {"two": ("description", ms.spec)}

            spec = FieldSpec(MyKls2).make_spec(meta)
            assert spec.normalise(meta, {"two": ms.inp}) == {"two": ms.ret}

        it "handles a field that is not callable", meta, ms:

            class MyKls(dictobj):
                fields = {"one": Field(lambda: ms.spec)}

            spec = FieldSpec(MyKls).make_spec(meta)
            assert spec.normalise(meta, {"one": ms.inp}) == {"one": ms.ret}

            class MyKls2(dictobj):
                fields = {"two": ms.spec}

            spec = FieldSpec(MyKls2).make_spec(meta)
            assert spec.normalise(meta, {"two": ms.inp}) == {"two": ms.ret}

    describe "empty_normalise":
        it "just calls normalise with an empty meta":

            class MyKls(dictobj.Spec):
                fields = dictobj.Field(sb.string_spec())

            res = mock.Mock(name="res")
            fake_normalise = mock.Mock(name="normalise", return_value=res)
            fake_empty = mock.Mock(name="empty")
            fakeMeta = mock.Mock(name="Meta")
            fakeMeta.empty.return_value = fake_empty

            spec = MyKls.FieldSpec()
            with mock.patch("delfick_project.norms.field_spec.Meta", fakeMeta):
                with mock.patch.object(spec, "normalise", fake_normalise):
                    assert spec.empty_normalise(one="one", two="two") is res

            fake_normalise.assert_called_once_with(fake_empty, {"one": "one", "two": "two"})

    describe "normalise":
        it "complains about a class that has no fields":

            class MyKls(object):
                pass

            spec = FieldSpec(MyKls)
            with assertRaises(BadSpec, "No fields on the class!", kls=MyKls):
                spec.normalise(Meta({}, []), {})

        it "complains if any field has no spec":

            class MyKls(object):
                fields = {
                    "one": "one!",
                    "two": type("blah", (object,), {"normalise": lambda: 1})(),
                    "three": ("three!",),
                }

            meta = Meta({}, [])
            error1 = BadSpec("No spec found for option", meta=meta.at("one"), option="one")
            error2 = BadSpec("No spec found for option", meta=meta.at("three"), option="three")

            spec = FieldSpec(MyKls)
            with assertRaises(BadSpec, _errors=[error1, error2]):
                spec.normalise(Meta({}, []), {})

        it "handles a class with empty fields":

            class MyKls(object):
                fields = {}

            spec = FieldSpec(MyKls)
            instance = spec.normalise(Meta({}, []), {})
            assert type(instance) == MyKls

describe "FieldSpecMixin":
    it "provides FieldSpec which passes the class to an instance of FieldSpec":

        class MyKls(FieldSpecMixin):
            fields = {}

        formatter = mock.Mock(name="formatter")
        spec = MyKls.FieldSpec(formatter=formatter)
        assert type(spec) is FieldSpec
        assert spec.kls is MyKls
        assert spec.formatter is formatter

describe "FieldSpecMetaKls":
    it "convert fields into a fields dictionary":
        inp_field1 = mock.Mock(name="inp_field1", is_dictobj_field=True, help="")
        inp_field2 = mock.Mock(name="inp_field2", is_dictobj_field=True, help="")

        class MyKls(metaclass=FieldSpecMetakls):
            field1 = inp_field1
            field2 = inp_field2

            one = "something else"

        assert MyKls.fields == {"field1": inp_field1, "field2": inp_field2}

    it "convert fields into a fields dictionary with tuple of help and field":
        help1 = mock.Mock(name="help1")
        help2 = mock.Mock(name="help2")
        inp_field1 = mock.Mock(name="inp_field1", is_dictobj_field=True, help=help1)
        inp_field2 = mock.Mock(name="inp_field2", is_dictobj_field=True, help=help2)

        class MyKls(metaclass=FieldSpecMetakls):
            field1 = inp_field1
            field2 = inp_field2

            one = "something else"

        assert MyKls.fields == {"field1": (help1, inp_field1), "field2": (help2, inp_field2)}

    it "Adds FieldSpecMixin as a baseclass":

        class MyKls(metaclass=FieldSpecMetakls):
            pass

        assert hasattr(MyKls, "FieldSpec")

describe "NullableField":
    it "is Field but with nullable=True":
        spec = mock.Mock(name="spec")
        field = NullableField(spec, default=False)
        assert issubclass(type(field), Field) is True
        assert field.nullable == True
        assert field.default == False

    it "is Field but with nullable=True and works with format_into instead of spec":
        format_into = mock.Mock(name="format_into")
        field = NullableField(default=False, format_into=format_into)
        assert issubclass(type(field), Field) is True
        assert field.nullable == True
        assert field.default == False

describe "Field":
    it "references mixin and metaclass":
        assert Field.mixin is FieldSpecMixin
        assert Field.metaclass is FieldSpecMetakls

    it "has is_dictobj_field set to True":
        assert Field.is_dictobj_field == True
        assert Field(lambda: 1).is_dictobj_field == True

    it "takes in several things like spec, help, formatted, wrapper and default":
        spec = mock.Mock(name="spec")
        help = mock.Mock(name="help")
        formatted = mock.Mock(name="formatted")
        wrapper = mock.Mock(name="wrapper")
        default = mock.Mock(name="default")

        field = Field(spec, help=help, formatted=formatted, wrapper=wrapper, default=default)

        assert field.spec is spec
        assert field.help is help
        assert field.formatted is formatted
        assert field.wrapper is wrapper
        assert field.default is default

    it "defaults spec to any_spec if format_into is specified":
        field = Field(format_into=sb.integer_spec)
        assert field.spec is sb.any_spec

    it "doesn't override existing spec if format_into is specified":
        field = Field(sb.integer_spec, format_into=sb.integer_spec)
        assert field.spec is sb.integer_spec

    it "sets after_format to what format_into is specified as and sets formatted to True":
        field = Field(sb.integer_spec)
        assert field.after_format is sb.NotSpecified
        assert field.formatted is False

        field = Field(format_into=sb.integer_spec)
        assert field.after_format is sb.integer_spec
        assert field.formatted is True

    it "complains if we have after_format, but formatted is False":
        with assertRaises(ProgrammerError, "after_format was specified when formatted was false"):
            field = Field(sb.any_spec, formatted=False, after_format=sb.integer_spec)

    it "complains if neither spec or format_into is specified":
        with assertRaises(
            ProgrammerError, "Declaring a Field must give a spec, otherwise provide format_into"
        ):
            field = Field()

    describe "clone":
        it "creates a new instance with the same fields":
            spec = mock.Mock(name="spec")
            help = mock.Mock(name="help")
            formatted = mock.Mock(name="formatted")
            wrapper = mock.Mock(name="wrapper")
            default = mock.Mock(name="default")
            after_format = mock.Mock(name="after_format")

            field = Field(
                spec,
                help=help,
                formatted=formatted,
                wrapper=wrapper,
                default=default,
                after_format=after_format,
            )
            clone = field.clone()

            assert field is not clone

            for f in (field, clone):
                assert f.spec is spec
                assert f.help is help
                assert f.formatted is formatted
                assert f.wrapper is wrapper
                assert f.default is default
                assert f.after_format is after_format

            # Make sure we can change the clone and not effect the original
            clone.formatted = False
            assert field.formatted is formatted

        it "allows overrides":
            spec = mock.Mock(name="spec")
            help = mock.Mock(name="help")
            formatted = mock.Mock(name="formatted")
            formatted2 = mock.Mock(name="formatted2")
            wrapper = mock.Mock(name="wrapper")
            default = mock.Mock(name="default")
            default2 = mock.Mock(name="default2")
            after_format = mock.Mock(name="after_format")
            after_format2 = mock.Mock(name="after_format2")

            field = Field(
                spec,
                help=help,
                formatted=formatted,
                wrapper=wrapper,
                default=default,
                after_format=after_format2,
            )
            clone = field.clone(formatted=formatted2, default=default2, after_format=after_format2)

            assert field is not clone

            assert clone.spec is spec
            assert clone.help is help
            assert clone.formatted is formatted2
            assert clone.wrapper is wrapper
            assert clone.default is default2
            assert clone.after_format is after_format2

    describe "make_spec":

        @pytest.fixture()
        def formatter(self):
            return mock.Mock(name="formatter")

        it "calls the spec if callable", meta, formatter:
            instance = mock.Mock(name="instance")
            spec = mock.Mock(name="spec", return_value=instance)
            assert Field(spec).make_spec(meta, formatter) is instance

        it "wraps spec in a defaulted if default is specified", meta, formatter:
            ret = mock.Mock(name="ret")
            inp = mock.Mock(name="inp")
            dflt = mock.Mock(name="dflt")
            instance = mock.Mock(name="instance")
            instance.normalise.return_value = ret
            spec = mock.Mock(name="spec", return_value=instance)
            spec = Field(spec, default=dflt).make_spec(meta, formatter)

            assert spec.normalise(meta, sb.NotSpecified) is dflt
            assert spec.normalise(meta, inp) is ret

        it "wraps default in a formatted if default and formatted are defined", meta:
            ret = mock.Mock(name="ret")
            inp = mock.Mock(name="inp")
            dflt = mock.Mock(name="dflt")

            class Formatter(object):
                def __init__(s, options, path, value):
                    s.value = value

                def format(s):
                    return ("formatted", s.value)

            instance = mock.Mock(name="instance")
            instance.normalise.return_value = ret
            spec = mock.Mock(name="spec", return_value=instance)
            spec = Field(spec, default=dflt, formatted=True).make_spec(meta, Formatter)

            assert spec.normalise(meta, sb.NotSpecified) == ("formatted", dflt)
            assert spec.normalise(meta, inp) == ("formatted", ret)

        it "wraps everything in wrapper if it's defined", meta, formatter:
            spec = Field(sb.string_or_int_as_string_spec, wrapper=sb.listof).make_spec(
                meta, formatter
            )
            assert spec.normalise(meta, 1) == ["1"]

        describe "nullable=True":
            it "defaults to None", meta, formatter:
                spec = NullableField(sb.string_spec).make_spec(meta, formatter)
                assert spec.normalise(meta, sb.NotSpecified) == None

            it "allows None as a value", meta, formatter:

                class i_hate_none_spec(sb.Spec):
                    def normalise_filled(s, meta, val):
                        if val is None:
                            raise Exception("I hate None", got=val, meta=meta)
                        return None

                spec = NullableField(i_hate_none_spec).make_spec(meta, formatter)
                assert spec.normalise(meta, sb.NotSpecified) == None

            it "calls the spec for you", meta, formatter:
                spec = NullableField(sb.integer_spec).make_spec(meta, formatter)
                assert spec.normalise(meta, "1") == 1

            it "still respects default", meta, formatter:
                dflt = mock.Mock(name="dflt")
                spec = NullableField(sb.string_spec, default=dflt).make_spec(meta, formatter)
                assert spec.normalise(meta, sb.NotSpecified) == dflt

            it "doesn't get formatted if not specified or specified as None", meta:
                formatter = mock.NonCallableMock(name="formatter", spec=[])
                spec = NullableField(format_into=sb.integer_spec).make_spec(meta, formatter)

                assert spec.normalise(meta, sb.NotSpecified) == None
                assert spec.normalise(meta, None) == None
