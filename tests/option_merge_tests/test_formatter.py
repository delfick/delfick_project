# coding: spec

from delfick_project.option_merge import MergedOptionStringFormatter, MergedOptions, BadOptionFormat

from delfick_project.errors_pytest import assertRaises
from delfick_project.norms import sb

from unittest import mock
import pytest
import string


describe "MergedOptionStringFormatter":

    @pytest.fixture()
    def ms(self, autouse=True):
        class Mocks:
            all_options = mock.MagicMock(name="all_options")
            chain = mock.Mock(name="chain")
            value = mock.Mock(name="value")

        return Mocks

    it "takes in all_options, value and chain", ms:
        formatter = MergedOptionStringFormatter(ms.all_options, ms.value, chain=ms.chain)
        assert formatter.all_options is ms.all_options
        assert formatter.value is ms.value
        assert formatter.chain is ms.chain

    it "defaults chain to a list", ms:
        formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
        assert formatter.chain == []

    describe "format":
        it "returns the value if it's not a string", ms:
            value = mock.Mock(name="value")
            assert (MergedOptionStringFormatter(ms.all_options, value).format()) is value

        it "calls format on super if the value is a string", ms:
            result = mock.Mock(name="result")
            format_func = mock.Mock(name="format", return_value=result)

            with mock.patch.object(string.Formatter, "format", format_func):
                assert (MergedOptionStringFormatter(ms.all_options, "asdf").format()) is result

            format_func.assert_called_once_with("asdf")

        it "complains about recursive options":
            all_options = MergedOptions.using({"one": "{two.three}", "two": {"three": "{one}"}})

            formatter = MergedOptionStringFormatter(all_options, "{one}")
            with assertRaises(
                BadOptionFormat, "Recursive option", chain=["one", "two.three", "one"]
            ):
                formatter.format()

        it "complains if option isn't in the options":
            all_options = MergedOptions.using({"one": "{two}"})

            formatter = MergedOptionStringFormatter(all_options, "{one}")
            with assertRaises(
                BadOptionFormat, "Can't find key in options", chain=["one"], key="two"
            ):
                formatter.format()

    describe "get_string":
        it "gets the key from all_options", ms:
            meh = mock.Mock(name="meh")
            blah = mock.Mock(name="blah")
            all_options = {meh: blah}

            assert (MergedOptionStringFormatter(all_options, ms.value).get_string(meh)) is blah

    describe "get_field":
        it "returns special if special_get_field returns something", ms:
            ret = mock.Mock(name="ret")
            special_get_field = mock.Mock(name="special_get_field")
            special_get_field.return_value = ret

            args = mock.Mock(name="args")
            value = mock.Mock(name="value")
            kwargs = mock.Mock(name="kwargs")
            format_spec = mock.Mock(name="format_spec")

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(formatter, "special_get_field", special_get_field):
                assert formatter.get_field(value, args, kwargs, format_spec=format_spec) is ret

            special_get_field.assert_called_once_with(value, args, kwargs, format_spec)

        it "recursively formats options":
            all_options = MergedOptions.using({"one": "{two.three}", "two": {"three": 4}})

            formatter = MergedOptionStringFormatter(all_options, "{one}")
            assert formatter.get_field("one", (), {}) == ("4", ())

    describe "format_field":
        it "returns special_format_field if it returns a value", ms:
            ret = mock.Mock(name="ret")
            special_format_field = mock.Mock(name="special_format_field")
            special_format_field.return_value = ret

            obj = mock.Mock(name="obj")
            format_spec = mock.Mock(name="format_spec")

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is ret

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the obj if it's a dictionary", ms:

            class blah(dict):
                pass

            obj = blah()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the object if asks for it", ms:

            class Obj(object):
                _merged_options_formattable = True

            obj = Obj()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the object if it's a mock", ms:
            obj = mock.Mock(name="obj")

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(formatter, "special_format_field", special_format_field):
                assert formatter.format_field(obj, format_spec) is obj

            special_format_field.assert_called_once_with(obj, format_spec)

        it "returns the obj if it's a lambda or function or method", ms:

            class blah(dict):
                def method(s):
                    pass

            def func(s):
                pass

            lamb = lambda: 1
            obj = blah()

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            for callable_obj in (obj.method, func, lamb, sum):
                formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
                with mock.patch.object(formatter, "special_format_field", special_format_field):
                    assert formatter.format_field(callable_obj, format_spec) is callable_obj

        it "does an actual format_field if no special and obj is not a dict", ms:
            obj = "shizzle"

            format_spec = mock.Mock(name="format_spec")
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            ret = mock.Mock(name="ret")
            super_format_field = mock.Mock(name="super_format_field", return_value=ret)

            formatter = MergedOptionStringFormatter(ms.all_options, ms.value)
            with mock.patch.object(string.Formatter, "format_field", super_format_field):
                with mock.patch.object(formatter, "special_format_field", special_format_field):
                    assert formatter.format_field(obj, format_spec) is ret

            special_format_field.assert_called_once_with(obj, format_spec)

    describe "_vformat":
        it "returns the object if only formatting one item":
            blah = type("blah", (dict,), {})()
            all_options = {"meh": blah}

            args = mock.Mock(name="args")
            kwargs = mock.Mock(name="kwargs")
            used_args = set([mock.Mock(name="used_args")])

            formatter = MergedOptionStringFormatter(all_options, "meh")
            special_get_field = mock.Mock(name="special_get_field", return_value=None)
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            with mock.patch.multiple(
                formatter,
                special_get_field=special_get_field,
                special_format_field=special_format_field,
            ):
                assert formatter._vformat("{meh}", args, kwargs, used_args, 2) is blah

        it "concatenates the strings together if this is multiple things to be formatted":
            blah = type("blah", (dict,), {})({"1": "2"})
            all_options = {"meh": blah, "wat": "ever"}

            args = mock.Mock(name="args")
            kwargs = mock.Mock(name="kwargs")
            used_args = set([mock.Mock(name="used_args")])

            formatter = MergedOptionStringFormatter(all_options, "meh")
            special_get_field = mock.Mock(name="special_get_field", return_value=None)
            special_format_field = mock.Mock(name="special_format_field", return_value=None)

            with mock.patch.multiple(
                formatter,
                special_get_field=special_get_field,
                special_format_field=special_format_field,
            ):
                assert (
                    formatter._vformat("{meh}and{wat}", args, kwargs, used_args, 2)
                    == "{'1': '2'}andever"
                )

describe "Custom MergedOptionStringFormatter":
    it "works":

        class MyStringFormatter(MergedOptionStringFormatter):
            custom_format_specs = ["no_interpret"]

            def special_format_field(s, obj, format_spec):
                if format_spec == "upper":
                    return obj.upper()

                if format_spec == "no_interpret":
                    return obj

        all_options = MergedOptions.using(
            {"yeap": "yessir", "blah": "notused"}, {"blah": {"things": "stuff", "la": "delala"}}
        )
        formatter = MyStringFormatter(
            all_options, "{yeap} and {blah.things:upper} {blah.la:no_interpret}"
        )
        assert formatter.format() == "yessir and STUFF blah.la"

    it "formats what it finds":
        all_options = MergedOptions.using({"one": "{two}", "two": "three"})
        formatter = MergedOptionStringFormatter(all_options, "{one}")
        assert formatter.format() == "three"
